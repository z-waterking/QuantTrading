"""Double moving-average crossover strategy.

Signal:
    +1 (long)  when fast MA > slow MA
    -1 (short) when fast MA < slow MA
     0         otherwise (e.g. NaN warm-up period)
"""

from __future__ import annotations

import pandas as pd


def generate_signals(price: pd.Series, fast: int = 20, slow: int = 60) -> pd.Series:
    """Return a -1/0/+1 signal series aligned to ``price.index``."""
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be < slow ({slow})")

    fast_ma = price.rolling(fast).mean()
    slow_ma = price.rolling(slow).mean()

    sig = pd.Series(0, index=price.index, dtype="int8")
    sig[fast_ma > slow_ma] = 1
    sig[fast_ma < slow_ma] = -1
    sig[fast_ma.isna() | slow_ma.isna()] = 0
    return sig
