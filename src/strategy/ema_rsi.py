"""EMA Crossover + RSI + Volume confirmation strategy."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_indicators
from src.strategy.base import BaseStrategy, Signal


class EmaRsiStrategy(BaseStrategy):
    """
    Classic trend-following strategy with filters.

    Entry (long):
      - Fast EMA crosses above Slow EMA
      - RSI is not overbought
      - Volume is above its moving average (optional confirmation)

    Exit:
      - Fast EMA crosses below Slow EMA
      - or RSI becomes extremely overbought
    """

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 50:
            return "flat"

        params = self.params
        df = add_indicators(
            df,
            ema_fast=params.get("ema_fast", 12),
            ema_slow=params.get("ema_slow", 26),
        )

        # Need at least two bars for crossover detection
        if len(df) < 2:
            return "flat"

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        # Skip if indicators not ready
        if any(pd.isna(curr[c]) for c in ["ema_fast", "ema_slow", "rsi", "atr"]):
            return "flat"

        # --- Crossover detection ---
        bullish_cross = (
            prev["ema_fast"] <= prev["ema_slow"]
            and curr["ema_fast"] > curr["ema_slow"]
        )
        bearish_cross = (
            prev["ema_fast"] >= prev["ema_slow"]
            and curr["ema_fast"] < curr["ema_slow"]
        )

        rsi = curr["rsi"]
        volume_ok = curr.get("volume_ratio", 1.0) >= params.get("min_volume_ratio", 1.0)

        # --- Entry logic ---
        if bullish_cross and rsi < params.get("rsi_overbought", 65) and volume_ok:
            logger.info(
                "LONG signal | EMA cross + RSI={:.1f} | vol_ratio={:.2f}",
                rsi,
                curr.get("volume_ratio", 0),
            )
            return "long"

        # --- Exit logic ---
        if bearish_cross or rsi > 78:
            logger.info("EXIT signal | bearish cross or RSI extreme ({:.1f})", rsi)
            return "exit"

        return "flat"
