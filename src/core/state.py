"""Shared state with paper portfolio and drawdown tracking."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PositionInfo:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    opened_at: datetime
    stop_price: Optional[float] = None
    take_profit: Optional[float] = None
    fees_paid: float = 0.0
    signal_score: int = 0


@dataclass
class BotState:
    trading_enabled: bool = False
    shutdown_requested: bool = False

    risk_profile: str = "medium"
    strategy_name: str = "ema_rsi"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    paper_mode: bool = True
    testnet: bool = False

    paper_cash: float = 1000.0
    paper_start_balance: float = 1000.0

    equity: float = 1000.0
    max_drawdown_pct: float = 0.0
    last_signal: str = "flat"
    last_signal_score: int = 0
    last_price: float = 0.0
    last_update: Optional[datetime] = None
    position: Optional[PositionInfo] = None

    trades_today: int = 0
    realized_pnl_today: float = 0.0
    wins_today: int = 0
    losses_today: int = 0
    started_at: Optional[datetime] = None
    last_stop_loss_at: Optional[datetime] = None

    max_trades_per_day: int = 15
    cooldown_minutes_after_sl: int = 20

    pending_notifications: List[str] = field(default_factory=list)
    force_close: bool = False

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, **kwargs: Any) -> None:
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)
            self.last_update = datetime.now(timezone.utc)

    def add_notification(self, message: str) -> None:
        with self._lock:
            self.pending_notifications.append(message)

    def pop_notifications(self) -> List[str]:
        with self._lock:
            notes = self.pending_notifications[:]
            self.pending_notifications.clear()
            return notes

    def mark_equity(self) -> float:
        eq = self.paper_cash
        if self.position and self.last_price > 0:
            eq += self.position.quantity * self.last_price
        return eq

    def unrealized_pnl(self) -> Optional[float]:
        if not self.position or not self.last_price:
            return None
        return (self.last_price - self.position.entry_price) * self.position.quantity

    def can_open_new_trade(self) -> tuple[bool, str]:
        if self.trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit ({self.max_trades_per_day})"
        if self.last_stop_loss_at:
            elapsed = (datetime.now(timezone.utc) - self.last_stop_loss_at).total_seconds() / 60
            if elapsed < self.cooldown_minutes_after_sl:
                return False, f"Cooldownoldown {int(self.cooldown_minutes_after_sl - elapsed)}m"
        return True, ""

    def reset_paper(self, amount: float = 1000.0) -> None:
        with self._lock:
            self.paper_cash = amount
            self.paper_start_balance = amount
            self.equity = amount
            self.position = None
            self.trades_today = 0
            self.realized_pnl_today = 0.0
            self.wins_today = 0
            self.losses_today = 0
            self.last_stop_loss_at = None
            self.max_drawdown_pct = 0.0

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            pos = None
            if self.position:
                pos = {
                    "symbol": self.position.symbol,
                    "side": self.position.side,
                    "quantity": self.position.quantity,
                    "entry_price": self.position.entry_price,
                    "opened_at": self.position.opened_at.isoformat(),
                    "stop_price": self.position.stop_price,
                    "take_profit": self.position.take_profit,
                    "signal_score": self.position.signal_score,
                }
            upnl = None
            if self.position and self.last_price:
                upnl = (self.last_price - self.position.entry_price) * self.position.quantity
            total_eq = self.paper_cash
            if self.position and self.last_price:
                total_eq += self.position.quantity * self.last_price

            return {
                "trading_enabled": self.trading_enabled,
                "risk_profile": self.risk_profile,
                "strategy_name": self.strategy_name,
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "paper_mode": self.paper_mode,
                "testnet": self.testnet,
                "paper_cash": self.paper_cash,
                "equity": total_eq,
                "paper_start_balance": self.paper_start_balance,
                "max_drawdown_pct": self.max_drawdown_pct,
                "last_signal": self.last_signal,
                "last_signal_score": self.last_signal_score,
                "last_price": self.last_price,
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "position": pos,
                "unrealized_pnl": upnl,
                "trades_today": self.trades_today,
                "realized_pnl_today": self.realized_pnl_today,
                "wins_today": self.wins_today,
                "losses_today": self.losses_today,
                "started_at": self.started_at.isoformat() if self.started_at else None,
            }
