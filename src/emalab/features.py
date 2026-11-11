"""Turn each golden cross into one row: what was known that day, and what happened next.

Everything in the "known that day" columns uses prices up to that day's close
and nothing later. Every value is a ratio or a percentage, never a raw price,
so a 30 dollar stock and a 300 dollar stock are described the same way.
"""
import numpy as np
import pandas as pd

from .signals import ema, ema_crossover

FEATURES = [
    "rsi_14", "macd_gap", "ema50_slope", "price_vs_ema200", "momentum_5", "momentum_21", "momentum_63",
    "daily_range", "cci_20", "band_position", "volume_surge", "below_year_high", "days_below",
    "market_above_trend", "market_momentum_63",
]


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    change = close.diff()
    gain = change.clip(lower=0).ewm(span=window, adjust=False).mean()
    loss = (-change.clip(upper=0)).ewm(span=window, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def describe_days(frame: pd.DataFrame, market_close: pd.Series) -> pd.DataFrame:
    """Indicators for every day of one stock. `frame` has open, high, low, close, volume."""
    o, h, l, c, v = (frame[k] for k in ("open", "high", "low", "close", "volume"))
    e50, e200 = ema(c, 50), ema(c, 200)
    macd = ema(c, 12) - ema(c, 26)
    typical = (h + l + c) / 3
    mean20, std20 = c.rolling(20).mean(), c.rolling(20).std()
    true_range = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    deviation = (typical - typical.rolling(20).mean()).abs().rolling(20).mean()
    below = (e50 <= e200).astype(int)
    market = market_close.reindex(c.index).ffill()

    out = pd.DataFrame(index=c.index)
    out["rsi_14"] = rsi(c)
    out["macd_gap"] = (macd - ema(macd, 9)) / c
    out["ema50_slope"] = e50 / e50.shift(5) - 1
    out["price_vs_ema200"] = c / e200 - 1
    out["momentum_5"] = c / c.shift(5) - 1
    out["momentum_21"] = c / c.shift(21) - 1
    out["momentum_63"] = c / c.shift(63) - 1
    out["daily_range"] = true_range.rolling(14).mean() / c
    out["cci_20"] = (typical - typical.rolling(20).mean()) / (0.015 * deviation)
    out["band_position"] = (c - mean20) / (2 * std20)
    out["volume_surge"] = v / v.rolling(60).mean()
    out["below_year_high"] = c / c.rolling(252).max() - 1
    out["days_below"] = below.groupby((below == 0).cumsum()).cumsum().shift(1)   # how long the fast line sat under the slow one
    out["market_above_trend"] = (market > ema(market, 200)).astype(float)
    out["market_momentum_63"] = market / market.shift(63) - 1
    return out.replace([np.inf, -np.inf], np.nan)


def crossover_events(frame: pd.DataFrame, market_close: pd.Series, cost: float = 0.0005) -> pd.DataFrame:
    """One row per golden cross for one stock.

    Outcome columns, all measured from the next day's open, since that is the
    first price you could have bought at:
    * forward_10: return over the following 10 trading days
    * trade_result: return if held until the fast line crossed back under, after costs
    * known_on: the date the trade closed, which is the first day its result could be used for training
    """
    c, o = frame["close"], frame["open"]
    wanted = ema_crossover(c)
    opened = (wanted.diff() == 1).to_numpy()
    closed = (wanted.diff() == -1).to_numpy()
    days = c.index
    described = describe_days(frame, market_close)
    rows = []
    for i in np.flatnonzero(opened):
        if i + 1 >= len(days):
            continue
        buy = o.iloc[i + 1] / (1 - cost)
        row = {"date": days[i], **described.iloc[i].to_dict()}
        row["forward_10"] = c.iloc[i + 10] / o.iloc[i + 1] - 1 if i + 10 < len(days) else np.nan
        later = np.flatnonzero(closed[i + 1:])
        if len(later) and i + 1 + later[0] + 1 < len(days):
            j = i + 1 + later[0] + 1                      # the open after the cross back down
            row["trade_result"] = o.iloc[j] * (1 - cost) / buy - 1
            row["known_on"] = days[j]
        else:
            row["trade_result"], row["known_on"] = np.nan, pd.NaT   # still open when the data ends
        rows.append(row)
    return pd.DataFrame(rows)
