"""Shared runtime state between trading engine and Telegram."""

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


@dataclass
class BotState:
    """Thread-safe shared state."""

    # Control flags
    trading_enabled: bool = False
    shutdown_requested: bool = False

    # Config (mutable at runtime)
    risk_profile: str = "medium"
    strategy_name: str = "ema_rsi"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    dry_run: bool = True
    testnet: bool = True

    # Live data
    equity: float = 0.0
    last_signal: str = "flat"
    last_price: float = 0.0
    last_update: Optional[datetime] = None
    position: Optional[PositionInfo] = None

    # Stats
    trades_today: int = 0
    realized_pnl_today: float = 0.0
    wins_today: int = 0
    losses_today: int = 0
    started_at: Optional[datetime] = None
    last_stop_loss_at: Optional[datetime] = None

    # Limits
    max_trades_per_day: int = 10
    cooldown_minutes_after_sl: int = 30

    # Messages for Telegram notifications
    pending_notifications: List[str] = field(default_factory=list)

    # Special commands from Telegram to engine
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

    def unrealized_pnl(self) -> Optional[float]:
        if not self.position or not self.last_price:
            return None
        return (self.last_price - self.position.entry_price) * self.position.quantity

    def can_open_new_trade(self) -> tuple[bool, str]:
        if self.trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit reached ({self.max_trades_per_day})"
        if self.last_stop_loss_at:
            elapsed = (datetime.now(timezone.utc) - self.last_stop_loss_at).total_seconds() / 60
            if elapsed < self.cooldown_minutes_after_sl:
                remaining = int(self.cooldown_minutes_after_sl - elapsed)
                return False, f"Cooldownoldown after SL: {remaining} min left"
        return True, ""

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
                }
            upnl = self.unrealized_pnl()
            return {
                "trading_enabled": self.trading_enabled,
                "risk_profile": self.risk_profile,
                "strategy_name": self.strategy_name,
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "dry_run": self.dry_run,
                "testnet": self.testnet,
                "equity": self.equity,
                "last_signal": self.last_signal,
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
