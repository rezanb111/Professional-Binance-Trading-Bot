"""Production trading engine – fees, slippage, trailing stop, scored entries."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from loguru import logger

from src.core.journal import log_trade
from src.core.state import BotState, PositionInfo
from src.exchange.client import BinanceClient
from src.indicators.technical import add_all_indicators
from src.risk.manager import RiskManager
from src.strategy import get_strategy
from src.strategy.base import BaseStrategy, SignalResult


class TradingBot:
    def __init__(self, client: BinanceClient, state: BotState, config: dict, poll_interval: int = 45):
        self.client = client
        self.state = state
        self.config = config
        self.poll_interval = poll_interval
        self.exec_cfg = config.get("execution", {})
        self.fee_rate = float(self.exec_cfg.get("fee_rate", 0.001))
        self.slippage_bps = float(self.exec_cfg.get("slippage_bps", 5))

        self._strategy: Optional[BaseStrategy] = None
        self._risk: Optional[RiskManager] = None
        self._last_strategy_name = ""
        self._last_risk_profile = ""
        self._peak_price_since_entry: Optional[float] = None
        self._rebuild_components()

    def _rebuild_components(self) -> None:
        profile = self.config["risk_profiles"][self.state.risk_profile]
        circuit = self.config.get("circuit_breaker", {})
        self._strategy = get_strategy(self.state.strategy_name, profile)
        self._risk = RiskManager(profile=profile, circuit_breaker=circuit)
        self._last_strategy_name = self.state.strategy_name
        self._last_risk_profile = self.state.risk_profile
        logger.info("Engine ready | {} | risk={}", self.state.strategy_name, self.state.risk_profile)

    def _apply_slippage(self, price: float, side: str) -> float:
        slip = self.slippage_bps / 10000.0
        if side == "buy":
            return price * (1 + slip)
        return price * (1 - slip)

    def _fee(self, notional: float) -> float:
        return notional * self.fee_rate

    def _refresh_equity(self) -> float:
        eq = self.state.mark_equity()
        self.state.update(equity=eq)
        if self._risk:
            self._risk.update_equity(eq)
            self.state.update(max_drawdown_pct=self._risk.drawdown_pct(eq))
        return eq

    def _fetch_dataframe(self) -> pd.DataFrame:
        ohlcv = self.client.fetch_ohlcv(self.state.symbol, self.state.timeframe, limit=200)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    def _open_long(self, df: pd.DataFrame, signal_meta: SignalResult) -> None:
        if self.state.position is not None:
            return

        ok, reason = self.state.can_open_new_trade()
        if not ok:
            logger.info("Skip: {}", reason)
            return

        equity = self._refresh_equity()
        if self._risk and self._risk.is_halted:
            self.state.add_notification(f"🚨 {self._risk.halt_reason}")
            self.state.update(trading_enabled=False)
            return

        last = df.iloc[-1]
        atr = last.get("atr")
        if pd.isna(atr) or atr <= 0:
            return

        raw_price = float(last["close"])
        size_result = self._risk.calculate_position_size(equity, raw_price, float(atr))
        if not size_result:
            return

        qty = self.client.amount_to_precision(self.state.symbol, size_result.quantity)
        if qty <= 0:
            return

        order = self.client.create_market_buy(self.state.symbol, qty)
        if not order:
            return

        fill = float(order.get("average") or order.get("price") or raw_price)
        fill = self._apply_slippage(fill, "buy")
        notional = qty * fill
        fee = self._fee(notional)
        total_cost = notional + fee

        if self.state.paper_mode:
            if total_cost > self.state.paper_cash:
                qty = self.client.amount_to_precision(
                    self.state.symbol, (self.state.paper_cash * 0.97) / fill
                )
                if qty <= 0:
                    return
                notional = qty * fill
                fee = self._fee(notional)
                total_cost = notional + fee
            self.state.update(paper_cash=self.state.paper_cash - total_cost)

        # Adjust stop for slipped entry
        stop = size_result.stop_price - (fill - raw_price)
        tp = size_result.take_profit_price + (fill - raw_price) if size_result.take_profit_price else None

        pos = PositionInfo(
            symbol=self.state.symbol,
            side="long",
            quantity=qty,
            entry_price=fill,
            opened_at=datetime.now(timezone.utc),
            stop_price=stop,
            take_profit=tp,
            fees_paid=fee,
            signal_score=signal_meta.score,
        )
        self.state.update(position=pos, trades_today=self.state.trades_today + 1)
        self._peak_price_since_entry = fill
        self._refresh_equity()

        log_trade(
            event="OPEN",
            symbol=self.state.symbol,
            side="long",
            quantity=qty,
            price=fill,
            stop=stop,
            take_profit=tp,
            strategy=self.state.strategy_name,
            risk_profile=self.state.risk_profile,
            dry_run=self.state.paper_mode,
        )

        self.state.add_notification(
            f"🟢 *LONG* score `{signal_meta.score}`\n"
            f"`{self.state.symbol}` `{qty:.6f}` @ `{fill:.2f}`\n"
            f"SL `{stop:.2f}` TP `{tp:.2f if tp else '—'}`\n"
            f"Fee `{fee:.4f}` | {signal_meta.reason}"
        )

    def _close_position(self, reason: str = "signal") -> None:
        pos = self.state.position
        if not pos:
            return

        order = self.client.create_market_sell(pos.symbol, pos.quantity)
        if not order:
            return

        raw = float(order.get("average") or order.get("price") or self.state.last_price or pos.entry_price)
        fill = self._apply_slippage(raw, "sell")
        proceeds = pos.quantity * fill
        fee = self._fee(proceeds)
        net_proceeds = proceeds - fee
        pnl = net_proceeds - (pos.quantity * pos.entry_price) - (pos.fees_paid or 0)

        if self.state.paper_mode:
            self.state.update(paper_cash=self.state.paper_cash + net_proceeds)

        wins, losses = self.state.wins_today, self.state.losses_today
        if pnl >= 0:
            wins += 1
        else:
            losses += 1
            self.state.update(last_stop_loss_at=datetime.now(timezone.utc))

        self.state.update(
            position=None,
            realized_pnl_today=self.state.realized_pnl_today + pnl,
            wins_today=wins,
            losses_today=losses,
        )
        self._peak_price_since_entry = None
        self._refresh_equity()

        log_trade(
            event="CLOSE",
            symbol=pos.symbol,
            side=pos.side,
            quantity=pos.quantity,
            price=fill,
            pnl=pnl,
            strategy=self.state.strategy_name,
            risk_profile=self.state.risk_profile,
            dry_run=self.state.paper_mode,
        )

        self.state.add_notification(
            f"🔴 *CLOSED* ({reason})\n"
            f"`{pos.symbol}` @ `{fill:.2f}`\n"
            f"PnL `{pnl:+.2f}` (fees included)\n"
            f"Equity `{self.state.equity:.2f}`"
        )

    def _update_trailing(self, atr: float) -> None:
        pos = self.state.position
        if not pos or not self._risk or atr <= 0:
            return
        if self.state.last_price > (self._peak_price_since_entry or 0):
            self._peak_price_since_entry = self.state.last_price

        trail = self._risk.trailing_stop(pos.entry_price, self._peak_price_since_entry or pos.entry_price, atr)
        # Only ratchet stop up
        if pos.stop_price is None or trail > pos.stop_price:
            pos.stop_price = trail
            self.state.update(position=pos)

    def run(self) -> None:
        logger.info("Engine started | paper={}", self.state.paper_mode)

        while not self.state.shutdown_requested:
            try:
                if (
                    self.state.strategy_name != self._last_strategy_name
                    or self.state.risk_profile != self._last_risk_profile
                ):
                    self._rebuild_components()

                if self.state.force_close:
                    self.state.update(force_close=False)
                    if self.state.position:
                        self._close_position("telegram")

                df = self._fetch_dataframe()
                atr_val = 0.0
                if not df.empty:
                    df = add_all_indicators(df)
                    self.state.update(last_price=float(df.iloc[-1]["close"]))
                    atr_val = float(df.iloc[-1].get("atr") or 0)

                self._refresh_equity()

                if not self.state.trading_enabled:
                    time.sleep(2)
                    continue

                if self._risk and self._risk.is_halted:
                    self.state.update(trading_enabled=False)
                    self.state.add_notification(f"🚨 {self._risk.halt_reason}")
                    time.sleep(5)
                    continue

                if self.state.position and atr_val > 0:
                    self._update_trailing(atr_val)

                if self.state.position and self.state.position.stop_price:
                    if self.state.last_price <= self.state.position.stop_price:
                        self._close_position("stop/trail")
                        continue

                if self.state.position and self.state.position.take_profit:
                    if self.state.last_price >= self.state.position.take_profit:
                        self._close_position("take-profit")
                        continue

                result = self._strategy.evaluate(df)
                self.state.update(last_signal=result.signal, last_signal_score=result.score)

                if result.signal == "long" and self.state.position is None:
                    self._open_long(df, result)
                elif result.signal == "exit" and self.state.position is not None:
                    self._close_position("strategy exit")

            except Exception as e:
                logger.exception("Engine error: {}", e)
                self.state.add_notification(f"⚠️ `{e}`")

            time.sleep(self.poll_interval)

        logger.info("Engine stopped")
