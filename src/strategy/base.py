"""Abstract strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal, Optional

import pandas as pd

Signal = Literal["long", "flat", "exit"]


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Signal:
        """
        Analyze the latest candles and return a signal.

        Returns:
            "long"  – open / keep long position
            "flat"  – no position / do nothing
            "exit"  – close existing position
        """
        ...

    def get_stop_distance(self, df: pd.DataFrame) -> Optional[float]:
        """Return ATR-based stop distance if available."""
        if df.empty or "atr" not in df.columns:
            return None
        atr = df["atr"].iloc[-1]
        if pd.isna(atr):
            return None
        multiplier = self.params.get("atr_stop_multiplier", 2.0)
        return float(atr * multiplier)
