"""
Collect each engine's metrics into one shared results table.

Every leg calls ``write_result(metrics)`` which upserts a single row (keyed by
engine name) into ``results/metrics.csv``. ``compare()`` renders the table for
the README / console.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import METRICS_CSV, RESULTS_DIR
from .metrics import Metrics

COLUMNS = ["engine", "total_return_pct", "sharpe", "max_drawdown_pct",
           "n_trades", "final_equity", "ann_factor"]


def write_result(metrics: Metrics, path: Path = METRICS_CSV) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = metrics.as_row()
    if path.exists():
        df = pd.read_csv(path)
    else:
        df = pd.DataFrame(columns=COLUMNS)
    df = df[df["engine"] != row["engine"]]  # replace any existing row for engine
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    # Stable ordering: vectorbt, nautilus, mt5*, then the rest.
    order = {"vectorbt": 0, "nautilus": 1, "mt5_python": 2, "mt5_strategy_tester": 3}
    df["_o"] = df["engine"].map(lambda e: order.get(e, 99))
    df = df.sort_values(["_o", "engine"]).drop(columns="_o").reset_index(drop=True)
    df.to_csv(path, index=False)


def load() -> pd.DataFrame:
    if not Path(METRICS_CSV).exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(METRICS_CSV)


def compare() -> str:
    df = load()
    if df.empty:
        return "(no results yet — run the engine legs first)"
    return df.to_string(index=False)


if __name__ == "__main__":
    print(compare())
