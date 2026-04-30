"""Paper trading runner stub.

要跑模拟盘需要先在 https://alpaca.markets/ 注册一个免费账号，
然后把 API key/secret 写进 .env，再 ``uv pip install -e ".[broker]"``。

实现要点（后续填）：
- 用 alpaca-py 的 ``PaperTradingClient``
- 订阅实时行情，生成滚动信号
- 把 ``signal`` diff 转成 buy/sell market 单
"""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

from runners._shared import load_config


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)

    if not os.getenv("ALPACA_API_KEY"):
        raise SystemExit(
            "ALPACA_API_KEY 未设置。请先 cp .env.example .env 并填入 paper account 凭据。"
        )

    raise NotImplementedError(
        f"paper trading 还未实现 (strategy={cfg['strategy']}). "
        "见 runners/paper.py 顶部说明。"
    )


if __name__ == "__main__":
    main()
