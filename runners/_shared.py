"""Shared utilities for runners (config loading, yfinance data cache)."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _cache_path(symbol: str, start: str, end: str) -> Path:
    key = hashlib.md5(f"{symbol}|{start}|{end}".encode()).hexdigest()[:12]
    return DATA_DIR / f"{symbol}_{key}.parquet"


def load_price(
    symbol: str,
    start: str,
    end: str,
    *,
    force: bool = False,
    max_age_minutes: int = 60,
    retry: int = 3,
    retry_sleep: float = 5.0,
) -> pd.Series:
    """Daily adjusted close, cached on disk.

    - 命中缓存且文件 mtime 不超过 ``max_age_minutes`` 就直接读
    - 限流时按 ``retry_sleep`` 退避重试
    """
    cache = _cache_path(symbol, start, end)

    if not force and cache.exists():
        age_min = (
            datetime.now(timezone.utc).timestamp() - cache.stat().st_mtime
        ) / 60
        if age_min <= max_age_minutes:
            return pd.read_parquet(cache)["close"]

    import yfinance as yf

    last_err: Exception | None = None
    for attempt in range(1, retry + 1):
        try:
            df = yf.download(
                symbol,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if df.empty:
                raise RuntimeError(f"yfinance empty for {symbol} {start}..{end}")

            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(symbol, axis=1, level=1, drop_level=True)

            close = df["Close"].dropna()
            close.name = "close"
            close.to_frame().to_parquet(cache)
            return close
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retry:
                time.sleep(retry_sleep * attempt)

    # 网络挂掉但本地仍有旧缓存就用旧的，比直接报错好
    if cache.exists():
        return pd.read_parquet(cache)["close"]

    raise RuntimeError(f"failed to fetch {symbol} after {retry} retries: {last_err}")
