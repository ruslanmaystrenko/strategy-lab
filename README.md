# Strategy Lab

A stock screener and a testing rig that answer one question honestly: if you had followed a trading rule, what would have happened?

It began as a project on the golden cross, the moment a stock's 50 day average price rises above its 200 day average. The first version reported strong results. Those results did not survive a careful check, so the project was rebuilt from the ground up. [REWORK.md](REWORK.md) explains what was wrong, and the original work is kept untouched in [`original/`](original).

## What it found

Five strategies, each trading the whole S&P 500 as one portfolio from January 2005 to November 2026.

| Strategy | Total return | $1 became | Per year | Worst drop |
| --- | --- | --- | --- | --- |
| Hold everything | +1,540% | $16.40 | 13.7% | 56% |
| Momentum | +1,433% | $15.33 | 13.3% | 54% |
| SPY, the index fund | +822% | $9.22 | 10.7% | 55% |
| Market trend filter | +766% | $8.66 | 10.4% | 25% |
| Golden cross | +399% | $4.99 | 7.6% | 26% |
| Dip buying | +202% | $3.02 | 5.2% | 40% |

* **Nothing beat simply holding every stock.** The rules that move in and out of the market dodge part of each crash and then miss the start of each recovery, which costs more.
* **The golden cross is a way to take less risk, not a way to earn more.** Its worst drop was 26 percent against 56 percent for holding, and it paid for that with a third of the return.
* **The winner on the early years lost on the later ones.** The rules were chosen using 2005 to 2021 only. The market trend filter looked best there, then fell behind on the years held back for the real test. Momentum did the opposite.

| Per year | 2005 to 2021 | 2022 to today |
| --- | --- | --- |
| Hold everything | 13.6% | 13.9% |
| Golden cross | 8.1% | 6.1% |
| Momentum | 11.4% | 20.3% |
| Market trend filter | 11.7% | 6.0% |
| Dip buying | 5.7% | 3.6% |
| SPY | 10.5% | 11.4% |

* **The original project's model added nothing.** Rebuilt without the leak described in REWORK.md, it could not tell good crossovers from bad ones. The trades it picked made money 37.5 percent of the time and the ones it skipped 37.0 percent.

This matches the published research, summarized in [RESEARCH.md](RESEARCH.md): trading signals that are public tend to fade.

## The screener

```
pip install -e .
python scripts/download.py
python -m streamlit run app.py
```

The download takes about three minutes and is free. On Windows, double click `Scanner.bat` to start the app. It opens in the browser.

**How the strategies did.** The table above with a chart of what $1 grew to, and a second chart of how far each strategy sat below its own peak. Switch between all years, the development years and the final test.

**One stock.** Pick any stock in the index. The chart marks each point where the golden cross bought and sold. A green band is a trade that made money, a red band is one that lost, and no band means the rule was out of the stock. Tiles above the chart compare following the rule with holding the stock.

**Today's signals.** Stocks that formed a golden cross in the last ten days, stocks that crossed back down, and the strongest stocks of the past year. Each new cross is shown with how that signal has done on that stock before.

On any chart, click a name to hide or show its line, drag to zoom, and double click to zoom back out.

The app reports only. It never places trades.

## How the tests are kept honest

* A decision made at today's close is traded at tomorrow's open.
* Every trade costs 0.05 percent, including the small trades that keep holdings at their target shares.
* A stock is tested only on the days it was in the S&P 500, including companies that later left.
* The strategies and their settings were written down in [PLAN.md](PLAN.md) before they were run.
* The years from 2022 were locked away and looked at once.
* Sixteen automated tests check that no rule can see the future.

## Limits

* Price history was available for 613 of the 990 companies that were in the index over these years. Most of the missing ones were bought out or failed, so every return above is likely too high.
* Cash earns nothing in these tests, which understates the strategies that hold cash.
* Every rule here uses price history alone. None looks at company finances or the economy.

## What is in the repo

| Path | What it is |
| --- | --- |
| `app.py` | The screener |
| `src/emalab/` | The signals, the strategies and the testing code |
| `scripts/` | Download prices and run each test |
| `notebooks/` | The three studies with charts: the plain crossover, the model test, the five strategies |
| `results/` | Output of the latest runs |
| `tests/` | The automated checks |
| `PLAN.md` | The test plan, written before the results |
| `REWORK.md` | What was wrong with the first version |
| `RESEARCH.md` | What published research says about predicting returns |
| `original/` | The first version, untouched |

## Data

Daily prices from Yahoo Finance through the `yfinance` package, downloaded to your own computer and not stored in this repo. Index membership history from [fja05680/sp500](https://github.com/fja05680/sp500).
