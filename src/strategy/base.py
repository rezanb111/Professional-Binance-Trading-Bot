"""Strategy interface with scored signals."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Type

import pandas as pd

Signal = Literal["long", "flat", "exit"]


@dataclass
class SignalResult:
    signal: Signal
    score: int = 0          # 0–100 confidence
    reason: str = ""


class BaseStrategy(ABC):
    name: str = "base"
    description: str = ""

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        ...

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        return self.evaluate(df).signal


STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {}


def register_strategy(cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
    STRATEGY_REGISTRY[cls.name] = cls
    return cls


def get_strategy(name: str, params: dict) -> BaseStrategy:
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name](params)


def list_strategies() -> Dict[str, str]:
    return {k: v.description for k, v in STRATEGY_REGISTRY.items()}
