"""Technical indicators used by strategies."""

from __future__ import annotations

import pandas as pd
import ta


def add_indicators(
    df: pd.DataFrame,
    ema_fast: int = 12,
    ema_slow: int = 26,
    rsi_period: int = 14,
    atr_period: int = 14,
) -> pd.DataFrame:
    """
    Enrich OHLCV DataFrame with technical indicators.

    Expects columns: open, high, low, close, volume
    """
    if df.empty:
        return df

    df = df.copy()

    df["ema_fast"] = ta.trend.ema_indicator(df["close"], window=ema_fast)
    df["ema_slow"] = ta.trend.ema_indicator(df["close"], window=ema_slow)
    df["rsi"] = ta.momentum.rsi(df["close"], window=rsi_period)
    df["atr"] = ta.volatility.average_true_range(
        df["high"], df["low"], df["close"], window=atr_period
    )

    # Volume moving average for confirmation
    df["volume_ma"] = df["volume"].rolling(window=20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma"]

    return df
