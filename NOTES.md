# Development notes & AI-assistance log

A running, honest record of how the project was built — including where an AI
coding assistant **helped** and where it was **wrong** and had to be corrected
against primary sources. (The assignment explicitly asks for this.)

## Where the AI assistant helped

- Scaffolding the repo, the shared indicator/metrics/signal modules, and the
  per-framework runners from a single spec.
- Recalling current API shapes for vectorbt 1.0, Nautilus 1.228, and the MT5
  Python package, which were then verified against the installed packages.
- Writing the pytest oracle that checks the hand-written EMA against
  `pandas.ewm(adjust=False)`.

## Where the AI assistant was WRONG (and how it was caught/fixed)

1. **"Open-source vectorbt is 0.27.2; 1.0+ is the paid PRO product."**
   Confidently asserted, and it would have forced an unnecessary `numpy<2.1` /
   Python-3.11 environment split. **Caught** by querying the PyPI JSON directly:
   vectorbt **1.0.0** (released 2026-04-22) *is* the open-source community
   edition and supports numpy 2.x / Python 3.12. **Fix:** single Python-3.12
   toolchain across all three legs.

2. **Nautilus: a single BID bar series is enough to trade.**
   First skeleton fed only BID bars; every market BUY was denied with
   `no market for EUR/USD.SIM` (a buy needs an ask). **Caught** by logging the
   denial reason. **Fix:** feed a single `LAST`-price bar series.

3. **Nautilus: "just feed bid + ask bars."**
   Doing so produced an implausible **Sharpe of 6.8 / +8.6% return**. **Caught**
   by disbelief at the number, then by printing fills: orders were filling at the
   *signal bar's own open* (a one-bar look-ahead), because the ask bar at the
   same timestamp matched the resting order. **Fix:** one `LAST` series + restamp
   bars at their **close** time so a market order rests and fills at the **next**
   bar's open. Sharpe fell back to ≈ the other engines (−0.12).

4. **Nautilus fees are zero by default.**
   The default FX instrument actually carries a 0.2 bp maker/taker fee (visible
   in the fills report). **Fix:** rebuild the instrument via `to_dict`/`from_dict`
   with `maker_fee = taker_fee = "0"` for a clean zero-fee baseline.

5. **EMA seeding was left implicit.**
   Different seedings (SMA-seed vs first-value vs `adjust=True`) shift early
   crossovers and the trade count. **Fix:** fix one convention (`adjust=False`,
   first-value seed), hand-write it, and unit-test it against pandas so all three
   engines are numerically identical.

## Verification at each step

- 18 unit tests (`tests/`) — EMA == pandas oracle, EMA ≠ `adjust=True`, metrics,
  and the reference engine's PnL on a hand-checked example.
- vectorbt result reproduces the glass-box reference engine exactly.
- Nautilus first-fill price checked by hand against the next bar's open.

## Environment

- Windows 11, Python 3.12.
- One isolated venv per framework (`.venv-vectorbt`, `.venv-nautilus`,
  `.venv-mt5`) — chosen for clean isolation. With vectorbt 1.0 + Nautilus 1.228
  the dependency constraints actually overlap on Python 3.12 / numpy 2.x, so a
  single env is possible too; separate envs are kept for robustness.
