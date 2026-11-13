"""Utility helpers."""

from __future__ import annotations

from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_price(price: float, precision: int = 8) -> str:
    return f"{price:.{precision}f}".rstrip("0").rstrip(".")
