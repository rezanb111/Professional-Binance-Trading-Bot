"""Basic Ichimoku cloud strategy."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, Signal, register_strategy


@register_strategy
class IchimokuStrategy(BaseStrategy):
    name = "ichimoku"
    description = "Ichimoku Cloud – price above cloud + Tenkan/Kijun cross"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 60:
            return "flat"

        df = add_all_indicators(df)
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(curr.get("tenkan")) or pd.isna(curr.get("senkou_a")):
            return "flat"

        cloud_top = max(curr["senkou_a"], curr["senkou_b"])
        cloud_bottom = min(curr["senkou_a"], curr["senkou_b"])

        above_cloud = curr["close"] > cloud_top
        below_cloud = curr["close"] < cloud_bottom

        tk_cross_up = prev["tenkan"] <= prev["kijun"] and curr["tenkan"] > curr["kijun"]
        tk_cross_down = prev["tenkan"] >= prev["kijun"] and curr["tenkan"] < curr["kijun"]

        if above_cloud and tk_cross_up:
            logger.info("ichimoku → LONG")
            return "long"

        if below_cloud or tk_cross_down:
            return "exit"

        return "flat"
