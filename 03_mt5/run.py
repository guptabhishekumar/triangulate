"""
Leg 3 of 3 — MetaTrader 5, *Python-API* backtest.

Important: the ``MetaTrader5`` Python package can pull historical bars and place
live/demo orders, but it CANNOT drive the Strategy Tester. A "backtest" via the
Python API is therefore necessarily a hand-written loop over historical bars —
so we reuse the project's glass-box reference engine (shared/reference_backtest)
with the same hand-written MACD and the same execution model as the other legs.

The canonical, graded MT5 result is the one produced by the MQL5 Expert Advisor
(macd_crossover_ea.mq5) in the Strategy Tester — see 03_mt5/README.md. This
script is the Python-API counterpart and a cross-check.

Data source: a live MT5 terminal if available (via copy_rates_range), otherwise
the committed canonical CSV — so it runs anywhere and always uses the same bars
as the other two legs.

Run:  python 03_mt5/run.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.config import CFG, CANONICAL_CSV, summary  # noqa: E402
from shared.data import load_ohlcv, sha256  # noqa: E402
from shared.indicators import macd  # noqa: E402
from shared.signals import crossover_signals  # noqa: E402
from shared.reference_backtest import backtest_long_flat  # noqa: E402
from shared.metrics import compute_metrics  # noqa: E402
from shared.results import write_result  # noqa: E402

ENGINE = "mt5_python"


def _utc(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def load_bars() -> tuple[pd.DataFrame, str]:
    """Pull bars from a live MT5 terminal if possible, else the canonical CSV."""
    try:
        import MetaTrader5 as mt5  # Windows + running terminal only
        if mt5.initialize():
            try:
                mt5.symbol_select(CFG.symbol_mt5, True)
                rates = mt5.copy_rates_range(
                    CFG.symbol_mt5, mt5.TIMEFRAME_H1, _utc(CFG.start), _utc(CFG.end)
                )
            finally:
                mt5.shutdown()
            if rates is not None and len(rates):
                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
                df = (df.rename(columns={"time": "timestamp", "tick_volume": "volume"})
                        .set_index("timestamp")[["open", "high", "low", "close", "volume"]]
                        .sort_index())
                return df, "live MT5 terminal (copy_rates_range)"
    except Exception as exc:  # noqa: BLE001
        print(f"(MT5 terminal unavailable: {exc})")
    return load_ohlcv(CANONICAL_CSV), "canonical CSV fallback (data/eurusd_h1.csv)"


def main() -> None:
    print("=" * 70)
    print(f"  ENGINE: {ENGINE} (MetaTrader5 Python API -> reference engine)")
    print("=" * 70)
    print("config :", summary())

    df, source = load_bars()
    print("source :", source)
    print("data   :", f"{len(df):,} bars  {df.index[0]} -> {df.index[-1]}")
    if source.startswith("canonical"):
        print("sha256 :", sha256(CANONICAL_CSV))

    macd_line, signal_line, _ = macd(df["close"].to_numpy(), CFG.fast, CFG.slow, CFG.signal)
    entries, exits = crossover_signals(macd_line, signal_line, CFG.warmup_bars)

    result = backtest_long_flat(
        df, entries, exits,
        init_cash=CFG.init_cash, size_units=CFG.trade_size_units,
        fees_frac=CFG.fees_frac, slippage_frac=CFG.slippage_frac, fill=CFG.fill,
    )

    metrics = compute_metrics(
        ENGINE, result.equity, result.n_trades,
        ann_factor=CFG.ann_factor, risk_free=CFG.risk_free,
    )
    print("\n--- shared metrics (used for the cross-framework comparison) ---")
    print(metrics.pretty())

    write_result(metrics)
    print("\nwrote -> results/metrics.csv")
    print("\nNOTE: the official MT5 result is the Strategy Tester report from "
          "macd_crossover_ea.mq5 -- see 03_mt5/README.md.")


if __name__ == "__main__":
    main()
