"""Time-series momentum: long if N-day return > 0, short if < 0."""

from __future__ import annotations

import pandas as pd


def generate_signals(price: pd.Series, lookback: int = 60) -> pd.Series:
    ret = price.pct_change(lookback)
    sig = pd.Series(0, index=price.index, dtype="int8")
    sig[ret > 0] = 1
    sig[ret < 0] = -1
    sig[ret.isna()] = 0
    return sig
