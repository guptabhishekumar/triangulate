"""
Crossover signal generation — shared by every engine.

A crossover is a *change of sign* of ``(macd_line - signal_line)`` between two
consecutive bars. Using the previous-vs-current pair (rather than the raw
``macd > signal`` condition) means we emit a signal only on the bar where the
lines actually cross, never on every bar they happen to be separated.

    cross_up[t]   = macd[t-1] <= signal[t-1]  AND  macd[t] > signal[t]
    cross_down[t] = macd[t-1] >= signal[t-1]  AND  macd[t] < signal[t]

Both arrays are masked to ``False`` for the first ``warmup`` bars so that every
engine begins trading on exactly the same bar, independent of how it warms up
its own indicators internally.
"""
from __future__ import annotations

import numpy as np


def crossover_signals(
    macd_line: np.ndarray,
    signal_line: np.ndarray,
    warmup: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return boolean (entries, exits) for a long/flat MACD-crossover strategy.

    entries  -> bullish cross (MACD crosses above signal)  -> go long
    exits    -> bearish cross (MACD crosses below signal)   -> exit to flat
    """
    m = np.asarray(macd_line, dtype=np.float64)
    s = np.asarray(signal_line, dtype=np.float64)
    if m.shape != s.shape:
        raise ValueError("macd_line and signal_line must have the same shape")

    prev_m = np.empty_like(m)
    prev_s = np.empty_like(s)
    prev_m[0], prev_s[0] = np.nan, np.nan
    prev_m[1:], prev_s[1:] = m[:-1], s[:-1]

    cross_up = (prev_m <= prev_s) & (m > s)
    cross_down = (prev_m >= prev_s) & (m < s)

    if warmup > 0:
        cross_up[:warmup] = False
        cross_down[:warmup] = False

    # The first bar can never be a valid cross (no previous bar).
    cross_up[0] = False
    cross_down[0] = False
    return cross_up, cross_down
