from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, SignalResult, register_strategy


@register_strategy
class IchimokuStrategy(BaseStrategy):
    name = "ichimoku"
    description = "Ichimoku cloud + TK cross"

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < 60:
            return SignalResult("flat", 0, "insufficient data")
        df = add_all_indicators(df)
        curr, prev = df.iloc[-1], df.iloc[-2]
        if pd.isna(curr.get("tenkan")) or pd.isna(curr.get("senkou_a")):
            return SignalResult("flat", 0, "ichimoku not ready")

        cloud_top = max(curr["senkou_a"], curr["senkou_b"])
        cloud_bottom = min(curr["senkou_a"], curr["senkou_b"])
        above = curr["close"] > cloud_top
        below = curr["close"] < cloud_bottom
        tk_up = prev["tenkan"] <= prev["kijun"] and curr["tenkan"] > curr["kijun"]
        tk_down = prev["tenkan"] >= prev["kijun"] and curr["tenkan"] < curr["kijun"]

        score = 40
        if above:
            score += 30
        if tk_up:
            score += 30

        if above and tk_up and score >= self.params.get("min_signal_score", 60):
            logger.info("ichimoku LONG score={}", score)
            return SignalResult("long", score, "above cloud + TK cross")
        if below or tk_down:
            return SignalResult("exit", score, "below cloud or TK down")
        return SignalResult("flat", score, "no ichimoku setup")
