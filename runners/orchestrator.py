"""Multi-strategy orchestrator on Alpaca paper.

每隔 ``interval_minutes`` 检查一次：
  对每个子策略计算最新信号 → 对齐 Alpaca paper 持仓 → 把动作写到 JSON。

运行结束后把账户、持仓、配置全部落到 ``reports/run_<id>/``，
配套 ``runners.analyze`` 离线分析。

跑：
    python -m runners.orchestrator --config configs/portfolio.yaml
停：
    Ctrl+C 后会等当前一轮跑完再退出。
"""

from __future__ import annotations

import argparse
import json
import signal
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from runners._shared import load_config, load_price
from runners.paper import _client, _current_qty, _submit_market
from strategies import load_strategy


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).strftime("%Y%m%d_%H%M%S")


def _safe(obj: Any) -> Any:
    """Best-effort json-serializable conversion (Alpaca enums etc.)."""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def _run_one_iter(client, sub_cfgs, equity_per: float, run_dir: Path, iter_n: int) -> list[dict]:
    rows: list[dict] = []
    for sc in sub_cfgs:
        name = sc["name"]
        symbol = sc["symbol"]
        row: dict[str, Any] = {
            "iter": iter_n,
            "ts": _utc_now().isoformat(),
            "name": name,
            "symbol": symbol,
            "signal": None,
            "close": None,
            "current_qty": None,
            "target_qty": None,
            "delta": None,
            "order_id": None,
            "order_status": None,
            "error": None,
        }
        try:
            end = _utc_now().date()
            start = sc.get("start", str(end - timedelta(days=400)))
            price = load_price(symbol, start, str(end))

            sig_fn = load_strategy(sc["strategy"])
            signal_series = sig_fn(price, **sc.get("params", {}))
            target_dir = int(signal_series.iloc[-1])
            last_close = float(price.iloc[-1])
            target_qty = int((target_dir * equity_per) // last_close)
            current_qty = _current_qty(client, symbol)
            delta = target_qty - current_qty

            row.update(
                {
                    "signal": target_dir,
                    "close": round(last_close, 4),
                    "current_qty": current_qty,
                    "target_qty": target_qty,
                    "delta": delta,
                }
            )

            if delta != 0:
                side = "buy" if delta > 0 else "sell"
                order = _submit_market(client, symbol, delta, side)
                row["order_id"] = _safe(order.id)
                row["order_status"] = _safe(order.status)
                row["side"] = side
                print(
                    f"  [{name}] {symbol} sig={target_dir} "
                    f"qty {current_qty}->{target_qty} ({delta:+g}) -> {side} #{order.id}"
                )
            else:
                print(f"  [{name}] {symbol} sig={target_dir} qty={current_qty} (aligned)")
        except Exception as e:  # noqa: BLE001
            row["error"] = str(e)
            print(f"  [{name}] ERROR: {e}")

        rows.append(row)

    out = run_dir / f"iter_{iter_n:04d}.json"
    out.write_text(json.dumps(rows, indent=2, default=_safe), encoding="utf-8")
    return rows


def _snapshot_account(client, run_dir: Path, fname: str) -> None:
    acct = client.get_account()
    payload: dict[str, Any] = {
        "ts": _utc_now().isoformat(),
        "status": _safe(acct.status),
        "equity": _safe(acct.equity),
        "cash": _safe(acct.cash),
        "buying_power": _safe(acct.buying_power),
        "portfolio_value": _safe(getattr(acct, "portfolio_value", None)),
    }
    positions = []
    try:
        for p in client.get_all_positions():
            positions.append(
                {
                    "symbol": p.symbol,
                    "qty": _safe(p.qty),
                    "avg_entry_price": _safe(p.avg_entry_price),
                    "current_price": _safe(p.current_price),
                    "market_value": _safe(p.market_value),
                    "unrealized_pl": _safe(p.unrealized_pl),
                    "unrealized_plpc": _safe(p.unrealized_plpc),
                }
            )
    except Exception as e:  # noqa: BLE001
        positions = [{"_error": str(e)}]
    payload["positions"] = positions
    (run_dir / fname).write_text(json.dumps(payload, indent=2, default=_safe), encoding="utf-8")


def main() -> None:
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-id", default=None, help="自定义 run id；默认时间戳")
    args = ap.parse_args()

    cfg = load_config(args.config)
    run_cfg = cfg["run"]
    sub_cfgs = cfg["strategies"]
    equity_per = run_cfg["total_equity"] / len(sub_cfgs)

    run_id = args.run_id or _stamp()
    run_dir = Path("reports") / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "config.json").write_text(json.dumps(cfg, indent=2, default=_safe), encoding="utf-8")

    print(f"=== orchestrator started: run_id={run_id} ===")
    print(f"strategies      : {[s['name'] for s in sub_cfgs]}")
    print(f"equity / strat  : ${equity_per:,.2f}")
    print(f"duration / step : {run_cfg['duration_hours']}h / {run_cfg['interval_minutes']}min")
    print(f"output dir      : {run_dir}")

    client, base = _client()
    print(f"alpaca base     : {base}")

    _snapshot_account(client, run_dir, "initial_account.json")
    print(f"initial snapshot saved -> {run_dir}/initial_account.json")

    deadline = _utc_now() + timedelta(hours=run_cfg["duration_hours"])
    interval_s = run_cfg["interval_minutes"] * 60

    stopped = {"flag": False}

    def _sigint(_sig, _frame):
        if stopped["flag"]:
            print("force exit.")
            raise SystemExit(130)
        stopped["flag"] = True
        print("\n[Ctrl+C] will stop after current iteration; press again to force.")

    signal.signal(signal.SIGINT, _sigint)

    iter_n = 0
    while _utc_now() < deadline and not stopped["flag"]:
        iter_n += 1
        print(f"\n--- iter {iter_n} @ {_utc_now().isoformat()} ---")
        try:
            _run_one_iter(client, sub_cfgs, equity_per, run_dir, iter_n)
        except Exception as e:  # noqa: BLE001
            print(f"iter {iter_n} fatal: {e}")

        if stopped["flag"] or _utc_now() >= deadline:
            break

        next_at = _utc_now() + timedelta(seconds=interval_s)
        print(f"  next iter ~ {next_at.isoformat()}  (sleep {interval_s}s)")
        # Sleep in small chunks so Ctrl+C is responsive on Windows.
        slept = 0
        while slept < interval_s and not stopped["flag"]:
            time.sleep(min(5, interval_s - slept))
            slept += 5

    _snapshot_account(client, run_dir, "final_account.json")
    (run_dir / "summary.txt").write_text(
        f"iterations: {iter_n}\nstopped_at: {_utc_now().isoformat()}\n",
        encoding="utf-8",
    )
    print(f"\n=== done: {iter_n} iterations ===")
    print(f"results in {run_dir}")
    print(f"analyze with: python -m runners.analyze --run-dir {run_dir.as_posix()}")


if __name__ == "__main__":
    main()
