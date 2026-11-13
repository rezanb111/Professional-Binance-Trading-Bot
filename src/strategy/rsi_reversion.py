from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, SignalResult, register_strategy


@register_strategy
class RsiReversionStrategy(BaseStrategy):
    name = "rsi_reversion"
    description = "RSI oversold mean reversion"

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < 20:
            return SignalResult("flat", 0, "insufficient data")
        df = add_all_indicators(df)
        curr = df.iloc[-1]
        rsi = curr.get("rsi", 50)
        if pd.isna(rsi):
            return SignalResult("flat", 0, "rsi not ready")

        oversold = self.params.get("rsi_oversold", 30)
        overbought = self.params.get("rsi_overbought", 70)
        score = 40
        if rsi <= oversold:
            score += 40
        if curr.get("close", 0) <= curr.get("bb_low", 0):
            score += 20

        if rsi <= oversold and score >= self.params.get("min_signal_score", 60):
            logger.info("rsi_reversion LONG score={}", score)
            return SignalResult("long", score, f"RSI={rsi:.1f}")
        if rsi >= overbought:
            return SignalResult("exit", score, f"RSI={rsi:.1f} overbought")
        return SignalResult("flat", score, f"RSI={rsi:.1f}")
