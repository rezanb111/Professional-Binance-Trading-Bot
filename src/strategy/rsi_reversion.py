"""Classic RSI mean-reversion."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, Signal, register_strategy


@register_strategy
class RsiReversionStrategy(BaseStrategy):
    name = "rsi_reversion"
    description = "RSI oversold/overbought mean reversion"

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 20:
            return "flat"

        df = add_all_indicators(df)
        curr = df.iloc[-1]
        rsi = curr.get("rsi", 50)

        if pd.isna(rsi):
            return "flat"

        oversold = self.params.get("rsi_oversold", 30)
        overbought = self.params.get("rsi_overbought", 70)

        if rsi <= oversold:
            logger.info("rsi_reversion → LONG (RSI={:.1f})", rsi)
            return "long"

        if rsi >= overbought:
            return "exit"

        return "flat"
