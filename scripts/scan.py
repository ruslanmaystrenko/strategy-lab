"""The scanner: what the signals say today, with their track record beside them.

python scripts/scan.py             uses the prices already downloaded
python scripts/scan.py --refresh   downloads fresh prices first (about 3 minutes)

It writes scanner/latest.html. It only reports. It never trades.
"""
import html
import json
import pathlib
import subprocess
import sys

import pandas as pd

sys.path.insert(0, "src")
from emalab.signals import ema  # noqa: E402
from emalab.universe import load_prices, membership  # noqa: E402

if "--refresh" in sys.argv:
    subprocess.run([sys.executable, "scripts/download.py"], check=False)

wide, spy, info = load_prices()
closes = wide["close"]
today = closes.index[-1]
members = membership(closes.index, list(closes.columns), info).iloc[-1]
closes = closes.loc[:, members & closes.iloc[-1].notna()]

# The market as a whole
spy_gap = spy.iloc[-1] / spy.rolling(200).mean().iloc[-1] - 1
above = ema(closes, 50) > ema(closes, 200)
breadth = above.iloc[-1].mean()

# Each stock's own record with the golden cross, from the baseline test
past = pd.read_csv("results/baseline_trades.csv").groupby("ticker")["result"].agg(trades="count", won=lambda r: (r > 0).sum(), average="mean")

def record(ticker):
    if ticker not in past.index:
        return "no earlier trades"
    r = past.loc[ticker]
    return f"{int(r.won)} of {int(r.trades)} earlier trades made money, average {r.average:+.0%}"

# Crosses in the last 10 trading days
recent = above.iloc[-11:]
flips = recent.astype(int).diff().iloc[1:]
crosses = [(day, ticker, "up" if change > 0 else "down") for ticker in flips for day, change in flips[ticker].items() if change != 0]
crosses.sort(reverse=True)

# Momentum leaders: return over the past year, skipping the latest month
momentum = (closes.iloc[-22] / closes.iloc[-253] - 1).dropna().sort_values(ascending=False)

tests = json.loads(pathlib.Path("results/strategies_final.json").read_text())
def tested(name):
    dev, final = tests["development 2005 to 2021"][name], tests["final test 2022 to today"][name]
    return f"{dev['yearly_return']:.0%} a year through 2021, {final['yearly_return']:.0%} since. Worst drop {min(dev['worst_drop'], final['worst_drop']):.0%}."

def rows(items):
    return "".join("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>" for row in items) or '<tr><td colspan="4" class="quiet">None</td></tr>'

ups = [(t, f"{d:%b %d}", f"{closes[t].iloc[-1]:,.2f}", record(t)) for d, t, way in crosses if way == "up"]
downs = [(t, f"{d:%b %d}", f"{closes[t].iloc[-1]:,.2f}", record(t)) for d, t, way in crosses if way == "down"]
leaders = [(t, f"{r:+.0%}", f"{closes[t].iloc[-1]:,.2f}", "in a golden cross" if above[t].iloc[-1] else "not in a golden cross") for t, r in momentum.head(15).items()]
hold = tested("Hold everything")

page = f"""<!doctype html><meta charset="utf-8"><title>Scanner {today:%Y %m %d}</title>
<style>
body {{ background:#000; color:#f2f2f0; font:15px/1.55 system-ui, "Segoe UI", sans-serif; max-width:980px; margin:0 auto; padding:36px 20px 60px; }}
h1 {{ font-size:30px; margin:0 0 4px; letter-spacing:-0.5px; }} h2 {{ font-size:19px; margin:38px 0 4px; }}
.quiet {{ color:#8d8d90; }} .jade {{ color:#5fd0a0; }} p {{ margin:4px 0 12px; max-width:70ch; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin:22px 0 6px; }}
.tile {{ border:1px solid #222224; border-radius:10px; padding:14px 16px; }} .tile b {{ display:block; font-size:24px; }}
table {{ border-collapse:collapse; width:100%; font-variant-numeric:tabular-nums; }}
td, th {{ text-align:left; padding:7px 14px 7px 0; border-bottom:1px solid #222224; }} th {{ color:#8d8d90; font-weight:500; font-size:13px; }}
td:first-child {{ font-weight:600; }}
</style>
<h1>Scanner</h1>
<p class="quiet">Prices through {today:%B %d, %Y}. {closes.shape[1]} S&amp;P 500 stocks. This page reports signals and their history. It does not place trades.</p>
<div class="tiles">
<div class="tile"><span class="quiet">Market trend</span><b class="{'jade' if spy_gap > 0 else ''}">{'Up' if spy_gap > 0 else 'Down'}</b>SPY is {abs(spy_gap):.1%} {'above' if spy_gap > 0 else 'below'} its 200 day average</div>
<div class="tile"><span class="quiet">Stocks in a golden cross</span><b>{breadth:.0%}</b>of the index has its 50 day average above its 200 day</div>
<div class="tile"><span class="quiet">New in the last 10 days</span><b>{len(ups)} up, {len(downs)} down</b>crosses among index members</div>
</div>
<h2>New golden crosses</h2>
<p class="quiet">Tested result: {tested("Golden cross")} Holding everything: {hold} The cross lowers risk. It has not beaten holding.</p>
<table><tr><th>Stock</th><th>Crossed</th><th>Last close</th><th>This stock's record with the signal</th></tr>{rows(ups)}</table>
<h2>Crosses back down</h2>
<p class="quiet">The 50 day average fell below the 200 day. In the test this is where the strategy stepped out.</p>
<table><tr><th>Stock</th><th>Crossed</th><th>Last close</th><th>This stock's record with the signal</th></tr>{rows(downs)}</table>
<h2>Momentum leaders</h2>
<p class="quiet">Largest gains over the past year, skipping the latest month. Tested result for holding the top fifth: {tested("Momentum")} It trailed holding through 2021 and led after.</p>
<table><tr><th>Stock</th><th>Past year</th><th>Last close</th><th>Trend</th></tr>{rows(leaders)}</table>
<h2>How to read this</h2>
<p class="quiet">Every number beside a signal comes from the backtests in this project: trades at the next open, costs included, each stock counted only while it was in the index. No strategy tested here beat holding in both periods. Price history is missing for about a third of past index members, mostly ones that failed, so the tested returns are likely too high.</p>
"""
pathlib.Path("scanner").mkdir(exist_ok=True)
pathlib.Path("scanner/latest.html").write_text(page, encoding="utf-8")
print(f"scanner/latest.html written for {today:%Y-%m-%d}: {len(ups)} new golden crosses, {len(downs)} crosses down, market trend {'up' if spy_gap > 0 else 'down'}")
