"""
Leg 2 of 3 — Nautilus Trader (event-driven backtest).

Builds a low-level ``BacktestEngine``, a simulated FX venue, an EUR/USD
instrument, feeds it the canonical CSV as 1-hour bars, runs the MACD strategy,
then computes the four metrics from the strategy's per-bar equity snapshots
using the SHARED metrics module (same conventions as the other legs).

Run:  (from repo root, nautilus venv)
    python 02_nautilus/run.py
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nautilus_trader.backtest.engine import BacktestEngine  # noqa: E402
from nautilus_trader.backtest.models import FillModel  # noqa: E402
from nautilus_trader.config import (  # noqa: E402
    BacktestEngineConfig, LoggingConfig, RiskEngineConfig,
)
from nautilus_trader.model.currencies import USD  # noqa: E402
from nautilus_trader.model.data import BarType  # noqa: E402
from nautilus_trader.model.enums import AccountType, OmsType  # noqa: E402
from nautilus_trader.model.identifiers import TraderId, Venue  # noqa: E402
from nautilus_trader.model.instruments import CurrencyPair  # noqa: E402
from nautilus_trader.model.objects import Money  # noqa: E402
from nautilus_trader.persistence.wranglers import BarDataWrangler  # noqa: E402
from nautilus_trader.test_kit.providers import TestInstrumentProvider  # noqa: E402

from shared.config import CFG, CANONICAL_CSV, summary  # noqa: E402
from shared.data import load_ohlcv, sha256  # noqa: E402
from shared.metrics import compute_metrics  # noqa: E402
from shared.results import write_result  # noqa: E402
from strategy import MACDConfig, MACDStrategy  # noqa: E402

ENGINE = "nautilus"


def main() -> None:
    print("=" * 70)
    print(f"  ENGINE: {ENGINE} (Nautilus Trader)")
    print("=" * 70)
    print("config :", summary())

    df = load_ohlcv(CANONICAL_CSV)
    print("data   :", f"{len(df):,} bars  {df.index[0]} -> {df.index[-1]}")
    print("sha256 :", sha256(CANONICAL_CSV))

    sim = Venue("SIM")
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id=TraderId("BACKTESTER-001"),
            logging=LoggingConfig(log_level="ERROR"),
            risk_engine=RiskEngineConfig(bypass=True),
        )
    )
    engine.add_venue(
        venue=sim,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(CFG.init_cash, USD)],
        fill_model=FillModel(prob_fill_on_limit=1.0, prob_slippage=0.0, random_seed=42),
    )

    # Default FX instrument carries a 0.2 bp maker/taker fee. We rebuild it with
    # zero fees so the cost model matches the zero-fee vectorbt baseline exactly
    # (CFG.fees_frac == 0). Removing this line is how you'd add realistic costs.
    base = TestInstrumentProvider.default_fx_ccy("EUR/USD", venue=sim)
    spec = CurrencyPair.to_dict(base)
    spec["maker_fee"] = "0"
    spec["taker_fee"] = "0"
    instrument = CurrencyPair.from_dict(spec)
    engine.add_instrument(instrument)

    # Dukascopy bars are stamped at their OPEN time. An event-driven engine must
    # only "see" a bar once it is COMPLETE, so we restamp each bar at its CLOSE
    # time (open + 1h) and use ts_init == ts_event (no delta). This keeps the
    # strategy clock and the matching engine in lock-step; otherwise the engine
    # advances to a bar before the strategy is told about it and market orders
    # fill against a future bar (look-ahead). With close stamping, an order
    # submitted in on_bar() correctly fills at the NEXT bar's open.
    df_nt = df.copy()
    df_nt.index = df_nt.index + pd.Timedelta(hours=1)

    # We feed a SINGLE LAST-price bar series (not separate BID+ASK). Feeding
    # bid and ask at identical timestamps caused a one-bar look-ahead: on_bar()
    # fires on the bid bar, then the ask bar at the SAME timestamp matches the
    # resting order at that bar's open — i.e. the open of the very bar whose
    # close produced the signal. With one LAST series there is no same-timestamp
    # duplicate, so a market order submitted in on_bar() rests and fills at the
    # NEXT bar's open — the look-ahead-free model used by every leg.
    bar_type = BarType.from_str(f"{instrument.id}-1-HOUR-LAST-EXTERNAL")
    bars = BarDataWrangler(bar_type, instrument).process(df_nt, default_volume=1_000_000)
    engine.add_data(bars)

    strategy = MACDStrategy(
        MACDConfig(
            instrument_id=instrument.id,
            bar_type=bar_type,
            trade_size=Decimal(str(int(CFG.trade_size_units))),
            fast=CFG.fast,
            slow=CFG.slow,
            signal=CFG.signal,
            warmup=CFG.warmup_bars,
        )
    )
    engine.add_strategy(strategy)

    engine.run()

    fills = engine.trader.generate_order_fills_report()
    positions = engine.trader.generate_positions_report()
    if getattr(strategy, "n_denied", 0):
        print(f"WARNING: {strategy.n_denied} orders denied "
              f"(first: {getattr(strategy, 'first_denial', '?')})")
    print(f"diag   : bars={strategy.n_bars} crossovers="
          f"{strategy.n_cross_up}up/{strategy.n_cross_down}down "
          f"fills={len(fills)} positions(closed)={len(positions)}")

    # ---- metrics from the engine's own per-bar equity snapshots --------------
    eq = pd.DataFrame(strategy.equity_curve, columns=["ts", "equity"])
    eq["ts"] = pd.to_datetime(eq["ts"], unit="ns", utc=True)
    equity = eq.set_index("ts")["equity"]

    n_trades = int(len(positions))

    metrics = compute_metrics(
        ENGINE, equity, n_trades, ann_factor=CFG.ann_factor, risk_free=CFG.risk_free
    )

    print("\n--- shared metrics (used for the cross-framework comparison) ---")
    print(metrics.pretty())

    write_result(metrics)
    print("\nwrote -> results/metrics.csv")

    engine.dispose()


if __name__ == "__main__":
    main()
