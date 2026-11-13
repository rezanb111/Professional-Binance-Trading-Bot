"""EMA Crossover + RSI + Volume."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, Signal, register_strategy


@register_strategy
class EmaRsiStrategy(BaseStrategy):
    name = "ema_rsi"
    description = "EMA crossover + RSI filter + volume confirmation (trend following)"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 60:
            return "flat"

        df = add_all_indicators(df, self.params)
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        if any(pd.isna(curr.get(c)) for c in ["ema_9", "ema_21", "rsi", "atr"]):
            return "flat"

        bullish = prev["ema_9"] <= prev["ema_21"] and curr["ema_9"] > curr["ema_21"]
        bearish = prev["ema_9"] >= prev["ema_21"] and curr["ema_9"] < curr["ema_21"]

        rsi = curr["rsi"]
        vol_ok = curr.get("volume_ratio", 1) >= self.params.get("min_volume_ratio", 1.0)

        if bullish and rsi < self.params.get("rsi_overbought", 65) and vol_ok:
            logger.info("ema_rsi → LONG | RSI={:.1f}", rsi)
            return "long"

        if bearish or rsi > 78:
            return "exit"

        return "flat"
