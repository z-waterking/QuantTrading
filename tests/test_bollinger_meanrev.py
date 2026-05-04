"""Smoke test for the Bollinger mean-reversion strategy logic (no network)."""

import numpy as np
import pandas as pd
import pytest

from strategies.bollinger_meanrev import generate_signals


def test_bollinger_meanrev_basic():
    sample_size = 200
    rng = np.random.default_rng(1)
    price = pd.Series(
        100 + rng.normal(0, 1, sample_size).cumsum(),
        index=pd.date_range("2024-01-01", periods=sample_size, freq="B"),
    )
    sig = generate_signals(price, window=20, num_std=2.0)
    assert len(sig) == sample_size
    assert set(sig.unique()).issubset({-1, 0, 1})
    assert (sig.iloc[:19] == 0).all()


def test_bollinger_meanrev_holds_until_mid_band():
    price = pd.Series(
        [100, 100, 100, 90, 95, 100, 110, 105, 106],
        index=pd.date_range("2024-01-01", periods=9, freq="B"),
    )

    sig = generate_signals(price, window=3, num_std=0.5)

    assert sig.tolist() == [0, 0, 0, 1, 0, -1, -1, 0, 0]


def test_bollinger_meanrev_rejects_invalid_params():
    price = pd.Series([100, 101, 102])

    with pytest.raises(ValueError, match="window"):
        generate_signals(price, window=1)

    with pytest.raises(ValueError, match="num_std"):
        generate_signals(price, num_std=0)
