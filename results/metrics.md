# Backtest results

**Run configuration:** EUR/USD H1 | 2023-01-01 -> 2025-01-01 | MACD(12,26,9) | long_flat | fill=next_open | size=10000 units | deposit=$100,000 | fees=0 | Sharpe ann=6048

_Risk-free rate = 0.0; Sharpe annualised by sqrt(6048); std uses ddof=1; metrics recomputed identically for every engine from each engine's own equity curve._

| Engine | Total Return | Sharpe | Max Drawdown | Trades | Final Equity |
|---|---:|---:|---:|---:|---:|
| vectorbt (vectorised) | -0.0536% | -0.0469 | -0.6565% | 484 | $99,946.40 |
| Nautilus Trader (event-driven) | -0.1340% | -0.1211 | -0.7249% | 484 | $99,865.96 |
| MetaTrader 5 (Python API) | -0.0536% | -0.0469 | -0.6565% | 484 | $99,946.40 |
