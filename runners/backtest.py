"""Backtest runner: download price -> generate signals -> compute equity & metrics."""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from runners._shared import load_config, load_price
from strategies import load_strategy


def run_backtest(cfg: dict) -> dict:
    price = load_price(cfg["symbol"], cfg["start"], cfg["end"])
    signal_fn = load_strategy(cfg["strategy"])
    signal = signal_fn(price, **cfg.get("params", {}))

    # Position is the previous bar's signal (no look-ahead).
    pos = signal.shift(1).fillna(0)
    ret = price.pct_change().fillna(0)
    strat_ret = pos * ret
    equity = (1 + strat_ret).cumprod()

    # Metrics
    n = len(strat_ret)
    if n == 0:
        return {"equity": equity, "metrics": {}}

    ann_factor = 252
    total_ret = float(equity.iloc[-1] - 1)
    ann_ret = float((1 + total_ret) ** (ann_factor / n) - 1) if n > 0 else 0.0
    ann_vol = float(strat_ret.std() * np.sqrt(ann_factor))
    sharpe = float(ann_ret / ann_vol) if ann_vol > 0 else 0.0
    drawdown = (equity / equity.cummax() - 1).min()

    metrics = {
        "bars": n,
        "total_return": round(total_ret, 4),
        "annual_return": round(ann_ret, 4),
        "annual_vol": round(ann_vol, 4),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(float(drawdown), 4),
    }
    return {"equity": equity, "metrics": metrics}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to strategy yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    print(f"running backtest: strategy={cfg['strategy']} symbol={cfg['symbol']} "
          f"period={cfg['start']}..{cfg['end']}")

    result = run_backtest(cfg)
    print("metrics:")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
