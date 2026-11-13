from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, SignalResult, register_strategy


@register_strategy
class BreakoutStrategy(BaseStrategy):
    name = "breakout"
    description = "Donchian channel breakout"

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < 25:
            return SignalResult("flat", 0, "insufficient data")
        df = add_all_indicators(df)
        curr = df.iloc[-1]
        channel_high = df["donchian_high"].iloc[-2]
        channel_low = df["donchian_low"].iloc[-2]
        if pd.isna(channel_high):
            return SignalResult("flat", 0, "channel not ready")

        score = 50
        if curr.get("volume_ratio", 1) > 1.1:
            score += 30
        if curr.get("adx", 0) >= self.params.get("min_adx", 18):
            score += 20

        if curr["close"] > channel_high and score >= self.params.get("min_signal_score", 60):
            logger.info("breakout LONG score={}", score)
            return SignalResult("long", score, "Donchian high break")
        if curr["close"] < channel_low:
            return SignalResult("exit", score, "Donchian low break")
        return SignalResult("flat", score, "inside channel")
