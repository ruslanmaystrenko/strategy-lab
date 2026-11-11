"""The backtester: what would have happened if you had followed a signal.

The rules are strict on purpose.

* A signal seen at today's close is acted on at tomorrow's open. You cannot
  trade on a price you have not seen yet.
* Every buy and every sell costs something.
* The result is always shown beside simply holding the stock.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def strategy_returns(open_: pd.Series, close: pd.Series, wanted: pd.Series, cost: float = 0.0005) -> pd.DataFrame:
    """Daily returns from following `wanted`, a 1 or 0 decided at each close.

    `cost` is the fraction lost on each buy and each sell. The default, 0.05
    percent, is a fair guess for a large liquid stock.

    Returns a table with, for each day: whether a position was held, the
    strategy's return and the return from simply holding.
    """
    held = wanted.shift(1).fillna(0).astype(int).to_numpy()      # today's position was decided yesterday
    before = np.roll(held, 1)
    before[0] = 0
    o, c = open_.to_numpy(float), close.to_numpy(float)
    prev_close = np.roll(c, 1)
    prev_close[0] = c[0]

    day = np.zeros(len(c))
    staying = (held == 1) & (before == 1)
    entering = (held == 1) & (before == 0)
    leaving = (held == 0) & (before == 1)
    day[staying] = c[staying] / prev_close[staying] - 1          # held all day: close to close
    day[entering] = (c[entering] / o[entering]) * (1 - cost) - 1  # bought at the open
    day[leaving] = (o[leaving] / prev_close[leaving]) * (1 - cost) - 1  # sold at the open

    hold = c / prev_close - 1
    hold[0] = 0.0
    return pd.DataFrame({"held": held, "strategy": day, "hold": hold, "entered": entering, "left": leaving}, index=close.index)


@dataclass
class Summary:
    total_return: float
    yearly_return: float
    worst_drop: float
    yearly_swing: float
    days: int

    def as_dict(self) -> dict:
        return {k: round(v, 4) if isinstance(v, float) else v for k, v in self.__dict__.items()}


def summarize(daily: pd.Series) -> Summary:
    """Turn a series of daily returns into the numbers people ask about.

    * total_return: 1.5 means the money grew by 150 percent.
    * yearly_return: the steady yearly growth rate that gives the same total.
    * worst_drop: the largest fall from a peak, as a negative number.
    * yearly_swing: how much the value bounces around in a year (volatility).
    """
    daily = daily.dropna()
    if len(daily) == 0:
        return Summary(0.0, 0.0, 0.0, 0.0, 0)
    growth = (1 + daily).cumprod()
    total = float(growth.iloc[-1] - 1)
    years = len(daily) / TRADING_DAYS
    yearly = float(growth.iloc[-1] ** (1 / years) - 1) if years > 0 and growth.iloc[-1] > 0 else -1.0
    worst = float((growth / growth.cummax() - 1).min())
    swing = float(daily.std() * np.sqrt(TRADING_DAYS))
    return Summary(total, yearly, worst, swing, len(daily))


def trades(table: pd.DataFrame, open_: pd.Series, cost: float = 0.0005) -> pd.DataFrame:
    """One row per completed trade: when it opened, when it closed and what it made after costs."""
    buys = table.index[table["entered"]]
    sells = table.index[table["left"]]
    rows = []
    for buy in buys:
        later = sells[sells > buy]
        if len(later) == 0:
            break  # still open at the end of the data
        sell = later[0]
        result = (open_.loc[sell] * (1 - cost)) / (open_.loc[buy] / (1 - cost)) - 1
        rows.append({"bought": buy, "sold": sell, "days": (sell - buy).days, "result": float(result)})
    return pd.DataFrame(rows)
