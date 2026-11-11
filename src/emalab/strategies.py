"""Each strategy turns prices into target weights: what share of the money to hold in each stock, decided at each close.

`member` is True where a stock was in the index that day. Nothing here looks past the current row.
"""
import numpy as np
import pandas as pd

from .features import rsi
from .signals import ema_crossover


def month_ends(days: pd.DatetimeIndex) -> pd.Series:
    """True on the last trading day of each month."""
    months = pd.Series(days.to_period("M"), index=days)
    return months != months.shift(-1)


def hold_everything(closes, member, spy):
    return member.div(member.sum(axis=1), axis=0).fillna(0)


def golden_cross(closes, member, spy):
    wanted = pd.DataFrame({t: ema_crossover(closes[t].dropna()) for t in closes if closes[t].count() > 400}).reindex(closes.index).fillna(0)
    return hold_everything(closes, member, spy) * wanted.reindex(columns=closes.columns).fillna(0)


def momentum(closes, member, spy, top_share=0.2):
    past_year = (closes.shift(21) / closes.shift(252) - 1).where(member)     # the past year, skipping the latest month
    rank = past_year.rank(axis=1, pct=True)
    chosen = (rank > 1 - top_share).astype(float)
    weights = chosen.div(chosen.sum(axis=1), axis=0)
    return weights.where(month_ends(closes.index), np.nan).ffill().fillna(0)   # only change at month ends


def market_trend_filter(closes, member, spy):
    spy = spy.reindex(closes.index).ffill()
    risk_on = (spy > spy.rolling(200).mean()).where(month_ends(closes.index)).ffill().fillna(False).astype(bool)
    return hold_everything(closes, member, spy).mul(risk_on.astype(float), axis=0)


def dip_buying(closes, member, spy, slots=20, max_days=10):
    uptrend = closes > closes.rolling(200).mean()
    oversold = closes.apply(rsi, window=2) < 10
    recovered = closes > closes.rolling(5).mean()
    enter, leave = (uptrend & oversold & member).to_numpy(), recovered.to_numpy()
    held = np.zeros(enter.shape, dtype=bool)
    age = np.zeros(enter.shape[1], dtype=int)
    for day in range(1, len(enter)):
        staying = held[day - 1] & ~leave[day] & (age < max_days)
        held[day] = staying | enter[day]
        age = np.where(held[day], np.where(staying, age + 1, 1), 0)
    count = held.sum(axis=1, keepdims=True)
    size = np.minimum(1 / slots, 1 / np.maximum(count, 1))                   # 5 percent each, or an even split if more than 20 qualify
    return pd.DataFrame(held * size, index=closes.index, columns=closes.columns)


STRATEGIES = {
    "Hold everything": hold_everything,
    "Golden cross": golden_cross,
    "Momentum": momentum,
    "Market trend filter": market_trend_filter,
    "Dip buying": dip_buying,
}
