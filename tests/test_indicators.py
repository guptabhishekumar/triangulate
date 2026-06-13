"""
Correctness tests for the hand-written indicator math.

The whole project rests on the claim that our EMA/MACD is implemented correctly
and uses the ``adjust=False`` convention. We prove it here against an
*independent oracle* — pandas' ``ewm`` — which is used ONLY in the test-suite,
never in production code (the assignment forbids built-in indicators in the
backtests themselves).

Run:  python -m pytest tests/ -q       (any of the project venvs works)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.indicators import ema, macd, ema_step  # noqa: E402
from shared.signals import crossover_signals  # noqa: E402


@pytest.fixture
def prices() -> np.ndarray:
    rng = np.random.default_rng(42)
    steps = rng.normal(0, 0.5, size=2000)
    return 100.0 + np.cumsum(steps)


@pytest.mark.parametrize("period", [1, 2, 9, 12, 26, 200])
def test_ema_matches_pandas_adjust_false(prices, period):
    ours = ema(prices, period)
    oracle = pd.Series(prices).ewm(span=period, adjust=False).mean().to_numpy()
    assert np.allclose(ours, oracle, rtol=0, atol=1e-10)


def test_ema_is_not_adjust_true(prices):
    """Guard against accidentally matching the (wrong) convergent-weighted EMA."""
    ours = ema(prices, 12)
    adjust_true = pd.Series(prices).ewm(span=12, adjust=True).mean().to_numpy()
    # They converge later but must differ in the warmup region.
    assert not np.allclose(ours[:50], adjust_true[:50], atol=1e-6)


def test_ema_seed_is_first_value(prices):
    assert ema(prices, 12)[0] == prices[0]


def test_macd_matches_pandas(prices):
    macd_line, signal_line, hist = macd(prices, 12, 26, 9)
    s = pd.Series(prices)
    ema_fast = s.ewm(span=12, adjust=False).mean()
    ema_slow = s.ewm(span=26, adjust=False).mean()
    macd_o = (ema_fast - ema_slow)
    signal_o = macd_o.ewm(span=9, adjust=False).mean()
    assert np.allclose(macd_line, macd_o.to_numpy(), atol=1e-10)
    assert np.allclose(signal_line, signal_o.to_numpy(), atol=1e-10)
    assert np.allclose(hist, (macd_o - signal_o).to_numpy(), atol=1e-10)


def test_ema_step_matches_vectorised(prices):
    """The incremental O(1) update (used by Nautilus) equals the batch EMA."""
    period = 12
    batch = ema(prices, period)
    prev, seeded = 0.0, False
    for i, x in enumerate(prices):
        prev = ema_step(prev, x, period, seeded)
        seeded = True
        assert abs(prev - batch[i]) < 1e-9


def test_crossover_detects_only_on_change():
    # Construct two lines that cross up at index 3 and down at index 6.
    macd_line = np.array([-2.0, -1.0, -0.5, 0.5, 1.0, 0.5, -0.5, -1.0])
    signal_line = np.zeros_like(macd_line)
    up, dn = crossover_signals(macd_line, signal_line, warmup=0)
    assert up.sum() == 1 and up[3]
    assert dn.sum() == 1 and dn[6]


def test_crossover_warmup_mask():
    macd_line = np.array([-1.0, 1.0, -1.0, 1.0, -1.0, 1.0])
    signal_line = np.zeros_like(macd_line)
    up, dn = crossover_signals(macd_line, signal_line, warmup=4)
    # Nothing before index 4.
    assert not up[:4].any() and not dn[:4].any()
