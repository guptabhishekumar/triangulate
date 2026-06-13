"""
Single source of truth for the entire project.

Every backtest leg (vectorbt, Nautilus Trader, MetaTrader 5) imports these
exact parameters so that all three are configured *identically*. Any difference
in results is therefore attributable to the backtest **engine**, never to
inconsistent inputs or assumptions.

Nothing in this file is framework-specific on purpose.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

# Repository root = parent of the `shared/` package.
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
CANONICAL_CSV = DATA_DIR / "eurusd_h1.csv"
METRICS_CSV = RESULTS_DIR / "metrics.csv"


@dataclass(frozen=True)
class Config:
    # ---- Instrument & sample -------------------------------------------------
    symbol: str = "EUR/USD"          # display name (engine-specific aliases below)
    symbol_mt5: str = "EURUSD"       # MetaTrader 5 / broker ticker
    symbol_yf: str = "EURUSD=X"      # yfinance ticker
    timeframe: str = "H1"            # 1-hour bars
    pandas_freq: str = "1h"          # pandas/vectorbt frequency alias for H1
    start: str = "2023-01-01"        # inclusive, UTC
    end: str = "2025-01-01"          # exclusive, UTC

    # ---- Strategy: MACD crossover -------------------------------------------
    fast: int = 12                   # fast EMA period
    slow: int = 26                   # slow EMA period
    signal: int = 9                  # signal EMA period (EMA of MACD line)
    # No trade is allowed until this many bars have elapsed, so every engine
    # starts trading on the *same* bar regardless of how it warms up internally.
    warmup_bars: int = 26 + 9        # slow + signal = 35

    # ---- Execution model -----------------------------------------------------
    # "long_flat": long on bullish cross, exit to cash on bearish cross.
    # (The alternative, "long_short", is documented but intentionally not used.)
    direction: str = "long_flat"
    # "next_open": the signal is detected on a *closed* bar and the order is
    # filled at the *next* bar's open. This is the only look-ahead-free choice
    # and is applied identically in all three engines.
    fill: str = "next_open"

    # ---- Account & sizing ----------------------------------------------------
    init_cash: float = 100_000.0     # starting deposit, USD
    trade_size_units: float = 10_000.0  # 0.10 lot of EUR/USD per trade (fixed)
    fees_frac: float = 0.0           # per-side commission as a fraction of notional
    slippage_frac: float = 0.0       # per-side slippage as a fraction of price

    # ---- Metrics conventions -------------------------------------------------
    risk_free: float = 0.0           # annual risk-free rate used for Sharpe
    # Annualisation factor for the Sharpe ratio. H1 forex trades ~24h x ~252
    # trading days => 6048 one-hour periods per year. Stated explicitly so all
    # three engines annualise the SAME way (engine defaults differ wildly).
    ann_factor: int = 24 * 252       # = 6048


CFG = Config()


def as_dict() -> dict:
    """Flat dict of the active configuration (handy for logging / provenance)."""
    return asdict(CFG)


def summary() -> str:
    c = CFG
    return (
        f"{c.symbol} {c.timeframe} | {c.start} -> {c.end} | "
        f"MACD({c.fast},{c.slow},{c.signal}) | {c.direction} | fill={c.fill} | "
        f"size={c.trade_size_units:g} units | deposit=${c.init_cash:,.0f} | "
        f"fees={c.fees_frac:g} | Sharpe ann={c.ann_factor}"
    )


if __name__ == "__main__":
    print(summary())
