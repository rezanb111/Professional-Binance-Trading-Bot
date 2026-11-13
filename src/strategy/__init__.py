"""Strategy package – import all strategies so they register themselves."""

from src.strategy.base import get_strategy, list_strategies, STRATEGY_REGISTRY
from src.strategy.ema_rsi import EmaRsiStrategy
from src.strategy.macd import MacdStrategy
from src.strategy.bollinger import BollingerStrategy
from src.strategy.supertrend import SupertrendStrategy
from src.strategy.breakout import BreakoutStrategy
from src.strategy.rsi_reversion import RsiReversionStrategy
from src.strategy.ichimoku import IchimokuStrategy

__all__ = [
    "get_strategy",
    "list_strategies",
    "STRATEGY_REGISTRY",
    "EmaRsiStrategy",
    "MacdStrategy",
    "BollingerStrategy",
    "SupertrendStrategy",
    "BreakoutStrategy",
    "RsiReversionStrategy",
    "IchimokuStrategy",
]
