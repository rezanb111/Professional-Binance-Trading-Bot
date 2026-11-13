from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, SignalResult, register_strategy


@register_strategy
class SupertrendStrategy(BaseStrategy):
    name = "supertrend"
    description = "ATR Supertrend-style trend following"

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < 30:
            return SignalResult("flat", 0, "insufficient data")
        df = add_all_indicators(df, self.params)
        curr, prev = df.iloc[-1], df.iloc[-2]
        if pd.isna(curr.get("st_lower")):
            return SignalResult("flat", 0, "st not ready")

        cross_up = prev["close"] <= prev["st_lower"] and curr["close"] > curr["st_lower"]
        score = 55
        if curr.get("adx", 0) >= self.params.get("min_adx", 18):
            score += 25
        if curr.get("volume_ratio", 1) >= 1.0:
            score += 20

        if cross_up and score >= self.params.get("min_signal_score", 60):
            logger.info("supertrend LONG score={}", score)
            return SignalResult("long", score, "price above ST lower")
        if curr["close"] < curr["st_lower"]:
            return SignalResult("exit", score, "below ST")
        return SignalResult("flat", score, "no cross")
