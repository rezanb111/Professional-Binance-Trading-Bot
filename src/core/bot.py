"""Main trading bot orchestration – now fully controllable via shared state."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import yaml
from loguru import logger
from pathlib import Path

from src.core.state import BotState, PositionInfo
from src.exchange.client import BinanceClient
from src.risk.manager import RiskManager
from src.strategy.ema_rsi import EmaRsiStrategy


class TradingBot:
    """Core trading loop controlled by BotState."""

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

        self._strategy: Optional[EmaRsiStrategy] = None
        self._risk: Optional[RiskManager] = None
        self._rebuild_components()

    def _rebuild_components(self) -> None:
        """Rebuild strategy & risk manager when profile changes."""
        profile_name = self.state.risk_profile
        profile = self.config["risk_profiles"][profile_name]
        circuit = self.config.get("circuit_breaker", {})

        self._strategy = EmaRsiStrategy(params=profile)
        self._risk = RiskManager(profile=profile, circuit_breaker=circuit)
        logger.info("Components rebuilt for risk profile: {}", profile_name.upper())

    def _get_equity(self) -> float:
        try:
            balance = self.client.fetch_balance()
            usdt = balance.get("USDT", {})
            return float(usdt.get("total", 0) or 0)
        except Exception as e:
            logger.error("Failed to fetch balance: {}", e)
            return self.state.equity

    def _fetch_dataframe(self) -> pd.DataFrame:
        ohlcv = self.client.fetch_ohlcv(self.state.symbol, self.state.timeframe, limit=150)
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
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
            logger.warning("ATR not available – skipping entry")
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
                f"Symbol: `{self.state.symbol}`\n"
                f"Qty: `{qty:.6f}`\n"
                f"Entry: `{entry_price:.2f}`\n"
                f"Stop: `{size_result.stop_price:.2f}`\n"
                f"TP: `{size_result.take_profit_price:.2f}`\n"
                f"Risk: `{size_result.risk_amount:.2f} USDT`"
            )
            self.state.add_notification(msg)
            logger.success("Opened LONG | qty={:.6f} @ {:.2f}", qty, entry_price)

    def _close_position(self, reason: str = "signal") -> None:
        pos = self.state.position
        if not pos:
            return

        order = self.client.create_market_sell(pos.symbol, pos.quantity)
        if order:
            # Rough PnL estimate (not exact without fill price)
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
            logger.success("Closed position | reason={}", reason)

    def run(self) -> None:
        logger.info("Trading engine started (controlled by Telegram state)")
        last_profile = self.state.risk_profile

        while not self.state.shutdown_requested:
            try:
                # Hot-reload risk profile if changed via Telegram
                if self.state.risk_profile != last_profile:
                    self._rebuild_components()
                    last_profile = self.state.risk_profile

                equity = self._get_equity()
                self.state.update(equity=equity)

                # Process force-close requests from Telegram
                notes = self.state.pending_notifications[:]  # peek
                if "FORCE_CLOSE" in notes:
                    self.state.pop_notifications()  # clear
                    if self.state.position:
                        self._close_position(reason="telegram force close")

                if not self.state.trading_enabled:
                    time.sleep(2)
                    continue

                if self._risk and self._risk.is_halted:
                    self.state.update(trading_enabled=False)
                    self.state.add_notification(f"🚨 Trading halted: {self._risk.halt_reason}")
                    time.sleep(5)
                    continue

                df = self._fetch_dataframe()
                if not df.empty:
                    last_close = float(df.iloc[-1]["close"])
                    self.state.update(last_price=last_close)

                signal = self._strategy.generate_signal(df)
                self.state.update(last_signal=signal)

                logger.debug(
                    "Signal={} | pos={} | equity={:.2f} | enabled={}",
                    signal,
                    bool(self.state.position),
                    equity,
                    self.state.trading_enabled,
                )

                if signal == "long" and self.state.position is None:
                    self._open_long(df)
                elif signal == "exit" and self.state.position is not None:
                    self._close_position(reason="strategy exit")

            except Exception as e:
                logger.exception("Error in trading loop: {}", e)
                self.state.add_notification(f"⚠️ Engine error: {e}")

            time.sleep(self.poll_interval)

        logger.info("Trading engine stopped")
