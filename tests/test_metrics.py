"""
Tests for the shared metrics and the reference backtester.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.metrics import total_return, sharpe_ratio, max_drawdown, compute_metrics  # noqa: E402
from shared.reference_backtest import backtest_long_flat  # noqa: E402


def test_total_return_simple():
    eq = pd.Series([100.0, 110.0, 121.0])
    assert total_return(eq) == pytest.approx(0.21)


def test_max_drawdown_simple():
    # Peak 120 -> trough 90 => -25%.
    eq = pd.Series([100.0, 120.0, 90.0, 100.0])
    assert max_drawdown(eq) == pytest.approx(-0.25)


def test_sharpe_zero_vol_is_nan():
    eq = pd.Series([100.0, 100.0, 100.0])
    assert np.isnan(sharpe_ratio(eq, ann_factor=6048))


def test_sharpe_scales_with_ann_factor():
    rng = np.random.default_rng(0)
    eq = pd.Series(100.0 * np.cumprod(1 + rng.normal(0, 0.001, 1000)))
    s1 = sharpe_ratio(eq, ann_factor=252)
    s2 = sharpe_ratio(eq, ann_factor=252 * 24)
    assert s2 == pytest.approx(s1 * np.sqrt(24), rel=1e-6)


def test_reference_backtest_known_pnl():
    # Flat then rising open prices; one clean long trade.
    idx = pd.date_range("2024-01-01", periods=6, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "open":  [1.00, 1.00, 1.00, 1.10, 1.20, 1.20],
            "high":  [1.00, 1.00, 1.00, 1.10, 1.20, 1.20],
            "low":   [1.00, 1.00, 1.00, 1.10, 1.20, 1.20],
            "close": [1.00, 1.00, 1.00, 1.10, 1.20, 1.20],
            "volume": [1, 1, 1, 1, 1, 1],
        },
        index=idx,
    )
    entries = np.array([False, True, False, False, False, False])  # signal @ bar1
    exits = np.array([False, False, False, True, False, False])    # signal @ bar3
    res = backtest_long_flat(
        df, entries, exits, init_cash=100_000, size_units=10_000,
        fees_frac=0.0, fill="next_open",
    )
    # Enter at open[2]=1.00, exit at open[4]=1.20 => 10_000 * 0.20 = 2_000 profit.
    assert res.n_trades == 1
    assert res.trades[0]["pnl"] == pytest.approx(2_000.0)
    assert res.equity.iloc[-1] == pytest.approx(102_000.0)


def test_compute_metrics_roundtrip():
    eq = pd.Series([100.0, 101.0, 102.0, 101.0, 103.0])
    m = compute_metrics("test", eq, n_trades=3, ann_factor=6048)
    assert m.engine == "test"
    assert m.n_trades == 3
    assert m.total_return == pytest.approx(0.03)
    row = m.as_row()
    assert row["n_trades"] == 3 and "sharpe" in row
