"""
Render the cross-framework results table from results/metrics.csv.

Writes a Markdown table to results/metrics.md (embedded in the README) and prints
it to the console. Run after the engine legs have populated results/metrics.csv:

    python compare.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared.config import CFG, RESULTS_DIR, summary  # noqa: E402
from shared.results import load  # noqa: E402

LABELS = {
    "vectorbt": "vectorbt (vectorised)",
    "nautilus": "Nautilus Trader (event-driven)",
    "mt5_python": "MetaTrader 5 (Python API)",
    "mt5_strategy_tester": "MetaTrader 5 (Strategy Tester)",
}


def to_markdown(df) -> str:
    header = (
        "| Engine | Total Return | Sharpe | Max Drawdown | Trades | Final Equity |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    rows = []
    for _, r in df.iterrows():
        rows.append(
            f"| {LABELS.get(r['engine'], r['engine'])} "
            f"| {r['total_return_pct']:.4f}% "
            f"| {r['sharpe']:.4f} "
            f"| {r['max_drawdown_pct']:.4f}% "
            f"| {int(r['n_trades'])} "
            f"| ${r['final_equity']:,.2f} |"
        )
    return header + "\n".join(rows) + "\n"


def main() -> None:
    df = load()
    if df.empty:
        print("No results yet. Run the engine legs first.")
        return

    md = (
        f"# Backtest results\n\n"
        f"**Run configuration:** {summary()}\n\n"
        f"_Risk-free rate = {CFG.risk_free}; Sharpe annualised by sqrt({CFG.ann_factor}); "
        f"std uses ddof=1; metrics recomputed identically for every engine from each "
        f"engine's own equity curve._\n\n"
        + to_markdown(df)
    )
    out = RESULTS_DIR / "metrics.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"wrote -> {out}")


if __name__ == "__main__":
    main()
