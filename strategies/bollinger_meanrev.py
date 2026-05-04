"""Bollinger band mean-reversion strategy.

+1 (long)  after close breaks below the lower band, until it reaches the mid band.
-1 (short) after close breaks above the upper band, until it reaches the mid band.
 0         when flat or during the warm-up period.
"""

from __future__ import annotations

import pandas as pd


def generate_signals(
    price: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.Series:
    """Return a -1/0/+1 signal series aligned to ``price.index``."""
    if window < 2:
        raise ValueError(f"window ({window}) must be >= 2")
    if num_std <= 0:
        raise ValueError(f"num_std ({num_std}) must be > 0")

    mid = price.rolling(window).mean()
    band_width = price.rolling(window).std() * num_std
    upper = mid + band_width
    lower = mid - band_width

    sig = pd.Series(0, index=price.index, dtype="int8")
    current_position = 0

    for date in price.index:
        if pd.isna(mid.loc[date]) or pd.isna(band_width.loc[date]):
            current_position = 0
            continue

        close = price.loc[date]
        if current_position == 0:
            if close < lower.loc[date]:
                current_position = 1
            elif close > upper.loc[date]:
                current_position = -1
        elif current_position == 1 and close >= mid.loc[date]:
            current_position = 0
        elif current_position == -1 and close <= mid.loc[date]:
            current_position = 0

        sig.loc[date] = current_position

    return sig
