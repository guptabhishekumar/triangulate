"""
The Nautilus strategy: a long/flat MACD crossover.

Event-driven — ``on_bar`` fires once per closed bar. We update the hand-written
incremental MACD, detect a crossover against the previous bar, and submit market
orders (which the simulated venue fills on the next bar). We also snapshot the
account's mark-to-market equity every bar, straight from Nautilus's own
portfolio, so the Sharpe/drawdown we report are computed from the engine's
equity curve — not reconstructed externally.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from macd_indicator import IncrementalMACD


class MACDConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast: int = 12
    slow: int = 26
    signal: int = 9
    warmup: int = 35


class MACDStrategy(Strategy):
    def __init__(self, config: MACDConfig):
        super().__init__(config)
        self.macd = IncrementalMACD(config.fast, config.slow, config.signal)
        self.prev_macd: float | None = None
        self.prev_signal: float | None = None
        self.instrument = None
        self.venue = config.instrument_id.venue
        # (timestamp_ns, equity) snapshots, one per bar.
        self.equity_curve: list[tuple[int, float]] = []
        # diagnostics
        self.n_bars = 0
        self.n_cross_up = 0
        self.n_cross_down = 0
        self.n_orders = 0
        self.n_denied = 0

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        self.n_bars += 1
        self.macd.update(float(bar.close))
        m, s = self.macd.macd, self.macd.signal

        if self.prev_macd is not None and self.macd.count > self.config.warmup:
            cross_up = self.prev_macd <= self.prev_signal and m > s
            cross_down = self.prev_macd >= self.prev_signal and m < s
            flat = self.portfolio.is_flat(self.config.instrument_id)
            if cross_up:
                self.n_cross_up += 1
                if flat:
                    self._market(OrderSide.BUY)
            elif cross_down and not flat:
                self.n_cross_down += 1
                self.close_all_positions(self.config.instrument_id)

        self.prev_macd, self.prev_signal = m, s
        self._snapshot_equity(bar)

    def on_order_denied(self, event) -> None:
        self.n_denied += 1
        if not hasattr(self, "first_denial"):
            self.first_denial = str(getattr(event, "reason", event))

    def on_order_rejected(self, event) -> None:
        self.n_denied += 1
        if not hasattr(self, "first_denial"):
            self.first_denial = str(getattr(event, "reason", event))

    def _snapshot_equity(self, bar: Bar) -> None:
        account = self.portfolio.account(self.venue)
        equity = float(account.balance_total(USD).as_double())
        upnl = self.portfolio.unrealized_pnl(self.config.instrument_id)
        if upnl is not None:
            equity += float(upnl.as_double())
        self.equity_curve.append((bar.ts_event, equity))

    def _market(self, side: OrderSide) -> None:
        order = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(self.config.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.n_orders += 1
        self.submit_order(order)

    def on_stop(self) -> None:
        self.close_all_positions(self.config.instrument_id)

    def on_reset(self) -> None:
        self.macd.reset()
        self.prev_macd = self.prev_signal = None
        self.equity_curve.clear()
