"""The honest baseline: the plain 50 over 200 EMA crossover, with no model at all.

Run from the repo root:  python scripts/baseline.py

For every stock, on the days it was in the S&P 500:
* follow the crossover, buying and selling at the next day's open, paying a cost each time
* compare with simply holding that stock

Then the same comparison for a whole portfolio that gives every member an
equal slice of the money. The slice is either always invested (holding) or
invested only while the crossover says so (the strategy, in cash otherwise).
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from emalab.backtest import strategy_returns, summarize, trades  # noqa: E402
from emalab.signals import ema_crossover  # noqa: E402

DATA, RESULTS = pathlib.Path("data"), pathlib.Path("results")
START = "2005-01-03"
COSTS = {"no cost": 0.0, "0.05% per trade": 0.0005, "0.20% per trade": 0.002}
MAIN_COST = "0.05% per trade"
ERAS = {"2005 to 2009": ("2005", "2009"), "2010 to 2019": ("2010", "2019"), "2020 to now": ("2020", "2100")}


def membership_mask(days: pd.DatetimeIndex, tickers: list[str], info: dict) -> pd.DataFrame:
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


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    info = json.loads((DATA / "download.json").read_text())
    prices = pd.read_parquet(DATA / "prices.parquet")
    prices["date"] = pd.to_datetime(prices["date"])
    opens = prices.pivot(index="date", columns="ticker", values="open").sort_index()
    closes = prices.pivot(index="date", columns="ticker", values="close").sort_index()
    spy = closes.pop("SPY")
    opens.pop("SPY")
    tickers = list(closes.columns)
    days = closes.index[closes.index >= START]
    member = membership_mask(closes.index, tickers, info).loc[days]

    out = {"data": {k: info[k] for k in ("symbols_wanted", "symbols_found", "first_day", "last_day", "has_membership_history")},
           "stocks_tested": 0, "by_cost": {}}
    out["data"]["symbols_missing"] = len(info["missing"])

    for label, cost in COSTS.items():
        strat = pd.DataFrame(np.nan, index=days, columns=tickers)
        hold = pd.DataFrame(np.nan, index=days, columns=tickers)
        per_stock, all_trades = [], []
        for t in tickers:
            c, o = closes[t].dropna(), opens[t].dropna()
            if len(c) < 400:
                continue
            o = o.reindex(c.index).fillna(c)
            table = strategy_returns(o, c, ema_crossover(c), cost)
            inside = member[t].reindex(table.index).fillna(False) & (table.index >= START)
            if inside.sum() < 252:
                continue
            strat.loc[table.index[inside], t] = table.loc[inside, "strategy"]
            hold.loc[table.index[inside], t] = table.loc[inside, "hold"]
            s, h = summarize(table.loc[inside, "strategy"]), summarize(table.loc[inside, "hold"])
            log = trades(table, o, cost)
            log = log[log["bought"].map(lambda d: bool(inside.get(d, False)))] if len(log) else log
            if len(log):
                all_trades.append(log.assign(ticker=t))
            per_stock.append({"ticker": t, "years": round(inside.sum() / 252, 1), "strategy_yearly": s.yearly_return, "hold_yearly": h.yearly_return,
                              "strategy_worst_drop": s.worst_drop, "hold_worst_drop": h.worst_drop,
                              "share_of_days_invested": float(table.loc[inside, "held"].mean()), "trades": len(log)})
        stocks = pd.DataFrame(per_stock)
        log = pd.concat(all_trades, ignore_index=True)

        # The portfolio: every member gets an equal slice each day.
        port_s, port_h = strat.mean(axis=1), hold.mean(axis=1)
        spy_daily = spy.pct_change().reindex(days).fillna(0)
        block = {
            "per_stock": {
                "stocks": len(stocks),
                "share_where_strategy_beat_holding": float((stocks["strategy_yearly"] > stocks["hold_yearly"]).mean()),
                "median_yearly_return": {"strategy": float(stocks["strategy_yearly"].median()), "hold": float(stocks["hold_yearly"].median())},
                "median_worst_drop": {"strategy": float(stocks["strategy_worst_drop"].median()), "hold": float(stocks["hold_worst_drop"].median())},
                "median_share_of_days_invested": float(stocks["share_of_days_invested"].median()),
            },
            "trades": {
                "count": len(log), "share_profitable": float((log["result"] > 0).mean()),
                "average_result": float(log["result"].mean()), "median_result": float(log["result"].median()),
                "average_winner": float(log.loc[log["result"] > 0, "result"].mean()), "average_loser": float(log.loc[log["result"] <= 0, "result"].mean()),
                "median_days_held": float(log["days"].median()),
            },
            "portfolio": {"strategy": summarize(port_s).as_dict(), "hold_all_members": summarize(port_h).as_dict(), "spy": summarize(spy_daily).as_dict()},
            "portfolio_by_era": {name: {"strategy": summarize(port_s.loc[a:b]).as_dict(), "hold_all_members": summarize(port_h.loc[a:b]).as_dict(), "spy": summarize(spy_daily.loc[a:b]).as_dict()}
                                 for name, (a, b) in ERAS.items()},
        }
        if label == MAIN_COST:
            yearly = pd.DataFrame({"strategy": (1 + port_s).groupby(port_s.index.year).prod() - 1,
                                   "hold_all_members": (1 + port_h).groupby(port_h.index.year).prod() - 1,
                                   "spy": (1 + spy_daily).groupby(spy_daily.index.year).prod() - 1})
            block["portfolio_by_year"] = {int(y): {k: round(float(v), 4) for k, v in row.items()} for y, row in yearly.iterrows()}
            out["stocks_tested"] = len(stocks)
            stocks.to_csv(RESULTS / "baseline_per_stock.csv", index=False)
            log.to_csv(RESULTS / "baseline_trades.csv", index=False)
            pd.DataFrame({"strategy": (1 + port_s).cumprod(), "hold_all_members": (1 + port_h).cumprod(), "spy": (1 + spy_daily).cumprod()}).to_csv(RESULTS / "baseline_growth.csv")
        out["by_cost"][label] = block
        p = block["portfolio"]
        print(f"[{label}] strategy {p['strategy']['yearly_return']:.1%}/yr, worst drop {p['strategy']['worst_drop']:.0%} | "
              f"hold {p['hold_all_members']['yearly_return']:.1%}/yr, worst drop {p['hold_all_members']['worst_drop']:.0%} | "
              f"SPY {p['spy']['yearly_return']:.1%}/yr, worst drop {p['spy']['worst_drop']:.0%}", flush=True)

    (RESULTS / "baseline.json").write_text(json.dumps(out, indent=1))
    print("saved results/baseline.json")


if __name__ == "__main__":
    main()
