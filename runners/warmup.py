"""Pre-fetch all symbols into local cache so orchestrator doesn't hit yfinance rate limit.

Usage:
    python -m runners.warmup --config configs/portfolio.yaml
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone

from runners._shared import load_config, load_price


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = load_config(args.config)
    today = datetime.now(timezone.utc).date()

    for sc in cfg["strategies"]:
        symbol = sc["symbol"]
        start = sc.get("start", str(today - timedelta(days=400)))
        end = str(today)
        print(f"warmup: {symbol} {start}..{end} ...", end=" ", flush=True)
        try:
            price = load_price(symbol, start, end, force=True, retry=5, retry_sleep=10)
            print(f"OK ({len(price)} bars, last={price.iloc[-1]:.2f})")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL: {e}")
        time.sleep(3)  # be polite to yfinance


if __name__ == "__main__":
    main()
