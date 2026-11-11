"""The scanner as an app.  Start it with:  streamlit run app.py   (or double click Scanner.bat)

Three views: one stock with its crossovers marked, today's signals across the index, and how every tested strategy has done.
It reads the prices in data/ and the test results in results/. It only reports. It never trades.
"""
import json
import subprocess
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, "src")
from emalab.backtest import strategy_returns, summarize, trades  # noqa: E402
from emalab.signals import ema, ema_crossover  # noqa: E402
from emalab.universe import load_prices, membership  # noqa: E402

WHITE, SILVER, GREY, JADE, RED = "#f2f2f0", "#d4d6da", "#8d8d90", "#5fd0a0", "#e0787a"
st.set_page_config(page_title="Strategy Lab", layout="wide")


@st.cache_data(show_spinner="Loading prices")
def load():
    wide, spy, info = load_prices()
    members = membership(wide["close"].index, list(wide["close"].columns), info).iloc[-1]
    keep = members & wide["close"].iloc[-1].notna()
    return wide["open"].loc[:, keep], wide["close"].loc[:, keep], spy


def chart(fig, height=460, log=False):
    fig.update_layout(template="plotly_dark", paper_bgcolor="black", plot_bgcolor="black", height=height, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.08), hovermode="x unified", yaxis_type="log" if log else "linear")
    fig.update_xaxes(gridcolor="#1c1c1e"); fig.update_yaxes(gridcolor="#1c1c1e")
    st.plotly_chart(fig, use_container_width=True)


opens, closes, spy = load()
today = closes.index[-1]
above = ema(closes, 50) > ema(closes, 200)
flips = above.astype(int).diff().iloc[-10:]

with st.sidebar:
    st.title("Strategy Lab")
    st.caption(f"Prices through {today:%B %d, %Y}")
    ticker = st.selectbox("Stock", sorted(closes.columns), index=sorted(closes.columns).index("AAPL") if "AAPL" in closes else 0)
    years = st.select_slider("Years shown", [1, 2, 3, 5, 10, 20], value=5)
    if st.button("Download fresh prices", help="Takes about three minutes"):
        with st.spinner("Downloading"):
            subprocess.run([sys.executable, "scripts/download.py"], check=False)
        st.cache_data.clear()
        st.rerun()
    st.caption("This app reports signals and their tested history. It does not place trades.")

# ---- the market right now
spy_gap = spy.iloc[-1] / spy.rolling(200).mean().iloc[-1] - 1
a, b, c, d = st.columns(4)
a.metric("Market trend", "Up" if spy_gap > 0 else "Down", f"{spy_gap:+.1%} SPY vs its 200 day average")
b.metric("Index in a golden cross", f"{above.iloc[-1].mean():.0%}")
c.metric("New golden crosses, 10 days", int((flips == 1).sum().sum()))
d.metric("Crosses back down, 10 days", int((flips == -1).sum().sum()))

one_stock, signals, strategies = st.tabs(["One stock", "Today's signals", "How the strategies did"])

# ---- one stock, with its crossovers marked
with one_stock:
    close, open_ = closes[ticker].dropna(), opens[ticker].reindex(closes[ticker].dropna().index).fillna(closes[ticker])
    table = strategy_returns(open_, close, ema_crossover(close))
    start = today - pd.DateOffset(years=years)
    view, log = table.loc[start:], trades(table, open_)
    shown = log[log["sold"] >= start] if len(log) else log
    mine, hold = summarize(view["strategy"]), summarize(view["hold"])

    k = st.columns(5)
    k[0].metric("Following the cross", f"{mine.total_return:+.0%}", f"{(mine.total_return - hold.total_return) * 100:+.0f} points vs holding")
    k[1].metric("Holding the stock", f"{hold.total_return:+.0%}")
    k[2].metric("Worst drop, cross", f"{mine.worst_drop:.0%}")
    k[2].caption(f"Holding: {hold.worst_drop:.0%}")
    k[3].metric("Trades that made money", f"{(shown['result'] > 0).sum()} of {len(shown)}" if len(shown) else "none")
    k[4].metric("Right now", "In a golden cross" if above[ticker].iloc[-1] else "Out")

    fig = go.Figure()
    for _, t in shown.iterrows():   # shade the stretches where the strategy held the stock
        fig.add_vrect(x0=max(t["bought"], start), x1=t["sold"], fillcolor=JADE if t["result"] > 0 else RED, opacity=0.09, line_width=0)
    if table["held"].iloc[-1]:
        fig.add_vrect(x0=max(table.index[table["entered"]][-1], start), x1=today, fillcolor=JADE, opacity=0.09, line_width=0)
    fig.add_scatter(x=view.index, y=close.loc[start:], name=ticker, line=dict(color=WHITE, width=1.4))
    fig.add_scatter(x=view.index, y=ema(close, 50).loc[start:], name="50 day average", line=dict(color=JADE, width=1.2))
    fig.add_scatter(x=view.index, y=ema(close, 200).loc[start:], name="200 day average", line=dict(color=GREY, width=1.2))
    ups, downs = view.index[view["entered"]], view.index[view["left"]]
    fig.add_scatter(x=ups, y=open_.loc[ups], mode="markers", name="Buy", marker=dict(symbol="triangle-up", size=13, color=JADE))
    fig.add_scatter(x=downs, y=open_.loc[downs], mode="markers", name="Sell", marker=dict(symbol="triangle-down", size=13, color=RED))
    chart(fig)
    st.caption("Triangles mark where the strategy bought and sold, at the open after each cross. Green bands are trades that made money, red bands are trades that lost.")

    growth = (1 + view[["strategy", "hold"]]).cumprod()
    fig = go.Figure()
    fig.add_scatter(x=growth.index, y=growth["hold"], name="Holding", line=dict(color=SILVER, width=1.3))
    fig.add_scatter(x=growth.index, y=growth["strategy"], name="Following the cross", line=dict(color=JADE, width=1.6))
    chart(fig, height=260)
    if len(shown):
        st.dataframe(shown.assign(result=shown["result"].map("{:+.1%}".format), bought=shown["bought"].dt.date, sold=shown["sold"].dt.date)[::-1], hide_index=True, use_container_width=True)

# ---- today's signals across the index
with signals:
    past = pd.read_csv("results/baseline_trades.csv").groupby("ticker")["result"].agg(trades="count", won=lambda r: (r > 0).sum(), average="mean")

    def listing(direction):
        rows = [{"Stock": t, "Crossed": day.date(), "Last close": round(closes[t].iloc[-1], 2),
                 "Earlier trades": int(past.trades.get(t, 0)), "Made money": int(past.won.get(t, 0)), "Average result": f"{past.average.get(t, 0):+.0%}"}
                for t in flips for day, change in flips[t].items() if change == direction]
        return pd.DataFrame(rows).sort_values("Crossed", ascending=False) if rows else pd.DataFrame()

    left, right = st.columns(2)
    left.subheader("New golden crosses"); left.dataframe(listing(1), hide_index=True, use_container_width=True)
    right.subheader("Crosses back down"); right.dataframe(listing(-1), hide_index=True, use_container_width=True)
    st.subheader("Momentum leaders")
    leaders = (closes.iloc[-22] / closes.iloc[-253] - 1).dropna().nlargest(20)
    st.dataframe(pd.DataFrame({"Stock": leaders.index, "Past year": leaders.map("{:+.0%}".format).values, "Last close": closes.iloc[-1][leaders.index].round(2).values,
                               "In a golden cross": above.iloc[-1][leaders.index].map({True: "Yes", False: "No"}).values}), hide_index=True, use_container_width=True)
    st.caption("Past year means the return over the last twelve months, skipping the latest month. Pick any of these in the sidebar to see its chart.")

# ---- how every tested strategy has done
with strategies:
    report = json.load(open("results/strategies_final.json"))
    daily = pd.read_csv("results/strategies_final_daily.csv", index_col=0, parse_dates=True)
    period = st.radio("Period", ["Development, 2005 to 2021", "Final test, 2022 to today", "Everything"], horizontal=True, index=1)
    part = {"Dev": daily.loc[:"2021"], "Fin": daily.loc["2022":], "Eve": daily}[period[:3]]
    best = max((n for n in part if n != "SPY"), key=lambda n: summarize(part[n]).yearly_return)
    cols = st.columns(len(part.columns))
    for col, name in zip(cols, part):
        s = summarize(part[name])
        col.metric(name + (" (best)" if name == best else ""), f"{s.yearly_return:.1%}")
        col.caption(f"a year. Worst drop {s.worst_drop:.0%}")
    colors = {"Hold everything": SILVER, "Golden cross": "#6f7074", "Momentum": JADE, "Market trend filter": WHITE, "Dip buying": "#4a4b4f", "SPY": GREY}
    fig = go.Figure()
    for name in part:
        fig.add_scatter(x=part.index, y=(1 + part[name]).cumprod(), name=name, line=dict(color=colors[name], width=1.5, dash="dot" if name == "SPY" else "solid"))
    chart(fig, log=True)
    fig = go.Figure()
    for name in ["Hold everything", "Momentum", "Market trend filter", "Golden cross"]:
        value = (1 + part[name]).cumprod()
        fig.add_scatter(x=part.index, y=value / value.cummax() - 1, name=name, line=dict(color=colors[name], width=1.2))
    fig.update_yaxes(tickformat=".0%")
    chart(fig, height=280)
    st.caption("Top: growth of one dollar. Bottom: how far each strategy sat below its own peak.")
    st.markdown("**What the tests found.** The strategy that looked best through 2021, the market trend filter, did poorly on the years held back for the final test. "
                "Momentum trailed holding through 2021 and led after. Nothing beat simply holding in both periods. "
                "Price history is missing for about a third of past index members, mostly ones that failed, so these returns are likely too high.")
