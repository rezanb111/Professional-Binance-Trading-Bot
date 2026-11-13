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
    started_at: Optional[datetime] = None

    # Messages for Telegram notifications
    pending_notifications: List[str] = field(default_factory=list)

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
            return {
                "trading_enabled": self.trading_enabled,
                "risk_profile": self.risk_profile,
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "dry_run": self.dry_run,
                "testnet": self.testnet,
                "equity": self.equity,
                "last_signal": self.last_signal,
                "last_price": self.last_price,
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "position": pos,
                "trades_today": self.trades_today,
                "realized_pnl_today": self.realized_pnl_today,
                "started_at": self.started_at.isoformat() if self.started_at else None,
            }
