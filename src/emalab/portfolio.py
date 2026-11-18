"""Backtest a whole portfolio from a table of target weights."""
import pandas as pd


def portfolio_returns(opens: pd.DataFrame, closes: pd.DataFrame, weights: pd.DataFrame, cost: float = 0.0005) -> pd.Series:
    """Daily returns from holding `weights`.

    `weights` has a row per day and a column per stock: the share of the money
    wanted in each stock, decided at that day's close. Rows may add up to less
    than 1, and the rest sits in cash.

    Each day has two halves. Overnight, the portfolio still holds what it
    traded to at yesterday's open, with each holding grown or shrunk by its
    own price move since then. At today's open it trades to what was wanted
    at the last close, pays the cost on everything that changed hands, and
    holds that to the close.

    Prices moving apart is itself a reason to trade: keeping every stock at
    an equal share means selling a little of what rose and buying a little of
    what fell, every day. That trading is charged too.
    """
    overnight = (opens / closes.shift(1) - 1).fillna(0)
    daytime = (closes / opens - 1).fillna(0)
    new = weights.shift(1).fillna(0)      # traded to at today's open
    old = weights.shift(2).fillna(0)      # traded to at yesterday's open
    grown = old * (1 + daytime.shift(1).fillna(0))                         # yesterday's holdings at yesterday's close
    at_close = grown.div(grown.sum(axis=1) + 1 - old.sum(axis=1), axis=0)  # as shares of the portfolio, cash included
    overnight_return = (at_close * overnight).sum(axis=1)
    held = (at_close * (1 + overnight)).div(1 + overnight_return, axis=0)   # shares held coming into today's open
    traded = (new - held).abs().sum(axis=1)
    return (1 + overnight_return) * (1 - cost * traded) * (1 + (new * daytime).sum(axis=1)) - 1
