"""Smoke test for the ma_cross strategy logic (no network)."""

import numpy as np
import pandas as pd

from strategies.ma_cross import generate_signals


def test_ma_cross_basic():
    n = 200
    rng = np.random.default_rng(0)
    price = pd.Series(
        100 + rng.normal(0, 1, n).cumsum(),
        index=pd.date_range("2024-01-01", periods=n, freq="B"),
    )
    sig = generate_signals(price, fast=5, slow=20)
    assert len(sig) == n
    assert set(sig.unique()).issubset({-1, 0, 1})
    # warm-up bars must be 0
    assert (sig.iloc[:19] == 0).all()
