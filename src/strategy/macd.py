from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, SignalResult, register_strategy


@register_strategy
class MacdStrategy(BaseStrategy):
    name = "macd"
    description = "MACD crossover with histogram confirmation"

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < 40:
            return SignalResult("flat", 0, "insufficient data")
        df = add_all_indicators(df)
        curr, prev = df.iloc[-1], df.iloc[-2]
        if pd.isna(curr.get("macd")) or pd.isna(curr.get("macd_signal")):
            return SignalResult("flat", 0, "macd not ready")

        bullish = prev["macd"] <= prev["macd_signal"] and curr["macd"] > curr["macd_signal"]
        bearish = prev["macd"] >= prev["macd_signal"] and curr["macd"] < curr["macd_signal"]
        score = 50
        if curr.get("macd_hist", 0) > 0:
            score += 20
        if curr.get("adx", 0) >= self.params.get("min_adx", 18):
            score += 15
        if curr.get("volume_ratio", 1) >= self.params.get("min_volume_ratio", 1.0):
            score += 15

        if bullish and score >= self.params.get("min_signal_score", 60):
            logger.info("macd LONG score={}", score)
            return SignalResult("long", score, "MACD cross up")
        if bearish:
            return SignalResult("exit", score, "MACD cross down")
        return SignalResult("flat", score, "no cross")
