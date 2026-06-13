"""
Leg 1 of 3 — vectorbt (vectorised backtest).

Philosophy: compute everything over whole NumPy arrays at once. We hand-roll the
MACD (shared/indicators.py), turn it into boolean entry/exit arrays, shift them
one bar so a signal seen at a bar's close is executed at the NEXT bar's open
(look-ahead-free), and hand the arrays to ``vbt.Portfolio.from_signals``.

We do NOT trust vectorbt's built-in Sharpe/return conventions for the
cross-framework comparison — we recompute all four metrics from the equity curve
(``pf.value()``) with the shared metrics module, so every leg is measured the
same way. vectorbt's own ``stats()`` is printed too, for transparency.

Run:  (from repo root, vectorbt venv)
    python 01_vectorbt/run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import vectorbt as vbt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.config import CFG, CANONICAL_CSV, summary  # noqa: E402
from shared.data import load_ohlcv, sha256  # noqa: E402
from shared.indicators import macd  # noqa: E402
from shared.signals import crossover_signals  # noqa: E402
from shared.metrics import compute_metrics  # noqa: E402
from shared.results import write_result  # noqa: E402

ENGINE = "vectorbt"


def main() -> None:
    print("=" * 70)
    print(f"  ENGINE: {ENGINE}")
    print("=" * 70)
    print("config :", summary())

    df = load_ohlcv(CANONICAL_CSV)
    print("data   :", f"{len(df):,} bars  {df.index[0]} -> {df.index[-1]}")
    print("sha256 :", sha256(CANONICAL_CSV))

    close = df["close"].to_numpy()
    macd_line, signal_line, _ = macd(close, CFG.fast, CFG.slow, CFG.signal)
    cross_up, cross_down = crossover_signals(macd_line, signal_line, CFG.warmup_bars)

    # Next-bar-open execution: shift signals one bar, fill at the open.
    entries = pd.Series(cross_up, index=df.index).shift(1).fillna(False)
    exits = pd.Series(cross_down, index=df.index).shift(1).fillna(False)

    pf = vbt.Portfolio.from_signals(
        close=df["close"],
        entries=entries,
        exits=exits,
        price=df["open"],                 # fill at the (next) bar's open
        direction="longonly",             # long / flat
        size=CFG.trade_size_units,
        size_type="amount",               # fixed number of units per trade
        init_cash=CFG.init_cash,
        fees=CFG.fees_frac,
        slippage=CFG.slippage_frac,
        freq=CFG.pandas_freq,             # only affects vectorbt's own stats()
    )

    equity = pf.value()
    n_trades = int(pf.trades.count())

    metrics = compute_metrics(
        ENGINE, equity, n_trades, ann_factor=CFG.ann_factor, risk_free=CFG.risk_free
    )

    print("\n--- vectorbt native stats (its own conventions) ---")
    try:
        print(pf.stats())
    except Exception as exc:  # pragma: no cover - stats is cosmetic
        print(f"(pf.stats() unavailable: {exc})")

    print("\n--- shared metrics (used for the cross-framework comparison) ---")
    print(metrics.pretty())

    write_result(metrics)
    print("\nwrote -> results/metrics.csv")


if __name__ == "__main__":
    main()
