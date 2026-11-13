"""Main trading bot orchestration – multi-strategy + full Telegram control."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from loguru import logger

from src.core.state import BotState, PositionInfo
from src.exchange.client import BinanceClient
from src.indicators.technical import add_all_indicators, market_summary
from src.risk.manager import RiskManager
from src.strategy import get_strategy, list_strategies
from src.strategy.base import BaseStrategy
from src.utils.charts import create_chart


class TradingBot:
    def __init__(
        self,
        client: BinanceClient,
        state: BotState,
        config: dict,
        poll_interval: int = 45,
    ):
        self.client = client
        self.state = state
        self.config = config
        self.poll_interval = poll_interval

        self._strategy: Optional[BaseStrategy] = None
        self._risk: Optional[RiskManager] = None
        self._last_strategy_name = ""
        self._last_risk_profile = ""
        self._rebuild_components()

    def _rebuild_components(self) -> None:
        profile_name = self.state.risk_profile
        profile = self.config["risk_profiles"][profile_name]
        circuit = self.config.get("circuit_breaker", {})

        self._strategy = get_strategy(self.state.strategy_name, profile)
        self._risk = RiskManager(profile=profile, circuit_breaker=circuit)

        self._last_strategy_name = self.state.strategy_name
        self._last_risk_profile = profile_name

        logger.info(
            "Engine ready | strategy={} | risk={}",
            self.state.strategy_name,
            profile_name.upper(),
        )

    def _get_equity(self) -> float:
        try:
            balance = self.client.fetch_balance()
            usdt = balance.get("USDT", {})
            return float(usdt.get("total", 0) or 0)
        except Exception as e:
            logger.error("Balance fetch failed: {}", e)
            return self.state.equity

    def _fetch_dataframe(self) -> pd.DataFrame:
        ohlcv = self.client.fetch_ohlcv(self.state.symbol, self.state.timeframe, limit=200)
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    def _open_long(self, df: pd.DataFrame) -> None:
        if self.state.position is not None:
            return

        equity = self._get_equity()
        self._risk.update_equity(equity)

        if self._risk.is_halted:
            self.state.add_notification(f"🚨 Circuit breaker: {self._risk.halt_reason}")
            self.state.update(trading_enabled=False)
            return

        last = df.iloc[-1]
        atr = last.get("atr")
        if pd.isna(atr) or atr <= 0:
            return

        entry_price = float(last["close"])
        size_result = self._risk.calculate_position_size(equity, entry_price, float(atr))
        if not size_result:
            return

        qty = self.client.amount_to_precision(self.state.symbol, size_result.quantity)
        if qty <= 0:
            return

        order = self.client.create_market_buy(self.state.symbol, qty)
        if order:
            pos = PositionInfo(
                symbol=self.state.symbol,
                side="long",
                quantity=qty,
                entry_price=entry_price,
                opened_at=datetime.now(timezone.utc),
                stop_price=size_result.stop_price,
                take_profit=size_result.take_profit_price,
            )
            self.state.update(position=pos, trades_today=self.state.trades_today + 1)

            msg = (
                f"🟢 *LONG OPENED*\n"
                f"Strategy: `{self.state.strategy_name}`\n"
                f"Symbol: `{self.state.symbol}`\n"
                f"Qty: `{qty:.6f}`\n"
                f"Entry: `{entry_price:.2f}`\n"
                f"Stop: `{size_result.stop_price:.2f}`\n"
                f"TP: `{size_result.take_profit_price:.2f}`\n"
                f"Risk: `{size_result.risk_amount:.2f} USDT`"
            )
            self.state.add_notification(msg)

    def _close_position(self, reason: str = "signal") -> None:
        pos = self.state.position
        if not pos:
            return

        order = self.client.create_market_sell(pos.symbol, pos.quantity)
        if order:
            last_price = self.state.last_price or pos.entry_price
            pnl = (last_price - pos.entry_price) * pos.quantity
            self.state.update(
                position=None,
                realized_pnl_today=self.state.realized_pnl_today + pnl,
            )

            msg = (
                f"🔴 *POSITION CLOSED* ({reason})\n"
                f"Symbol: `{pos.symbol}`\n"
                f"Qty: `{pos.quantity:.6f}`\n"
                f"Entry: `{pos.entry_price:.2f}`\n"
                f"Exit≈ `{last_price:.2f}`\n"
                f"Est. PnL: `{pnl:+.2f} USDT`"
            )
            self.state.add_notification(msg)

    def run(self) -> None:
        logger.info("Trading engine started")

        while not self.state.shutdown_requested:
            try:
                # Hot-reload strategy or risk profile
                if (
                    self.state.strategy_name != self._last_strategy_name
                    or self.state.risk_profile != self._last_risk_profile
                ):
                    self._rebuild_components()

                equity = self._get_equity()
                self.state.update(equity=equity)

                # Force close from Telegram
                if self.state.force_close:
                    self.state.update(force_close=False)
                    if self.state.position:
                        self._close_position(reason="telegram force close")

                df = self._fetch_dataframe()
                if not df.empty:
                    df = add_all_indicators(df)
                    self.state.update(last_price=float(df.iloc[-1]["close"]))

                # Analyze / Chart requests are handled by Telegram side mostly,
                # but we keep the latest df available via state if needed.

                if not self.state.trading_enabled:
                    time.sleep(2)
                    continue

                if self._risk and self._risk.is_halted:
                    self.state.update(trading_enabled=False)
                    self.state.add_notification(f"🚨 Trading halted: {self._risk.halt_reason}")
                    time.sleep(5)
                    continue

                signal = self._strategy.generate_signal(df)
                self.state.update(last_signal=signal)

                if signal == "long" and self.state.position is None:
                    self._open_long(df)
                elif signal == "exit" and self.state.position is not None:
                    self._close_position(reason="strategy exit")

            except Exception as e:
                logger.exception("Engine error: {}", e)
                self.state.add_notification(f"⚠️ Engine error: `{e}`")

            time.sleep(self.poll_interval)

        logger.info("Trading engine stopped")
