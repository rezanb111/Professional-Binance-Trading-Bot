"""Donchian Channel breakout strategy."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, Signal, register_strategy


@register_strategy
class BreakoutStrategy(BaseStrategy):
    name = "breakout"
    description = "Donchian Channel breakout (20-period high/low)"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 25:
            return "flat"

        df = add_all_indicators(df)
        # Use previous completed channel to avoid look-ahead
        curr = df.iloc[-1]
        channel_high = df["donchian_high"].iloc[-2]
        channel_low = df["donchian_low"].iloc[-2]

        if pd.isna(channel_high):
            return "flat"

        if curr["close"] > channel_high and curr.get("volume_ratio", 1) > 1.1:
            logger.info("breakout → LONG (Donchian high)")
            return "long"

        if curr["close"] < channel_low:
            return "exit"

        return "flat"
