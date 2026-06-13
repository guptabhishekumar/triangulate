# Leg 3 — MetaTrader 5

MT5 plays **two** roles here:

| File | Role | Needs terminal? |
|---|---|---|
| [`macd_crossover_ea.mq5`](macd_crossover_ea.mq5) | The EA for the **Strategy Tester** — the official, graded MT5 result | Yes (GUI) |
| [`export_data.py`](export_data.py) | Export broker EUR/USD H1 → canonical CSV | Yes |
| [`run.py`](run.py) | MT5 **Python-API** backtest (reuses the glass-box engine) | No (CSV fallback) |

> **Why two?** The `MetaTrader5` Python package can pull data and trade live, but
> it **cannot drive the Strategy Tester**. So the canonical MT5 backtest is the
> MQL5 EA; the Python script is a cross-check that runs anywhere.

The EA writes the MACD/EMA math **by hand** (no `iMACD`/`iMA`), updated once per
new bar on the just-closed bar, long/flat, market orders filling at the next
bar's open — identical logic to the other two legs.

## A. Official result — MQL5 EA + Strategy Tester

1. Install **MetaTrader 5** (any broker, or MetaQuotes) and open a **free demo**
   account (`File → Open an Account → MetaQuotes-Demo`).
2. Get history: open the **EUR/USD, H1** chart and press **Home** / scroll left
   so the terminal downloads the 2023–2024 bars.
3. Open **MetaEditor** (`Tools → MetaQuotes Language Editor`), put
   `macd_crossover_ea.mq5` under `MQL5/Experts/`, and press **F7** to compile.
4. Open the **Strategy Tester** (`View → Strategy Tester`, or `Ctrl+R`):
   - Expert: `macd_crossover_ea`
   - Symbol: **EURUSD**, Period: **H1**
   - Date range: **2023-01-01 → 2025-01-01**
   - Modelling: **Open prices only** (deterministic, matches bar-close logic)
   - Deposit: **100000 USD**, Leverage as default
   - Inputs: `InpLots=0.10`, `InpFast=12`, `InpSlow=26`, `InpSignal=9`, `InpWarmup=35`
5. **Start**. When done, open the **Backtest / Report** tab → right-click →
   **Save as Report** (HTML) and screenshot it.
6. Save the screenshot to `../results/mt5_report.png` and copy Total Net Profit,
   Sharpe Ratio, Balance/Equity Drawdown, and Total Trades into the root README
   table (the `mt5_strategy_tester` row).

## B. Python-API cross-check

```bash
pip install -r 03_mt5/requirements.txt
python 03_mt5/run.py        # uses live MT5 if running, else the committed CSV
```

## Result

| Engine | Total Return | Sharpe | Max Drawdown | Trades |
|---|---:|---:|---:|---:|
| MT5 Python API (CSV) | −0.0536% | −0.0469 | −0.6565% | 484 |
| MT5 Strategy Tester | _run on your machine (step A)_ | | | |

The Strategy Tester numbers will differ slightly from the Python legs — it uses
the broker's bars and models spread/commission per your settings. That expected
difference is exactly what the root README's analysis discusses.
