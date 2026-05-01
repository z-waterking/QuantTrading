"""Donchian channel breakout.

+1 when close hits N-day high.
-1 when close hits N-day low.
 0 otherwise.
"""

from __future__ import annotations

import pandas as pd


def generate_signals(price: pd.Series, lookback: int = 20) -> pd.Series:
    high = price.rolling(lookback).max()
    low = price.rolling(lookback).min()
    sig = pd.Series(0, index=price.index, dtype="int8")
    sig[price >= high] = 1
    sig[price <= low] = -1
    sig[high.isna() | low.isna()] = 0
    return sig
