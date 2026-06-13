"""
Produce the single canonical OHLCV dataset that every engine consumes.

The price series is pulled ONCE here and written to ``data/eurusd_h1.csv`` so the
two Python legs (vectorbt, Nautilus) read byte-identical bars. Three sources are
supported; pick with ``--source``:

  mt5        MetaTrader 5 terminal (RECOMMENDED if you have it): the bars the
             Strategy Tester itself will later use -> tightest cross-framework
             alignment. Windows-only; needs the terminal installed + running.

  dukascopy  Dukascopy public tick/bar server via the ``dukascopy-python``
             package. Free, no account, deep history, works headless. This is
             the default and the source committed in the repo.

  yfinance   Yahoo Finance (EURUSD=X). Easiest but WEAKEST: hourly data is
             capped to ~the last 730 days, has gaps, and is indicative (not
             broker) pricing. Fallback only.

Output schema:  timestamp(UTC,index), open, high, low, close, volume

Usage:
    python data/get_data.py --source dukascopy
    python data/get_data.py --source mt5
    python data/get_data.py --source yfinance --start 2024-07-01 --end 2026-06-01
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.config import CFG, CANONICAL_CSV  # noqa: E402
from shared.data import sha256, describe  # noqa: E402

OHLCV = ["open", "high", "low", "close", "volume"]


def _utc(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def from_dukascopy(start: str, end: str) -> pd.DataFrame:
    import dukascopy_python
    from dukascopy_python.instruments import INSTRUMENT_FX_MAJORS_EUR_USD

    df = dukascopy_python.fetch(
        INSTRUMENT_FX_MAJORS_EUR_USD,
        dukascopy_python.INTERVAL_HOUR_1,
        dukascopy_python.OFFER_SIDE_BID,
        _utc(start),
        _utc(end),
    )
    df.columns = [c.lower() for c in df.columns]
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df.index = pd.to_datetime(df.index, utc=True)
    df.index.name = "timestamp"
    return df[OHLCV]


def from_mt5(start: str, end: str) -> pd.DataFrame:
    import MetaTrader5 as mt5  # Windows-only; needs the terminal running

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()} "
                           "(is the terminal installed, running, and logged in?)")
    try:
        mt5.symbol_select(CFG.symbol_mt5, True)
        rates = mt5.copy_rates_range(
            CFG.symbol_mt5, mt5.TIMEFRAME_H1, _utc(start), _utc(end)
        )
    finally:
        mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise RuntimeError("MT5 returned no bars — open the EUR/USD H1 chart and "
                           "press Home to download history, then retry.")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"time": "timestamp", "tick_volume": "volume"})
    df = df.set_index("timestamp")
    return df[OHLCV]


def from_yfinance(start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(CFG.symbol_yf, interval="1h", start=start, end=end,
                     auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df.index = pd.to_datetime(df.index, utc=True)
    df.index.name = "timestamp"
    return df[OHLCV]


SOURCES = {"mt5": from_mt5, "dukascopy": from_dukascopy, "yfinance": from_yfinance}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=SOURCES, default="dukascopy")
    p.add_argument("--start", default=CFG.start)
    p.add_argument("--end", default=CFG.end)
    p.add_argument("--out", default=str(CANONICAL_CSV))
    args = p.parse_args()

    print(f"Fetching {CFG.symbol} {CFG.timeframe} from '{args.source}' "
          f"[{args.start} -> {args.end}] ...")
    df = SOURCES[args.source](args.start, args.end)

    df = df.sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df.dropna(subset=["open", "high", "low", "close"])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)

    print("Saved:", out)
    print(describe(df))
    print("SHA-256:", sha256(out))


if __name__ == "__main__":
    main()
