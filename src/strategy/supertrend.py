"""Supertrend-like strategy using ATR bands."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, Signal, register_strategy


@register_strategy
class SupertrendStrategy(BaseStrategy):
    name = "supertrend"
    description = "ATR-based Supertrend style trend following"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 30:
            return "flat"

        df = add_all_indicators(df, self.params)
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(curr.get("st_lower")):
            return "flat"

        # Simple logic: price crosses above lower band → long, below → exit
        if prev["close"] <= prev["st_lower"] and curr["close"] > curr["st_lower"]:
            logger.info("supertrend → LONG")
            return "long"

        if curr["close"] < curr["st_lower"]:
            return "exit"

        return "flat"
