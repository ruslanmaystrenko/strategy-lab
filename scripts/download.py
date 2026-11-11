"""Download daily prices for every stock that has been in the S&P 500, plus the index fund SPY.

Run from the repo root:  python scripts/download.py

Two lists decide which stocks to fetch:
* today's members, and
* a public record of who was in the index on each past date.

The second list matters. Testing only today's members means testing only the
companies that survived, which makes any strategy look better than it was.
Prices are adjusted for splits and dividends. Everything lands in data/,
which is never committed.
"""
import io
import json
import pathlib
import sys

import pandas as pd
import requests
import yfinance as yf

DATA = pathlib.Path("data")
START = "2003-01-01"
CURRENT = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
HISTORY_REPO = "https://api.github.com/repos/fja05680/sp500/contents"


def yahoo(symbol: str) -> str:
    return symbol.strip().replace(".", "-")


def current_members() -> list[str]:
    table = pd.read_csv(io.StringIO(requests.get(CURRENT, timeout=30).text))
    return sorted({yahoo(s) for s in table["Symbol"]})


def membership_history() -> pd.DataFrame | None:
    """One row per date the index changed, with the full member list on that date."""
    try:
        files = requests.get(HISTORY_REPO, timeout=30).json()
        names = [f for f in files if f["name"].lower().endswith(".csv") and "historical components" in f["name"].lower()]
        newest = sorted(names, key=lambda f: f["name"])[-1]
        table = pd.read_csv(io.StringIO(requests.get(newest["download_url"], timeout=60).text))
        table["date"] = pd.to_datetime(table["date"])
        table["tickers"] = table["tickers"].map(lambda row: sorted({yahoo(s) for s in row.split(",")}))
        print(f"membership history: {newest['name']}, {len(table)} change dates")
        return table[["date", "tickers"]]
    except Exception as problem:  # the test still runs without it, and says so
        print(f"could not get membership history: {problem}")
        return None


def main() -> None:
    DATA.mkdir(exist_ok=True)
    members = current_members()
    history = membership_history()
    wanted = set(members) | {"SPY"}
    if history is not None:
        recent = history[history["date"] >= "2004-06-01"]
        for row in recent["tickers"]:
            wanted |= set(row)
        history.assign(tickers=history["tickers"].map(",".join)).to_csv(DATA / "membership.csv", index=False)
    wanted = sorted(wanted)
    print(f"{len(members)} current members, {len(wanted)} symbols to fetch")

    pieces, missing = [], []
    for start in range(0, len(wanted), 100):
        batch = wanted[start:start + 100]
        raw = yf.download(batch, start=START, auto_adjust=True, group_by="ticker", threads=True, progress=False)
        for symbol in batch:
            try:
                one = raw[symbol].dropna(subset=["Close"])
            except KeyError:
                one = pd.DataFrame()
            if len(one) < 50:
                missing.append(symbol)
                continue
            one = one.reset_index().rename(columns=str.lower)[["date", "open", "high", "low", "close", "volume"]]
            one.insert(1, "ticker", symbol)
            pieces.append(one)
        print(f"  {min(start + 100, len(wanted))}/{len(wanted)} done, {len(missing)} with no data so far", flush=True)

    prices = pd.concat(pieces, ignore_index=True)
    prices.to_parquet(DATA / "prices.parquet", index=False)
    (DATA / "download.json").write_text(json.dumps({
        "symbols_wanted": len(wanted), "symbols_found": prices["ticker"].nunique(), "missing": missing,
        "first_day": str(prices["date"].min().date()), "last_day": str(prices["date"].max().date()), "rows": len(prices),
        "current_members": members, "has_membership_history": history is not None,
    }, indent=1))
    print(f"saved {len(prices):,} rows for {prices['ticker'].nunique()} symbols, {len(missing)} had no data")


if __name__ == "__main__":
    sys.exit(main())
