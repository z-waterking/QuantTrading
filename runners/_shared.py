"""Shared utilities for runners (config loading, yfinance data cache)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_price(symbol: str, start: str, end: str, *, force: bool = False) -> pd.Series:
    """Daily adjusted close for ``symbol`` between ``start`` and ``end``.

    Cached on disk under ``data/<key>.parquet``; pass ``force=True`` to refresh.
    """
    key = hashlib.md5(f"{symbol}|{start}|{end}".encode()).hexdigest()[:12]
    cache = DATA_DIR / f"{symbol}_{key}.parquet"

    if cache.exists() and not force:
        return pd.read_parquet(cache)["close"]

    import yfinance as yf

    df = yf.download(
        symbol,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        raise RuntimeError(f"yfinance returned no data for {symbol} {start}..{end}")

    # yfinance 新版返回 MultiIndex 列 (price_type, ticker)；统一拍平
    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs(symbol, axis=1, level=1, drop_level=True)

    close = df["Close"].dropna()
    close.name = "close"
    close.to_frame().to_parquet(cache)
    return close
