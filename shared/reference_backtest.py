"""
A minimal, fully transparent ("glass-box") fixed-size long/flat backtester.

This is NOT one of the three required frameworks. It exists for two reasons:

  1. As an independent baseline to validate that the vectorbt and Nautilus
     engines behave the way we think they do.
  2. As the MetaTrader 5 *Python-API* backtest: the ``MetaTrader5`` package can
     pull historical bars but cannot drive the Strategy Tester, so a Python
     "MT5 backtest" is necessarily a hand-written loop. We reuse this one rather
     than writing a fourth.

Model (matches the project-wide assumptions in shared/config.py):
  * Position size is FIXED (``size_units``), long/flat only.
  * Signal is detected on a closed bar; the order fills at the NEXT bar's open
    (``fill="next_open"``) — i.e. signals are shifted one bar and executed at
    that bar's open price.
  * Equity is marked to market on each bar's close as
    ``deposit + realised_pnl + unrealised_pnl``. For a fixed-size FX position
    this is the standard PnL accounting (PnL = size * price_change).
  * A position still open on the final bar is closed at the last close.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: list = field(default_factory=list)

    @property
    def n_trades(self) -> int:
        return len(self.trades)


def backtest_long_flat(
    df: pd.DataFrame,
    entries: np.ndarray,
    exits: np.ndarray,
    init_cash: float,
    size_units: float,
    fees_frac: float = 0.0,
    slippage_frac: float = 0.0,
    fill: str = "next_open",
) -> BacktestResult:
    """Run the reference simulation and return an equity curve + trade list."""
    open_ = df["open"].to_numpy(dtype="float64")
    close = df["close"].to_numpy(dtype="float64")
    idx = df.index
    n = len(close)

    ent = np.asarray(entries, dtype=bool).copy()
    exi = np.asarray(exits, dtype=bool).copy()

    if fill == "next_open":
        # Signal seen at close of bar t -> executed at open of bar t+1.
        ent = np.roll(ent, 1); ent[0] = False
        exi = np.roll(exi, 1); exi[0] = False
        exec_price = open_
    elif fill == "close":
        exec_price = close
    else:
        raise ValueError(f"unknown fill mode: {fill!r}")

    equity = np.empty(n, dtype="float64")
    trades: list[dict] = []

    realised = 0.0
    in_pos = False
    entry_price = 0.0
    entry_i = -1

    def _fill_price(px: float, side: int) -> float:
        # side: +1 buy, -1 sell. Slippage worsens the fill.
        return px * (1.0 + side * slippage_frac)

    for i in range(n):
        if (not in_pos) and ent[i]:
            entry_price = _fill_price(exec_price[i], +1)
            realised -= size_units * entry_price * fees_frac
            in_pos = True
            entry_i = i
        elif in_pos and exi[i]:
            exit_price = _fill_price(exec_price[i], -1)
            pnl = size_units * (exit_price - entry_price)
            realised += pnl - size_units * exit_price * fees_frac
            trades.append({
                "entry_time": idx[entry_i], "exit_time": idx[i],
                "entry_price": entry_price, "exit_price": exit_price,
                "pnl": pnl,
            })
            in_pos = False

        unrealised = size_units * (close[i] - entry_price) if in_pos else 0.0
        equity[i] = init_cash + realised + unrealised

    # Force-close any position open on the last bar.
    if in_pos:
        exit_price = _fill_price(close[-1], -1)
        pnl = size_units * (exit_price - entry_price)
        realised += pnl - size_units * exit_price * fees_frac
        trades.append({
            "entry_time": idx[entry_i], "exit_time": idx[-1],
            "entry_price": entry_price, "exit_price": exit_price,
            "pnl": pnl, "forced_close": True,
        })
        equity[-1] = init_cash + realised

    return BacktestResult(equity=pd.Series(equity, index=idx, name="equity"), trades=trades)
