"""EMA crossover + RSI + volume + ADX scored strategy."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.indicators.technical import add_all_indicators
from src.strategy.base import BaseStrategy, SignalResult, register_strategy


@register_strategy
class EmaRsiStrategy(BaseStrategy):
    name = "ema_rsi"
    description = "EMA crossover + RSI + volume + ADX (scored)"

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < 60:
            return SignalResult("flat", 0, "insufficient data")

        df = add_all_indicators(df, self.params)
        curr, prev = df.iloc[-1], df.iloc[-2]

        needed = ["ema_9", "ema_21", "rsi", "atr", "adx", "volume_ratio"]
        if any(pd.isna(curr.get(c)) for c in needed):
            return SignalResult("flat", 0, "indicators not ready")

        bullish = prev["ema_9"] <= prev["ema_21"] and curr["ema_9"] > curr["ema_21"]
        bearish = prev["ema_9"] >= prev["ema_21"] and curr["ema_9"] < curr["ema_21"]

        score = 0
        reasons = []

        if bullish:
            score += 40
            reasons.append("EMA cross up")
        if curr["close"] > curr.get("ema_50", curr["close"]):
            score += 15
            reasons.append("above EMA50")
        if curr["rsi"] < self.params.get("rsi_overbought", 65):
            score += 15
            reasons.append("RSI ok")
        if curr["volume_ratio"] >= self.params.get("min_volume_ratio", 1.0):
            score += 15
            reasons.append("volume")
        if curr["adx"] >= self.params.get("min_adx", 18):
            score += 15
            reasons.append("ADX trend")

        min_score = self.params.get("min_signal_score", 60)

        if bullish and score >= min_score:
            logger.info("ema_rsi LONG score={} | {}", score, ", ".join(reasons))
            return SignalResult("long", score, ", ".join(reasons))

        if bearish or curr["rsi"] > 78:
            return SignalResult("exit", score, "bearish cross or RSI extreme")

        return SignalResult("flat", score, ", ".join(reasons) or "no setup")
