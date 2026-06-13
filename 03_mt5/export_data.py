"""
Export EUR/USD H1 bars from a running MetaTrader 5 terminal to the canonical CSV.

This is the *recommended* way to produce ``data/eurusd_h1.csv`` if you have MT5:
the bars come from the same broker history the Strategy Tester will use, giving
the tightest possible alignment between the MT5 report and the Python legs.

Requires: Windows, the MT5 terminal installed + running + logged into a (demo)
account, and ``pip install MetaTrader5`` in this folder's environment.

    python 03_mt5/export_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.get_data import from_mt5  # noqa: E402  (reuse the canonical puller)
from shared.config import CFG, CANONICAL_CSV  # noqa: E402
from shared.data import sha256, describe  # noqa: E402


def main() -> None:
    print(f"Exporting {CFG.symbol_mt5} {CFG.timeframe} from MT5 "
          f"[{CFG.start} -> {CFG.end}] ...")
    df = from_mt5(CFG.start, CFG.end)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="first")]
    CANONICAL_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CANONICAL_CSV)
    print("Saved:", CANONICAL_CSV)
    print(describe(df))
    print("SHA-256:", sha256(CANONICAL_CSV))


if __name__ == "__main__":
    main()
