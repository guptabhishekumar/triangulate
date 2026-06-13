"""
Hand-written MACD / EMA — the heart of the assignment.

The brief requires the indicator math to be implemented *by hand* (no TA-Lib,
no ``vbt.MACD``, no MQL5 ``iMACD``). This module is the single, framework-
agnostic implementation that the vectorbt and Nautilus legs both import, and
that the MQL5 Expert Advisor mirrors line-for-line.

EMA convention (fixed everywhere)
---------------------------------
Recursive exponential moving average, ``adjust=False`` semantics:

    alpha       = 2 / (period + 1)
    ema[0]      = price[0]                         # first value seeds the filter
    ema[t]      = alpha*price[t] + (1-alpha)*ema[t-1]

This is identical to ``pandas.Series.ewm(span=period, adjust=False).mean()`` —
which we use only in the test-suite as an independent oracle, never in
production code. Choosing one explicit seeding rule is what lets three
different engines agree numerically (see ``tests/test_indicators.py`` and the
README "Why results differ" section).
"""
from __future__ import annotations

import numpy as np


def ema(values: np.ndarray, period: int) -> np.ndarray:
    """Recursive EMA (adjust=False, first-value seed). Pure, dependency-free."""
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("ema expects a 1-D array")
    if period < 1:
        raise ValueError("period must be >= 1")
    n = x.size
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    alpha = 2.0 / (period + 1.0)
    out[0] = x[0]
    for i in range(1, n):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


def macd(
    close: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (macd_line, signal_line, histogram).

    macd_line   = EMA(close, fast) - EMA(close, slow)
    signal_line = EMA(macd_line, signal)
    histogram   = macd_line - signal_line
    """
    close = np.asarray(close, dtype=np.float64)
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# A single incremental EMA step, used by the event-driven Nautilus indicator so
# it can update bar-by-bar with O(1) work instead of recomputing the whole
# series. Mathematically identical to the vectorised `ema` above.
def ema_step(prev: float, value: float, period: int, seeded: bool) -> float:
    """One recursive EMA update. If ``seeded`` is False, returns ``value`` (seed)."""
    if not seeded:
        return float(value)
    alpha = 2.0 / (period + 1.0)
    return alpha * float(value) + (1.0 - alpha) * float(prev)
