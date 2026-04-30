"""Strategy registry."""

from importlib import import_module
from typing import Callable

import pandas as pd


def load_strategy(name: str) -> Callable[..., pd.Series]:
    """Load ``strategies.<name>.generate_signals`` by string name."""
    mod = import_module(f"strategies.{name}")
    fn = getattr(mod, "generate_signals", None)
    if fn is None:
        raise AttributeError(f"strategies.{name} has no generate_signals()")
    return fn
