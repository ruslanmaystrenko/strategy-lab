"""The scanner as an app.  Start it with:  streamlit run app.py   (or double click Scanner.bat)

Three views: how every tested strategy has done, one stock with its crossovers marked, and today's signals across the index.
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
GOLD, VIOLET, SKY, CORAL = "#e3b341", "#b392f0", "#79c0ff", "#ff7b72"
# One clear color per strategy. None of them is green, so no line looks like the winner before you read the numbers.
COLORS = {"Hold everything": WHITE, "Golden cross": GOLD, "Momentum": VIOLET, "Market trend filter": CORAL, "Dip buying": SKY, "SPY": GREY}
RULES = {"Hold everything": "Own every stock in the index, equally.", "Golden cross": "Own a stock only while its 50 day average is above its 200 day average.",
         "Momentum": "Own the fifth of stocks that rose most over the past year. Reshuffled once a month.", "Market trend filter": "Own everything while the index is above its 200 day average, otherwise sit in cash. Checked once a month.",
         "Dip buying": "Buy stocks in an uptrend that just fell sharply. Sell on the bounce, or after ten days.", "SPY": "The S&P 500 fund, for reference."}
st.set_page_config(page_title="Strategy Lab", layout="wide")


@st.cache_data(show_spinner="Loading prices")
def load():
    wide, spy, info = load_prices()
    members = membership(wide["close"].index, list(wide["close"].columns), info).iloc[-1]
    keep = members & wide["close"].iloc[-1].notna()
    return wide["open"].loc[:, keep], wide["close"].loc[:, keep], spy


def chart(fig, height=460, log=False):
    # Clicking a name in the legend hides or shows that line. Double clicking is switched off because it could blank the chart.
    fig.update_layout(template="plotly_dark", paper_bgcolor="black", plot_bgcolor="black", height=height, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.08, itemdoubleclick=False), hovermode="x unified", yaxis_type="log" if log else "linear")
    fig.update_xaxes(gridcolor="#1c1c1e"); fig.update_yaxes(gridcolor="#1c1c1e")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def dot(color):
    return f"<span style='color:{color}'>&#9679;</span>"


opens, closes, spy = load()
today = closes.index[-1]
above = ema(closes, 50) > ema(closes, 200)
flips = above.astype(int).diff().iloc[-10:]

with st.sidebar:
    st.title("Strategy Lab")
    st.caption(f"Prices through {today:%B %d, %Y}")
    if st.button("Download fresh prices", help="Takes about three minutes"):
        with st.spinner("Downloading"):
            subprocess.run([sys.executable, "scripts/download.py"], check=False)
        st.cache_data.clear()
        st.rerun()
    st.caption("This app reports signals and their tested history. It does not place trades.")
    st.caption("On any chart: click a name to hide or show its line, drag to zoom, double click the chart to zoom back out.")

# ---- the market right now
spy_gap = spy.iloc[-1] / spy.rolling(200).mean().iloc[-1] - 1
a, b, c, d = st.columns(4)
a.metric("Market trend", "Up" if spy_gap > 0 else "Down", f"{spy_gap:+.1%} SPY vs its 200 day average")
b.metric("Index in a golden cross", f"{above.iloc[-1].mean():.0%}")
c.metric("New golden crosses, 10 days", int((flips == 1).sum().sum()))
d.metric("Crosses back down, 10 days", int((flips == -1).sum().sum()))

strategies, one_stock, signals = st.tabs(["How the strategies did", "One stock", "Today's signals"])

# ---- how every tested strategy has done
with strategies:
    st.markdown("Five strategies, each trading **the whole S&P 500 as one portfolio** that starts with $1, ranked by total return. "
                "These results cover every stock in the index, so they do not change with the stock picked on the One stock tab.")
    report = json.load(open("results/strategies_final.json"))
    daily = pd.read_csv("results/strategies_final_daily.csv", index_col=0, parse_dates=True)
    period = st.radio("Years", ["All years, 2005 to today", "Development, 2005 to 2021", "Final test, 2022 to today"], horizontal=True)
    st.caption("The rules were chosen using 2005 to 2021 only. The years from 2022 were held back and looked at once, as the real test.")
    part = {"All": daily, "Dev": daily.loc[:"2021"], "Fin": daily.loc["2022":]}[period[:3]]
    stats = {name: summarize(part[name]) for name in part}
    rows = "".join(
        f"<tr><td>{dot(COLORS[name])}&nbsp; <b>{name}</b><br><span style='color:{GREY};font-size:13px'>{RULES[name]}</span></td>"
        f"<td style='font-size:26px'>{s.total_return:+,.0%}</td><td>${1 + s.total_return:,.2f}</td><td>{s.yearly_return:.1%}</td><td>{s.worst_drop:.0%}</td></tr>"
        for name, s in sorted(stats.items(), key=lambda item: -item[1].total_return))
    st.markdown("<style>.ranks{width:100%;border-collapse:collapse} .ranks td,.ranks th{padding:10px 14px;border-bottom:1px solid #232527;text-align:right;vertical-align:middle;border-left:0;border-right:0}"
                ".ranks td:first-child,.ranks th:first-child{text-align:left} .ranks th{color:#8d8d90;font-weight:400;font-size:13px}</style>"
                f"<table class='ranks'><tr><th>Strategy</th><th>Total return</th><th>$1 became</th><th>Per year</th><th>Worst drop</th></tr>{rows}</table>", unsafe_allow_html=True)

    st.subheader("Growth of $1")
    fig = go.Figure()
    for name in part:
        fig.add_scatter(x=part.index, y=(1 + part[name]).cumprod(), name=name, line=dict(color=COLORS[name], width=1.6, dash="dot" if name == "SPY" else "solid"),
                        hovertemplate="$%{y:.2f}")
    fig.update_yaxes(tickprefix="$", dtick="D2")
    chart(fig, log=True)

    st.subheader("How deep the losses got")
    st.caption("This chart shows how far each strategy was below its own best value so far. 0% means it is at a new high. "
               "A reading of 30% down means a person following it had lost 30% from their peak at that moment. Shallow, short dips are easier to live with than deep, long ones.")
    fig = go.Figure()
    for name in part:
        value = (1 + part[name]).cumprod()
        fig.add_scatter(x=part.index, y=value / value.cummax() - 1, name=name, line=dict(color=COLORS[name], width=1.2, dash="dot" if name == "SPY" else "solid"),
                        hovertemplate="%{y:.0%}")
    fig.update_yaxes(tickformat=".0%")
    chart(fig, height=320)
    st.markdown("**What the tests found.** The strategy that looked best through 2021, the market trend filter, did poorly on the years held back for the final test. "
                "Momentum trailed holding through 2021 and led after. Nothing beat simply holding in both periods. "
                "Price history is missing for about a third of past index members, mostly ones that failed, so these returns are likely too high.")

# ---- one stock, with its crossovers marked
with one_stock:
    st.markdown("The golden cross strategy on a single stock: buy when the 50 day average rises above the 200 day average, sell when it falls back below.")
    pick, span = st.columns([1, 2])
    ticker = pick.selectbox("Stock", sorted(closes.columns), index=sorted(closes.columns).index("AAPL") if "AAPL" in closes else 0)
    years = span.select_slider("Years shown", [1, 2, 3, 5, 10, 20], value=5)
    close, open_ = closes[ticker].dropna(), opens[ticker].reindex(closes[ticker].dropna().index).fillna(closes[ticker])
    table = strategy_returns(open_, close, ema_crossover(close))
    start = today - pd.DateOffset(years=years)
    view, log = table.loc[start:], trades(table, open_)
    shown = log[log["sold"] >= start] if len(log) else log
    mine, hold = summarize(view["strategy"]), summarize(view["hold"])
    span_words = f"past {years} years" if years > 1 else "past year"

    k = st.columns(5)
    k[0].metric(f"Return following the cross, {span_words}", f"{mine.total_return:+.0%}", f"{(mine.total_return - hold.total_return) * 100:+.0f} points vs holding")
    k[1].metric(f"Return holding {ticker}, {span_words}", f"{hold.total_return:+.0%}")
    k[2].metric("Worst drop following the cross", f"{mine.worst_drop:.0%}")
    k[2].caption(f"Holding: {hold.worst_drop:.0%}")
    k[3].metric("Trades that made money", f"{(shown['result'] > 0).sum()} of {len(shown)}" if len(shown) else "none")
    k[4].metric("Right now", "In a golden cross" if above[ticker].iloc[-1] else "Out")

    st.markdown(f"<span style='color:{JADE}'>&#9650;</span> bought &nbsp; <span style='color:{RED}'>&#9660;</span> sold &nbsp;&nbsp; "
                f"<span style='background:{JADE}33;padding:1px 8px'>green band</span> the strategy owned the stock and that trade made money &nbsp; "
                f"<span style='background:{RED}33;padding:1px 8px'>red band</span> it owned the stock and that trade lost money &nbsp; "
                "no band: it was out of the stock", unsafe_allow_html=True)
    fig = go.Figure()
    for _, t in shown.iterrows():   # shade the stretches where the strategy held the stock
        fig.add_vrect(x0=max(t["bought"], start), x1=t["sold"], fillcolor=JADE if t["result"] > 0 else RED, opacity=0.12, line_width=0)
    if table["held"].iloc[-1]:
        fig.add_vrect(x0=max(table.index[table["entered"]][-1], start), x1=today, fillcolor=JADE, opacity=0.12, line_width=0)
    fig.add_scatter(x=view.index, y=close.loc[start:], name=ticker, line=dict(color=WHITE, width=1.4))
    fig.add_scatter(x=view.index, y=ema(close, 50).loc[start:], name="50 day average", line=dict(color=GOLD, width=1.2))
    fig.add_scatter(x=view.index, y=ema(close, 200).loc[start:], name="200 day average", line=dict(color=SKY, width=1.2))
    ups, downs = view.index[view["entered"]], view.index[view["left"]]
    fig.add_scatter(x=ups, y=open_.loc[ups], mode="markers", name="Bought", marker=dict(symbol="triangle-up", size=13, color=JADE))
    fig.add_scatter(x=downs, y=open_.loc[downs], mode="markers", name="Sold", marker=dict(symbol="triangle-down", size=13, color=RED))
    fig.update_yaxes(tickprefix="$")
    chart(fig)

    st.subheader(f"Growth of $1 over the {span_words}")
    growth = (1 + view[["strategy", "hold"]]).cumprod()
    fig = go.Figure()
    fig.add_scatter(x=growth.index, y=growth["hold"], name=f"Holding {ticker}", line=dict(color=WHITE, width=1.4), hovertemplate="$%{y:.2f}")
    fig.add_scatter(x=growth.index, y=growth["strategy"], name="Following the cross", line=dict(color=GOLD, width=1.6), hovertemplate="$%{y:.2f}")
    fig.update_yaxes(tickprefix="$")
    chart(fig, height=260)
    st.caption("The gold line goes flat whenever the strategy is out of the stock.")
    if len(shown):
        st.subheader("Each trade")
        st.dataframe(shown.assign(result=shown["result"].map("{:+.1%}".format), bought=shown["bought"].dt.date, sold=shown["sold"].dt.date)[::-1], hide_index=True, width="stretch")

# ---- today's signals across the index
with signals:
    past = pd.read_csv("results/baseline_trades.csv").groupby("ticker")["result"].agg(trades="count", won=lambda r: (r > 0).sum(), average="mean")

    def listing(direction):
        rows = [{"Stock": t, "Crossed": day.date(), "Last close": round(closes[t].iloc[-1], 2),
                 "Earlier trades": int(past.trades.get(t, 0)), "Made money": int(past.won.get(t, 0)), "Average result": f"{past.average.get(t, 0):+.0%}"}
                for t in flips for day, change in flips[t].items() if change == direction]
        return pd.DataFrame(rows).sort_values("Crossed", ascending=False) if rows else pd.DataFrame()

    left, right = st.columns(2)
    left.subheader("New golden crosses"); left.dataframe(listing(1), hide_index=True, width="stretch")
    right.subheader("Crosses back down"); right.dataframe(listing(-1), hide_index=True, width="stretch")
    st.subheader("Momentum leaders")
    leaders = (closes.iloc[-22] / closes.iloc[-253] - 1).dropna().nlargest(20)
    st.dataframe(pd.DataFrame({"Stock": leaders.index, "Past year": leaders.map("{:+.0%}".format).values, "Last close": closes.iloc[-1][leaders.index].round(2).values,
                               "In a golden cross": above.iloc[-1][leaders.index].map({True: "Yes", False: "No"}).values}), hide_index=True, width="stretch")
    st.caption("Past year means the return over the last twelve months, skipping the latest month. Pick any of these on the One stock tab to see its chart.")
