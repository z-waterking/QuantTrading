"""Paper trading runner — Alpaca paper account, "rebalance to target" 模式.

每次运行做一遍完整对齐：
1. 用 yfinance 拉 ``configs/<x>.yaml`` 中 start..今天 的历史数据
2. 用同一个 ``generate_signals`` 算出**当前应持有**的方向 (+1/-1/0)
3. 查询 Alpaca paper 账户的现持仓，差值用 market 单补齐
4. 退出。可丢进 Windows Task Scheduler / cron 每个交易日盘后跑一次。

跑：
    python -m runners.paper --config configs/ma_cross.yaml --equity 10000
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv

from runners._shared import load_config, load_price
from strategies import load_strategy


def _client():
    try:
        from alpaca.trading.client import TradingClient
    except ImportError as e:
        raise SystemExit(
            'alpaca-py 未安装。请运行: uv pip install -e ".[broker]"'
        ) from e

    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_API_SECRET")
    base = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    if not key or not secret:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET 未配置 (.env)")
    paper = "paper" in base
    return TradingClient(key, secret, paper=paper), base


def _current_qty(client, symbol: str) -> float:
    from alpaca.common.exceptions import APIError

    try:
        pos = client.get_open_position(symbol)
        return float(pos.qty)
    except APIError:
        return 0.0


def _submit_market(client, symbol: str, qty: float, side: str):
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    req = MarketOrderRequest(
        symbol=symbol,
        qty=abs(qty),
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    return client.submit_order(req)


def main() -> None:
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument(
        "--equity",
        type=float,
        default=10000.0,
        help="目标资金规模（美元），用来换算应持仓股数",
    )
    args = ap.parse_args()

    cfg = load_config(args.config)
    symbol = cfg["symbol"]

    # 1) 算最新信号
    end = datetime.utcnow().date()
    start = cfg.get("start", str(end - timedelta(days=400)))
    price = load_price(symbol, start, str(end), force=True)
    signal_fn = load_strategy(cfg["strategy"])
    signal = signal_fn(price, **cfg.get("params", {}))
    target_dir = int(signal.iloc[-1])
    last_close = float(price.iloc[-1])
    target_qty = int((target_dir * args.equity) // last_close)

    print(
        f"latest bar: {price.index[-1].date()}  close={last_close:.2f}  "
        f"signal={target_dir}  target_qty={target_qty}"
    )

    # 2) 对齐持仓
    client, base = _client()
    print(f"alpaca base={base}")

    acct = client.get_account()
    print(f"account: status={acct.status} equity=${acct.equity} buying_power=${acct.buying_power}")

    current_qty = _current_qty(client, symbol)
    delta = target_qty - current_qty
    print(f"current_qty={current_qty}  delta={delta:+g}")

    if delta == 0:
        print("已对齐，不下单。")
        sys.exit(0)

    if acct.status != "ACTIVE":
        raise SystemExit(f"账户状态非 ACTIVE: {acct.status}")

    side = "buy" if delta > 0 else "sell"
    order = _submit_market(client, symbol, delta, side)
    print(f"submitted: id={order.id} side={side} qty={abs(delta)} status={order.status}")


if __name__ == "__main__":
    main()
