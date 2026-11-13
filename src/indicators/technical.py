"""Comprehensive technical indicators."""

from __future__ import annotations

import pandas as pd
import ta


def add_all_indicators(df: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    """
    Enrich OHLCV with a rich set of indicators used across strategies.
    """
    if df.empty:
        return df

    p = params or {}
    df = df.copy()

    # Trend
    df["ema_9"] = ta.trend.ema_indicator(df["close"], window=9)
    df["ema_21"] = ta.trend.ema_indicator(df["close"], window=21)
    df["ema_50"] = ta.trend.ema_indicator(df["close"], window=50)
    df["ema_200"] = ta.trend.ema_indicator(df["close"], window=200)
    df["sma_20"] = ta.trend.sma_indicator(df["close"], window=20)
    df["sma_50"] = ta.trend.sma_indicator(df["close"], window=50)

    # MACD
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    # Momentum
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["stoch_k"] = ta.momentum.stoch(df["high"], df["low"], df["close"])
    df["stoch_d"] = ta.momentum.stoch_signal(df["high"], df["low"], df["close"])
    df["williams_r"] = ta.momentum.williams_r(df["high"], df["low"], df["close"])

    # Volatility
    df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["bb_high"] = bb.bollinger_hband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_low"] = bb.bollinger_lband()
    df["bb_width"] = (df["bb_high"] - df["bb_low"]) / df["bb_mid"]

    # Supertrend (approximation using ATR)
    atr_mult = p.get("supertrend_mult", 3.0)
    hl2 = (df["high"] + df["low"]) / 2
    df["st_upper"] = hl2 + atr_mult * df["atr"]
    df["st_lower"] = hl2 - atr_mult * df["atr"]

    # Volume
    df["volume_ma"] = df["volume"].rolling(window=20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma"]
    df["obv"] = ta.volume.on_balance_volume(df["close"], df["volume"])

    # ADX (trend strength)
    adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14)
    df["adx"] = adx.adx()
    df["di_plus"] = adx.adx_pos()
    df["di_minus"] = adx.adx_neg()

    # Ichimoku basic
    high_9 = df["high"].rolling(window=9).max()
    low_9 = df["low"].rolling(window=9).min()
    df["tenkan"] = (high_9 + low_9) / 2
    high_26 = df["high"].rolling(window=26).max()
    low_26 = df["low"].rolling(window=26).min()
    df["kijun"] = (high_26 + low_26) / 2
    df["senkou_a"] = ((df["tenkan"] + df["kijun"]) / 2).shift(26)
    high_52 = df["high"].rolling(window=52).max()
    low_52 = df["low"].rolling(window=52).min()
    df["senkou_b"] = ((high_52 + low_52) / 2).shift(26)

    # Donchian
    df["donchian_high"] = df["high"].rolling(window=20).max()
    df["donchian_low"] = df["low"].rolling(window=20).min()

    return df


def market_summary(df: pd.DataFrame) -> dict:
    """Generate a human-readable technical summary."""
    if df.empty or len(df) < 50:
        return {"error": "Not enough data"}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    trend = "Neutral"
    if last["close"] > last.get("ema_50", last["close"]) and last.get("ema_50", 0) > last.get("ema_200", 0):
        trend = "Bullish (Uptrend)"
    elif last["close"] < last.get("ema_50", last["close"]) and last.get("ema_50", 0) < last.get("ema_200", 0):
        trend = "Bearish (Downtrend)"

    rsi = last.get("rsi", 50)
    rsi_state = "Neutral"
    if rsi >= 70:
        rsi_state = "Overbought"
    elif rsi <= 30:
        rsi_state = "Oversold"

    adx = last.get("adx", 0)
    strength = "Weak"
    if adx >= 25:
        strength = "Strong"
    elif adx >= 20:
        strength = "Moderate"

    bb_pos = "Middle"
    if last["close"] >= last.get("bb_high", last["close"]):
        bb_pos = "Upper Band (Potential exhaustion)"
    elif last["close"] <= last.get("bb_low", last["close"]):
        bb_pos = "Lower Band (Potential bounce)"

    return {
        "price": float(last["close"]),
        "trend": trend,
        "rsi": float(rsi),
        "rsi_state": rsi_state,
        "adx": float(adx) if pd.notna(adx) else 0,
        "trend_strength": strength,
        "atr": float(last.get("atr", 0)),
        "bb_position": bb_pos,
        "volume_ratio": float(last.get("volume_ratio", 1)),
        "macd_hist": float(last.get("macd_hist", 0)),
        "ema_9": float(last.get("ema_9", 0)),
        "ema_21": float(last.get("ema_21", 0)),
        "ema_50": float(last.get("ema_50", 0)),
    }
