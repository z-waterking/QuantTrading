"""Live trading runner stub.

⚠️ 真实下单。运行前要二次确认。
- Alpaca: 切换 ALPACA_BASE_URL 为 https://api.alpaca.markets
- IB: 启动 TWS / IB Gateway，端口默认 7497(paper)/7496(live)
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from runners._shared import load_config


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--yes", action="store_true", help="跳过二次确认（不推荐）")
    args = ap.parse_args()

    cfg = load_config(args.config)

    if not args.yes:
        prompt = (
            f"即将启动 LIVE 交易: strategy={cfg['strategy']} symbol={cfg['symbol']}\n"
            "确认请输入大写 GO: "
        )
        if input(prompt).strip() != "GO":
            print("已取消。")
            sys.exit(0)

    base = os.getenv("ALPACA_BASE_URL", "")
    if "paper" in base:
        raise SystemExit(
            "ALPACA_BASE_URL 仍指向 paper-api，refusing to run live。"
            "如果你确实想实盘，请改为 https://api.alpaca.markets。"
        )

    raise NotImplementedError(
        f"live trading 还未实现 (strategy={cfg['strategy']}). "
        "见 runners/live.py 顶部说明。"
    )


if __name__ == "__main__":
    main()
