"""
Shared, framework-agnostic core for the MACD-crossover backtesting project.

Importing from here keeps the three engine legs (vectorbt, Nautilus Trader,
MetaTrader 5) numerically consistent: the same hand-written indicator math, the
same signal logic, the same metric definitions, and the same configuration.
"""
from . import config, data, indicators, metrics, signals  # noqa: F401
from .config import CFG  # noqa: F401

__all__ = ["CFG", "config", "data", "indicators", "metrics", "signals"]
__version__ = "1.0.0"
