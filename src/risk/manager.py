"""Institutional-style risk management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger


@dataclass
class PositionSizeResult:
    quantity: float
    risk_amount: float
    stop_price: float
    take_profit_price: Optional[float]


class RiskManager:
    def __init__(self, profile: dict, circuit_breaker: dict):
        self.risk_per_trade = profile["risk_per_trade"]
        self.atr_stop_mult = profile["atr_stop_multiplier"]
        self.atr_tp_mult = profile.get("atr_take_profit_multiplier", 3.0)
        self.trailing_atr_mult = profile.get("trailing_atr_multiplier", 2.0)
        self.max_positions = profile["max_positions"]
        self.min_signal_score = profile.get("min_signal_score", 60)
        self.min_adx = profile.get("min_adx", 18)

        self.max_daily_loss_pct = circuit_breaker.get("max_daily_loss_pct", 0.05)
        self.max_drawdown_pct = circuit_breaker.get("max_drawdown_pct", 0.15)

        self._day_start_equity: Optional[float] = None
        self._peak_equity: Optional[float] = None
        self._halted = False
        self._halt_reason: str = ""

    def update_equity(self, equity: float) -> None:
        if self._day_start_equity is None:
            self._day_start_equity = equity
        if self._peak_equity is None or equity > self._peak_equity:
            self._peak_equity = equity

        if self._day_start_equity and equity < self._day_start_equity * (1 - self.max_daily_loss_pct):
            self._halted = True
            self._halt_reason = f"Daily loss limit ({self.max_daily_loss_pct:.0%})"
            logger.critical(self._halt_reason)

        if self._peak_equity and equity < self._peak_equity * (1 - self.max_drawdown_pct):
            self._halted = True
            self._halt_reason = f"Max drawdown ({self.max_drawdown_pct:.0%})"
            logger.critical(self._halt_reason)

    @property
    def is_halted(self) -> bool:
        return self._halted

    @property
    def halt_reason(self) -> str:
        return self._halt_reason

    def peak_equity(self) -> Optional[float]:
        return self._peak_equity

    def drawdown_pct(self, equity: float) -> float:
        if not self._peak_equity or self._peak_equity <= 0:
            return 0.0
        return max(0.0, (self._peak_equity - equity) / self._peak_equity)

    def calculate_position_size(
        self,
        equity: float,
        entry_price: float,
        atr: float,
        side: str = "long",
    ) -> Optional[PositionSizeResult]:
        if equity <= 0 or entry_price <= 0 or atr <= 0:
            return None

        stop_distance = atr * self.atr_stop_mult
        risk_amount = equity * self.risk_per_trade
        quantity = risk_amount / stop_distance

        if side == "long":
            stop_price = entry_price - stop_distance
            take_profit = entry_price + (atr * self.atr_tp_mult)
        else:
            stop_price = entry_price + stop_distance
            take_profit = entry_price - (atr * self.atr_tp_mult)

        # Cap notional at 95% of equity
        if quantity * entry_price > equity * 0.95:
            quantity = (equity * 0.95) / entry_price

        if quantity <= 0:
            return None

        return PositionSizeResult(
            quantity=quantity,
            risk_amount=risk_amount,
            stop_price=stop_price,
            take_profit_price=take_profit,
        )

    def trailing_stop(self, entry_price: float, highest_price: float, atr: float) -> float:
        """Long trailing stop from peak price since entry."""
        return highest_price - (atr * self.trailing_atr_mult)
