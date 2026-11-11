"""Backtest a whole portfolio from a table of target weights."""
import pandas as pd


def portfolio_returns(opens: pd.DataFrame, closes: pd.DataFrame, weights: pd.DataFrame, cost: float = 0.0005) -> pd.Series:
    """Daily returns from holding `weights`.

    `weights` has a row per day and a column per stock: the share of the money
    wanted in each stock, decided at that day's close. Rows may add up to less
    than 1, and the rest sits in cash.

    Each day has two halves. Overnight, the portfolio still holds what was
    wanted two closes ago. At the open it trades to what was wanted at the
    last close, pays the cost on whatever changed, and holds that to the close.
    """
    last_close = closes.shift(1)
    overnight = (opens / last_close - 1).fillna(0)
    daytime = (closes / opens - 1).fillna(0)
    new = weights.shift(1).fillna(0)      # decided at the last close
    old = weights.shift(2).fillna(0)      # held coming into today
    traded = (new - old).abs().sum(axis=1)
    return (1 + (old * overnight).sum(axis=1)) * (1 - cost * traded) * (1 + (new * daytime).sum(axis=1)) - 1
