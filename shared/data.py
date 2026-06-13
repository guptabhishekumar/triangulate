"""
Canonical data loader.

Every engine reads the *same* CSV through this one function, so the two Python
legs (vectorbt, Nautilus) consume byte-identical bars. The CSV schema is:

    timestamp (UTC, ISO-8601, index), open, high, low, close, volume

See ``data/get_data.py`` for how the file is produced and ``data/README.md`` for
its provenance.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


def load_ohlcv(path: str | Path) -> pd.DataFrame:
    """Load and validate the canonical OHLCV CSV with a UTC DatetimeIndex."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Canonical dataset not found: {path}\n"
            f"Generate it first, e.g.:  python data/get_data.py --source dukascopy"
        )
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    df.columns = [c.lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV {path} is missing columns: {missing}")

    df = df[REQUIRED_COLUMNS].sort_index()
    df = df[~df.index.duplicated(keep="first")]
    if not df.index.is_monotonic_increasing:
        raise ValueError("Index is not monotonically increasing after sort")
    if df[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError("OHLC contains NaNs — clean the source data")
    return df


def sha256(path: str | Path) -> str:
    """SHA-256 of a file — printed at load time so the dataset is verifiable."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(df: pd.DataFrame) -> str:
    return (
        f"{len(df):,} bars | {df.index[0]} -> {df.index[-1]} | "
        f"cols={list(df.columns)}"
    )
