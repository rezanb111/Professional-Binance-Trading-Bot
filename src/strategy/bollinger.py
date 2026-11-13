"""Bollinger Bands mean-reversion strategy."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, Signal, register_strategy


@register_strategy
class BollingerStrategy(BaseStrategy):
    name = "bollinger"
    description = "Bollinger Bands mean reversion (buy lower band, exit mid/upper)"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 30:
            return "flat"

        df = add_all_indicators(df)
        curr = df.iloc[-1]

        if pd.isna(curr.get("bb_low")):
            return "flat"

        # Mean reversion long when price touches/closes below lower band + RSI oversold
        if curr["close"] <= curr["bb_low"] and curr.get("rsi", 50) < 35:
            logger.info("bollinger → LONG (lower band)")
            return "long"

        # Exit when price returns to middle or upper band
        if curr["close"] >= curr["bb_mid"]:
            return "exit"

        return "flat"
