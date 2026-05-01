"""Analyze a finished orchestrator run.

读取 ``reports/run_<id>/`` 下的所有 ``iter_*.json`` + ``initial/final_account.json``，
打印每个策略的下单次数、最终持仓 / 浮盈，并给出一个简单对比表。

跑：
    python -m runners.analyze --run-dir reports/run_20260501_120000
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def _load_json(p: Path) -> dict | list:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        raise SystemExit(f"not a directory: {run_dir}")

    cfg = _load_json(run_dir / "config.json")
    initial = _load_json(run_dir / "initial_account.json") if (run_dir / "initial_account.json").exists() else {}
    final = _load_json(run_dir / "final_account.json") if (run_dir / "final_account.json").exists() else {}

    iter_files = sorted(run_dir.glob("iter_*.json"))
    if not iter_files:
        print("no iter_*.json found.")
        return

    by_strat: dict[str, list[dict]] = defaultdict(list)
    for f in iter_files:
        rows = _load_json(f)
        if not isinstance(rows, list):
            continue
        for r in rows:
            by_strat[r["name"]].append(r)

    print(f"=== run: {run_dir.name} ===")
    print(f"iterations    : {len(iter_files)}")
    print(f"start equity  : {initial.get('equity')}")
    print(f"end equity    : {final.get('equity')}")
    if initial.get("equity") and final.get("equity"):
        try:
            d = float(final["equity"]) - float(initial["equity"])
            pct = d / float(initial["equity"]) * 100
            print(f"pnl (账户)    : {d:+.2f}  ({pct:+.3f}%)")
        except Exception:  # noqa: BLE001
            pass

    print()
    print(f"{'strategy':<18} {'orders':>6} {'errors':>6} {'last_signal':>11} {'last_qty':>9}")
    print("-" * 60)
    rows_summary = []
    for name in [s["name"] for s in cfg["strategies"]]:
        recs = by_strat.get(name, [])
        orders = sum(1 for r in recs if r.get("order_id"))
        errors = sum(1 for r in recs if r.get("error"))
        last = recs[-1] if recs else {}
        rows_summary.append(
            {
                "strategy": name,
                "orders": orders,
                "errors": errors,
                "last_signal": last.get("signal"),
                "last_target_qty": last.get("target_qty"),
            }
        )
        print(
            f"{name:<18} {orders:>6} {errors:>6} {str(last.get('signal')):>11} "
            f"{str(last.get('target_qty')):>9}"
        )

    print()
    print("final positions:")
    for p in (final.get("positions") or []):
        if "_error" in p:
            print(f"  ERR: {p['_error']}")
            continue
        print(
            f"  {p.get('symbol'):<6} qty={p.get('qty')} avg={p.get('avg_entry_price')} "
            f"mv={p.get('market_value')} pl={p.get('unrealized_pl')}"
        )

    out = run_dir / "summary.json"
    out.write_text(
        json.dumps(
            {
                "run": run_dir.name,
                "iterations": len(iter_files),
                "initial_equity": initial.get("equity"),
                "final_equity": final.get("equity"),
                "strategies": rows_summary,
                "final_positions": final.get("positions", []),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\nsummary written to {out}")


if __name__ == "__main__":
    main()
