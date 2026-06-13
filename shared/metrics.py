"""
One metrics implementation, used by all three legs.

The four required figures — total return, Sharpe ratio, max drawdown, and number
of trades — are computed here from an *equity curve*. Each engine reports
performance with its own conventions (different annualisation factors, different
definitions of a "trade"); to make the three genuinely comparable we ignore
those built-ins and recompute everything from each engine's equity series with
ONE explicit set of assumptions:

    * risk-free rate            : CFG.risk_free (default 0)
    * Sharpe annualisation      : sqrt(CFG.ann_factor)   (H1 forex -> 24*252)
    * standard deviation        : sample std, ddof = 1
    * "number of trades"        : round-trip closed positions (passed in)

All assumptions are surfaced in the README so the numbers are reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Metrics:
    engine: str
    total_return: float      # fraction, e.g. 0.0423 = +4.23%
    sharpe: float            # annualised, risk-free = 0
    max_drawdown: float      # negative fraction, e.g. -0.0817 = -8.17%
    n_trades: int            # round-trip closed positions
    final_equity: float
    ann_factor: int

    def as_row(self) -> dict:
        return {
            "engine": self.engine,
            "total_return_pct": round(self.total_return * 100, 4),
            "sharpe": round(self.sharpe, 4),
            "max_drawdown_pct": round(self.max_drawdown * 100, 4),
            "n_trades": int(self.n_trades),
            "final_equity": round(self.final_equity, 2),
            "ann_factor": int(self.ann_factor),
        }

    def pretty(self) -> str:
        return (
            f"[{self.engine}]\n"
            f"  Total return : {self.total_return:+.2%}\n"
            f"  Sharpe ratio : {self.sharpe:.3f}\n"
            f"  Max drawdown : {self.max_drawdown:.2%}\n"
            f"  Trades       : {self.n_trades}\n"
            f"  Final equity : ${self.final_equity:,.2f}"
        )


def _to_series(equity) -> pd.Series:
    if isinstance(equity, pd.Series):
        return equity.astype("float64").dropna()
    return pd.Series(np.asarray(equity, dtype="float64")).dropna()


def total_return(equity) -> float:
    e = _to_series(equity)
    if len(e) < 2 or e.iloc[0] == 0:
        return 0.0
    return float(e.iloc[-1] / e.iloc[0] - 1.0)


def sharpe_ratio(equity, ann_factor: int, risk_free: float = 0.0) -> float:
    """Annualised Sharpe from a per-bar equity curve. rf is an *annual* rate."""
    e = _to_series(equity)
    rets = e.pct_change().dropna()
    if len(rets) < 2:
        return float("nan")
    sd = rets.std(ddof=1)
    if sd == 0:
        return float("nan")
    rf_per_bar = risk_free / ann_factor
    excess = rets - rf_per_bar
    return float(excess.mean() / sd * np.sqrt(ann_factor))


def max_drawdown(equity) -> float:
    """Most negative peak-to-trough move on the equity curve (a fraction <= 0)."""
    e = _to_series(equity)
    if e.empty:
        return 0.0
    running_max = e.cummax()
    dd = e / running_max - 1.0
    return float(dd.min())


def compute_metrics(
    engine: str,
    equity,
    n_trades: int,
    ann_factor: int,
    risk_free: float = 0.0,
) -> Metrics:
    e = _to_series(equity)
    return Metrics(
        engine=engine,
        total_return=total_return(e),
        sharpe=sharpe_ratio(e, ann_factor, risk_free),
        max_drawdown=max_drawdown(e),
        n_trades=int(n_trades),
        final_equity=float(e.iloc[-1]) if len(e) else float("nan"),
        ann_factor=int(ann_factor),
    )
