"""Simple trade journal – append-only CSV for later analysis."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loguru import logger

JOURNAL_PATH = Path("logs") / "trades.csv"
HEADERS = [
    "timestamp",
    "event",
    "symbol",
    "side",
    "quantity",
    "price",
    "stop",
    "take_profit",
    "pnl",
    "strategy",
    "risk_profile",
    "dry_run",
]


def _ensure_file() -> None:
    JOURNAL_PATH.parent.mkdir(exist_ok=True)
    if not JOURNAL_PATH.exists():
        with open(JOURNAL_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)


def log_trade(
    event: str,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    stop: Optional[float] = None,
    take_profit: Optional[float] = None,
    pnl: Optional[float] = None,
    strategy: str = "",
    risk_profile: str = "",
    dry_run: bool = True,
) -> None:
    try:
        _ensure_file()
        with open(JOURNAL_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [
                    datetime.now(timezone.utc).isoformat(),
                    event,
                    symbol,
                    side,
                    f"{quantity:.8f}",
                    f"{price:.8f}",
                    f"{stop:.8f}" if stop is not None else "",
                    f"{take_profit:.8f}" if take_profit is not None else "",
                    f"{pnl:.4f}" if pnl is not None else "",
                    strategy,
                    risk_profile,
                    str(dry_run),
                ]
            )
    except Exception as e:
        logger.warning("Journal write failed: {}", e)


def load_recent(limit: int = 20) -> list[dict]:
    if not JOURNAL_PATH.exists():
        return []
    rows = []
    with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows[-limit:]
