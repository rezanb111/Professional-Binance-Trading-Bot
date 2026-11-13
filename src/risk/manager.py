"""Professional risk management layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from loguru import logger


@dataclass
class PositionSizeResult:
    quantity: float
    risk_amount: float
    stop_price: float
    take_profit_price: Optional[float]


class RiskManager:
    """
    Fixed-fractional risk + circuit breakers.

    Position size is calculated so that a stop-loss hit
    results in approximately `risk_per_trade` of equity loss.
    """

    def __init__(self, profile: dict, circuit_breaker: dict):
        self.risk_per_trade = profile["risk_per_trade"]
        self.atr_stop_mult = profile["atr_stop_multiplier"]
        self.atr_tp_mult = profile.get("atr_take_profit_multiplier", 3.0)
        self.max_positions = profile["max_positions"]

        self.max_daily_loss_pct = circuit_breaker.get("max_daily_loss_pct", 0.05)
        self.max_drawdown_pct = circuit_breaker.get("max_drawdown_pct", 0.15)

        self._day_start_equity: Optional[float] = None
        self._peak_equity: Optional[float] = None
        self._halted = False
        self._halt_reason: str = ""

    def update_equity(self, equity: float) -> None:
        """Call on every loop to track daily loss and drawdown."""
        now = datetime.now(timezone.utc)

        if self._day_start_equity is None or now.hour == 0 and now.minute < 5:
            self._day_start_equity = equity

        if self._peak_equity is None or equity > self._peak_equity:
            self._peak_equity = equity

        # Daily loss circuit breaker
        if self._day_start_equity and equity < self._day_start_equity * (1 - self.max_daily_loss_pct):
            self._halted = True
            self._halt_reason = f"Daily loss limit reached ({self.max_daily_loss_pct:.1%})"
            logger.critical(self._halt_reason)

        # Max drawdown circuit breaker
        if self._peak_equity and equity < self._peak_equity * (1 - self.max_drawdown_pct):
            self._halted = True
            self._halt_reason = f"Max drawdown limit reached ({self.max_drawdown_pct:.1%})"
            logger.critical(self._halt_reason)

    @property
    def is_halted(self) -> bool:
        return self._halted

    @property
    def halt_reason(self) -> str:
        return self._halt_reason

    def calculate_position_size(
        self,
        equity: float,
        entry_price: float,
        atr: float,
        side: str = "long",
    ) -> Optional[PositionSizeResult]:
        """
        Calculate quantity so that stop distance ≈ risk_per_trade of equity.
        """
        if equity <= 0 or entry_price <= 0 or atr <= 0:
            logger.warning("Invalid inputs for position sizing")
            return None

        stop_distance = atr * self.atr_stop_mult
        risk_amount = equity * self.risk_per_trade

        # Quantity = risk_amount / stop_distance
        quantity = risk_amount / stop_distance

        if side == "long":
            stop_price = entry_price - stop_distance
            take_profit = entry_price + (atr * self.atr_tp_mult)
        else:
            stop_price = entry_price + stop_distance
            take_profit = entry_price - (atr * self.atr_tp_mult)

        # Sanity checks
        if quantity * entry_price > equity * 0.95:
            logger.warning("Position size too large vs equity – reducing")
            quantity = (equity * 0.95) / entry_price

        if quantity <= 0:
            return None

        return PositionSizeResult(
            quantity=quantity,
            risk_amount=risk_amount,
            stop_price=stop_price,
            take_profit_price=take_profit,
        )
