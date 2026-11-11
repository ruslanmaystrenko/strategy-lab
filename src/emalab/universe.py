"""Load the downloaded prices and the record of which stocks were in the S&P 500 on which days."""
import json
import pathlib

import pandas as pd

DATA = pathlib.Path("data")
START = "2005-01-03"


def load_prices() -> tuple[dict[str, pd.DataFrame], pd.Series, dict]:
    """Returns a table per price field (rows are days, columns are stocks), the SPY closes, and notes on the download."""
    info = json.loads((DATA / "download.json").read_text())
    prices = pd.read_parquet(DATA / "prices.parquet")
    prices["date"] = pd.to_datetime(prices["date"])
    wide = {field: prices.pivot(index="date", columns="ticker", values=field).sort_index() for field in ("open", "high", "low", "close", "volume")}
    spy = wide["close"]["SPY"].dropna()
    for field in wide:
        wide[field] = wide[field].drop(columns="SPY")
    return wide, spy, info


def membership(days: pd.DatetimeIndex, tickers: list[str], info: dict) -> pd.DataFrame:
    """True where a stock was in the index on that day."""
    path = DATA / "membership.csv"
    if not path.exists():
        return pd.DataFrame(True, index=days, columns=tickers)
    history = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
    mask = pd.DataFrame(False, index=days, columns=tickers)
    known = set(tickers)
    edges = list(history["date"]) + [pd.Timestamp("2100-01-01")]
    for (start, row), end in zip(zip(history["date"], history["tickers"]), edges[1:]):
        window = (days >= start) & (days < end)
        if window.any():
            mask.loc[window, [t for t in row.split(",") if t in known]] = True
    # The public record stops at its last change date. From there on, use today's list.
    last = history["date"].max()
    current = [t for t in info.get("current_members", []) if t in known]
    if current:
        mask.loc[days > last, :] = False
        mask.loc[days > last, current] = True
    return mask
