"""RSI mean-reversion strategy.

+1 (long)  when RSI < low  (oversold)
-1 (short) when RSI > high (overbought)
 0         otherwise
"""

from __future__ import annotations

import pandas as pd


def rsi(price: pd.Series, period: int = 14) -> pd.Series:
    delta = price.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - 100 / (1 + rs)


def generate_signals(
    price: pd.Series,
    period: int = 14,
    low: float = 30,
    high: float = 70,
) -> pd.Series:
    r = rsi(price, period)
    sig = pd.Series(0, index=price.index, dtype="int8")
    sig[r < low] = 1
    sig[r > high] = -1
    sig[r.isna()] = 0
    return sig
