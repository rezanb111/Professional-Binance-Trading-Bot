from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, SignalResult, register_strategy


@register_strategy
class BollingerStrategy(BaseStrategy):
    name = "bollinger"
    description = "Bollinger mean reversion (lower band + RSI)"

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < 30:
            return SignalResult("flat", 0, "insufficient data")
        df = add_all_indicators(df)
        curr = df.iloc[-1]
        if pd.isna(curr.get("bb_low")):
            return SignalResult("flat", 0, "bb not ready")

        score = 40
        if curr["close"] <= curr["bb_low"]:
            score += 30
        if curr.get("rsi", 50) < 35:
            score += 30

        if curr["close"] <= curr["bb_low"] and curr.get("rsi", 50) < 35:
            if score >= self.params.get("min_signal_score", 60):
                logger.info("bollinger LONG score={}", score)
                return SignalResult("long", score, "lower band + RSI")
        if curr["close"] >= curr["bb_mid"]:
            return SignalResult("exit", score, "back to mid band")
        return SignalResult("flat", score, "no reversion setup")
