# Data

One canonical dataset feeds **all three** backtests, so the comparison is apples
to apples. It is generated once by [`get_data.py`](get_data.py) and committed to
the repo for full reproducibility.

## Committed dataset — `eurusd_h1.csv`

| Field | Value |
|---|---|
| Instrument | EUR/USD |
| Timeframe | H1 (1-hour) |
| Range | 2023-01-01 → 2024-12-31 (UTC) |
| Bars | 12,475 |
| Source | Dukascopy (bid candles), via `dukascopy-python` |
| SHA-256 | `b1eda5a4a3045caea00f54228e566c74277d33ffe9bc44741a1166f411d1194d` |

Schema: `timestamp` (UTC, ISO-8601, index), `open`, `high`, `low`, `close`,
`volume`. Timestamps are bar **open** times; forex has no weekend bars, so the
count is below 24×730.

## Regenerating

```bash
python data/get_data.py --source dukascopy     # default: free, headless, deep history
python data/get_data.py --source mt5           # best if you have MT5 (broker-matched bars)
python data/get_data.py --source yfinance      # fallback: ~730-day hourly cap, indicative quotes
```

The loader (`shared/data.py`) validates the schema, enforces a monotonic UTC
index, drops duplicates, and prints the SHA-256 at load time.

## Why source matters for the MT5 leg

The MT5 **Strategy Tester** always runs on the broker's own downloaded bars — it
cannot be fed this CSV. If you have MT5, regenerate the CSV with `--source mt5`
so the Python legs use the *same* broker bars the Tester will use. Otherwise the
committed Dukascopy bars are used by the Python legs and the MT5 Tester uses its
broker history — a small, documented source difference (see the root README).
