"""Backtest runner: download price -> generate signals -> compute equity & metrics."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from runners._shared import load_config, load_price
from strategies import load_strategy


def run_backtest(cfg: dict) -> dict:
    price = load_price(cfg["symbol"], cfg["start"], cfg["end"])
    signal_fn = load_strategy(cfg["strategy"])
    signal = signal_fn(price, **cfg.get("params", {}))

    # Position is the previous bar's signal (no look-ahead).
    position = signal.shift(1).fillna(0).astype("int8")
    daily_return = price.pct_change().fillna(0)
    strategy_return = position * daily_return
    equity = (1 + strategy_return).cumprod()
    drawdown = equity / equity.cummax() - 1

    # Metrics
    bar_count = len(strategy_return)
    if bar_count == 0:
        return {
            "price": price,
            "signal": signal,
            "position": position,
            "daily_return": daily_return,
            "strategy_return": strategy_return,
            "equity": equity,
            "drawdown": drawdown,
            "metrics": {},
        }

    ann_factor = 252
    total_ret = float(equity.iloc[-1] - 1)
    ann_ret = float((1 + total_ret) ** (ann_factor / bar_count) - 1)
    ann_vol = float(strategy_return.std() * np.sqrt(ann_factor))
    sharpe = float(ann_ret / ann_vol) if ann_vol > 0 else 0.0
    trade_count = int((position.diff().fillna(position).abs() > 0).sum())

    metrics = {
        "bars": bar_count,
        "total_return": round(total_ret, 4),
        "annual_return": round(ann_ret, 4),
        "annual_vol": round(ann_vol, 4),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(float(drawdown.min()), 4),
        "final_equity": round(float(equity.iloc[-1]), 4),
        "trades": trade_count,
        "exposure": round(float((position != 0).mean()), 4),
        "long_days": int((position > 0).sum()),
        "short_days": int((position < 0).sum()),
    }
    return {
        "price": price,
        "signal": signal,
        "position": position,
        "daily_return": daily_return,
        "strategy_return": strategy_return,
        "equity": equity,
        "drawdown": drawdown,
        "metrics": metrics,
    }


def _default_report_dir(cfg: dict) -> Path:
    strategy = str(cfg["strategy"]).replace("/", "_").replace("\\", "_")
    symbol = str(cfg["symbol"]).replace("/", "_").replace("\\", "_")
    return Path("reports") / f"backtest_{strategy}_{symbol}"


def _format_metric(name: str, value: object) -> str:
    if name in {"total_return", "annual_return", "annual_vol", "max_drawdown", "exposure"}:
        return f"{float(value) * 100:.2f}%"
    if name == "final_equity":
        return f"{float(value):.4f}x"
    return str(value)


def _write_report(cfg: dict, result: dict, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)

    metrics = result["metrics"]
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": cfg,
        "metrics": metrics,
    }
    (report_dir / "metrics.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    rows = pd.DataFrame(
        {
            "close": result["price"],
            "signal": result["signal"],
            "position": result["position"],
            "daily_return": result["daily_return"],
            "strategy_return": result["strategy_return"],
            "equity": result["equity"],
            "drawdown": result["drawdown"],
        }
    )
    rows.index.name = "date"
    rows.to_csv(report_dir / "equity.csv", encoding="utf-8")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, height_ratios=[3, 1])
    axes[0].plot(result["equity"].index, result["equity"], color="#1f77b4", linewidth=1.6)
    axes[0].set_title(f"{cfg['strategy']} on {cfg['symbol']} equity")
    axes[0].set_ylabel("Equity multiple")
    axes[0].grid(True, alpha=0.25)

    axes[1].fill_between(
        result["drawdown"].index,
        result["drawdown"].to_numpy() * 100,
        0,
        color="#d62728",
        alpha=0.35,
    )
    axes[1].set_ylabel("Drawdown %")
    axes[1].grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(report_dir / "equity.png", dpi=140)
    plt.close(fig)

    metric_lines = ["| metric | value |", "|---|---:|"]
    for metric_name, metric_value in metrics.items():
        metric_lines.append(f"| {metric_name} | {_format_metric(metric_name, metric_value)} |")

    params = cfg.get("params", {})
    summary = "\n".join(
        [
            f"# Backtest: {cfg['strategy']} / {cfg['symbol']}",
            "",
            f"- Period: {cfg['start']} to {cfg['end']}",
            f"- Params: `{json.dumps(params, ensure_ascii=False)}`",
            f"- Generated: {payload['generated_at']}",
            "",
            "## Metrics",
            "",
            *metric_lines,
            "",
            "## Files",
            "",
            "- `equity.png`: equity and drawdown chart",
            "- `equity.csv`: daily close, signal, position, return, equity, drawdown",
            "- `metrics.json`: config and raw metrics",
            "",
        ]
    )
    (report_dir / "summary.md").write_text(summary, encoding="utf-8")
    return report_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to strategy yaml")
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Directory for summary.md, metrics.json, equity.csv, and equity.png",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    print(f"running backtest: strategy={cfg['strategy']} symbol={cfg['symbol']} "
          f"period={cfg['start']}..{cfg['end']}")

    result = run_backtest(cfg)
    print("metrics:")
    for metric_name, metric_value in result["metrics"].items():
        print(f"  {metric_name}: {_format_metric(metric_name, metric_value)}")

    report_dir = Path(args.report_dir) if args.report_dir else _default_report_dir(cfg)
    report_dir = _write_report(cfg, result, report_dir)
    print(f"report: {report_dir / 'summary.md'}")
    print(f"chart : {report_dir / 'equity.png'}")


if __name__ == "__main__":
    main()
