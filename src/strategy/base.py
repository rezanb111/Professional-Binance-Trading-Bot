"""Abstract strategy interface + registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Literal, Optional, Type

import pandas as pd

Signal = Literal["long", "flat", "exit"]


class BaseStrategy(ABC):
    name: str = "base"
    description: str = ""

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Signal:
        ...

    def get_stop_distance(self, df: pd.DataFrame) -> Optional[float]:
        if df.empty or "atr" not in df.columns:
            return None
        atr = df["atr"].iloc[-1]
        if pd.isna(atr):
            return None
        return float(atr * self.params.get("atr_stop_multiplier", 2.0))


# Global registry
STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {}


def register_strategy(cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
    STRATEGY_REGISTRY[cls.name] = cls
    return cls


def get_strategy(name: str, params: dict) -> BaseStrategy:
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name](params)


def list_strategies() -> Dict[str, str]:
    return {k: v.description for k, v in STRATEGY_REGISTRY.items()}
