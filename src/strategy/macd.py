"""MACD Crossover strategy."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, Signal, register_strategy


@register_strategy
class MacdStrategy(BaseStrategy):
    name = "macd"
    description = "MACD line / signal line crossover with histogram filter"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 40:
            return "flat"

        df = add_all_indicators(df)
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(curr.get("macd")) or pd.isna(curr.get("macd_signal")):
            return "flat"

        bullish = prev["macd"] <= prev["macd_signal"] and curr["macd"] > curr["macd_signal"]
        bearish = prev["macd"] >= prev["macd_signal"] and curr["macd"] < curr["macd_signal"]

        if bullish and curr.get("macd_hist", 0) > 0:
            logger.info("macd → LONG")
            return "long"

        if bearish:
            return "exit"

        return "flat"
