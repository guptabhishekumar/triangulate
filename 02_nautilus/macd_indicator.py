"""
Hand-written, incremental MACD for the event-driven Nautilus leg.

Nautilus processes one bar at a time, so instead of recomputing the whole series
every bar we carry the EMA state forward with an O(1) update. The update uses the
exact same recursion as the batch ``shared.indicators.ema`` (verified equal in
``tests/test_indicators.py::test_ema_step_matches_vectorised``), so this engine
sees numerically identical MACD/signal values to the vectorbt leg.

This is deliberately NOT the built-in ``nautilus_trader`` MACD indicator — the
assignment requires the math to be hand-written.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.indicators import ema_step  # noqa: E402


class IncrementalMACD:
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast, self.slow, self.signal_p = fast, slow, signal
        self._ema_fast = 0.0
        self._ema_slow = 0.0
        self._signal = 0.0
        self._seen_fast = False
        self._seen_slow = False
        self._seen_signal = False
        self.macd = 0.0
        self.signal = 0.0
        self.count = 0

    def update(self, close: float) -> None:
        self._ema_fast = ema_step(self._ema_fast, close, self.fast, self._seen_fast)
        self._seen_fast = True
        self._ema_slow = ema_step(self._ema_slow, close, self.slow, self._seen_slow)
        self._seen_slow = True
        self.macd = self._ema_fast - self._ema_slow
        self._signal = ema_step(self._signal, self.macd, self.signal_p, self._seen_signal)
        self._seen_signal = True
        self.signal = self._signal
        self.count += 1

    def reset(self) -> None:
        self.__init__(self.fast, self.slow, self.signal_p)
