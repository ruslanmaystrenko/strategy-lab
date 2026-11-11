"""Signals: rules that say, at the close of each day, whether to be in a stock or out of it.

Every signal here uses only prices up to and including that day's close.
"""
import numpy as np
import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average: a running average that weights recent days more."""
    return series.ewm(span=span, adjust=False).mean()


def ema_crossover(close: pd.Series, fast: int = 50, slow: int = 200) -> pd.Series:
    """Be in the stock from the day the fast average crosses above the slow one,
    until the day it crosses back below.

    Returns 1 for "in" and 0 for "out", decided at each day's close.

    Two details matter:
    * The first `slow` days are ignored. The averages have not settled yet.
    * A position only opens on an actual cross. If the fast average is already
      above the slow one when the data starts, we wait for the next cross.
    """
    fast_line, slow_line = ema(close, fast), ema(close, slow)
    above = (fast_line > slow_line).to_numpy()
    crossed_up = above & ~np.roll(above, 1)
    crossed_up[: slow + 1] = False

    wanted = np.zeros(len(close), dtype=np.int8)
    holding = False
    for i in range(len(close)):
        if not holding and crossed_up[i]:
            holding = True
        elif holding and not above[i]:
            holding = False
        wanted[i] = holding
    return pd.Series(wanted, index=close.index, name="wanted")
