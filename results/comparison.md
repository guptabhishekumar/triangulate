# Cross-framework comparison — why the numbers (don't quite) agree

**Run:** EUR/USD H1, 2023-01-01 → 2024-12-31, MACD(12,26,9), long/flat, fixed
10,000-unit orders, $100,000 deposit, zero fees, fill at next bar's open, Sharpe
annualised by √6048, risk-free 0.

| Engine | Total Return | Sharpe | Max Drawdown | Trades |
|---|---:|---:|---:|---:|
| vectorbt (vectorised) | −0.0536% | −0.0469 | −0.6565% | 484 |
| Nautilus (event-driven) | −0.1340% | −0.1211 | −0.7249% | 484 |
| MT5 (Python API, on CSV) | −0.0536% | −0.0469 | −0.6565% | 484 |
| MT5 (Strategy Tester) | _run locally — see 03_mt5/_ | | | |

## What is identical, and why

- **Trade count = 484 everywhere.** All legs import the *same* hand-written MACD
  (`shared/indicators.py`, `adjust=False`, first-value seed) and the *same*
  crossover + warmup logic. Identical indicator → identical signals → identical
  number of round-trips. This is the single most important design choice: it
  isolates the *engine* as the only moving part.
- **vectorbt ≡ MT5 Python API, to the cent.** Both fill at the next bar's open on
  the same CSV, and vectorbt reproduces the glass-box reference engine exactly.
  This is a useful sanity check: the vectorised maths and the explicit loop agree.

## What differs, and why

**1. Nautilus is ~0.08% lower (−0.134% vs −0.054%).**
Same 484 trades, but a different *fill price*. vectorbt fills at exactly the next
bar's `open` value from the CSV. Nautilus is a true matching engine: it fills the
resting market order against the next bar reconstructed from a `LAST`-price
series, which lands a fraction of a pip away from the raw CSV open. Across 484
round-trips that is ≈ 0.16 pip/trade — entirely a micro-structure/fill-model
difference, not a logic difference. (Sign, magnitude, drawdown and trade count
all still agree.)

**2. The MT5 Strategy Tester will differ more (when you run it).** Expected,
because it changes things the Python legs hold fixed:
- **Different bars.** The Tester runs on the *broker's* history, not this CSV
  (unless you regenerated the CSV with `--source mt5`). Different broker → slightly
  different opens/closes → a few crossovers shift by a bar.
- **Costs.** If your broker applies spread/commission/swap, net profit drops vs
  the zero-fee Python baseline. Set commission to 0 (or a known value) for the
  closest comparison.
- **Modelling.** "Open prices only" matches the bar-close logic; "Every tick"
  simulates intrabar fills and will diverge.

## Things deliberately standardised so they *don't* cause spurious differences

| Pitfall | How each engine could differ | What we did |
|---|---|---|
| EMA seeding | SMA-seed vs first-value vs pandas `adjust=True` | One definition (`adjust=False`, first-value), hand-written, used everywhere; unit-tested against pandas |
| Look-ahead / fill timing | close-fill vs next-open vs intrabar | "Signal on closed bar → next-bar open" enforced in all three |
| Sharpe annualisation | 252 vs 24×252 vs 24×365 defaults | Recomputed ourselves with √6048 from each engine's equity curve |
| "Number of trades" | round-trips vs fills vs deals | Round-trip closed positions everywhere (MT5 *positions*, not *deals*) |
| Fees | engine defaults (e.g. Nautilus 0.2 bp) | Forced to zero in every engine for the baseline |

## Takeaway

After removing every avoidable source of difference, the three engines agree on
trade count exactly and on returns to within ~0.08% — and the residual is a
clean, explainable fill-price effect, not a bug. A naive MACD crossover on
EUR/USD H1 is, as expected, roughly break-even before costs (and negative once
realistic costs are added).
