# EMA crossover, tested properly

A tool for answering one question honestly: if you had followed a trading
signal, what would have happened?

It starts with the golden cross, where a stock's 50 day average price moves
above its 200 day average. The first version of this project reported strong
results for that signal. Those results did not survive a careful check.
[REWORK.md](REWORK.md) explains what went wrong, and the original work is kept
in [`original/`](original).

## First result: the plain crossover, no model

Tested on 590 stocks from January 2005 to November 2026, on the days each was
in the S&P 500, with a cost of 0.05 percent per trade.

| | Yearly return | Worst drop | Yearly swing |
| --- | --- | --- | --- |
| Crossover, equal slice per member | 7.6% | 26% | 10% |
| Holding the same stocks | 13.5% | 57% | 21% |
| Holding the index fund SPY | 10.7% | 55% | 19% |

What that says:

* **It made money, and less than holding.** Following the crossover beat
  holding the same stock for only 19 percent of stocks.
* **It cut the worst losses by more than half.** In 2008 it lost 12 percent
  while the same stocks lost 35 percent. It is out of the market about a
  third of the time, and those tend to be the bad stretches.
* **The price of that safety is missing rebounds.** In 2009 holding gained
  47 percent and the crossover 14. In 2020 it was 24 against roughly zero.
* **Most trades lose.** Of 5,664 trades, 38 percent were profitable. The
  average winner gained 55 percent and the average loser lost 10, so a few
  long trends carry the result.
* **It behaves a lot like holding about half as much stock.** Putting 56
  percent in the same stocks and the rest in cash would have earned the same
  7.6 percent with a similar worst drop. On this evidence the crossover is a
  way to take less risk, not a way to beat the market.

Two limits to keep in mind. Price history was available for 613 of the 990
companies that were in the index over these years. Most of the missing ones
were bought out or failed, so both columns are likely too rosy. And cash
earns nothing in this test, which understates the crossover a little.

Full numbers are in [`results/baseline.json`](results/baseline.json).

## The rules of the test

* A decision made at today's close is traded at tomorrow's open.
* Every buy and every sell has a cost.
* A stock is only tested on the days it was in the S&P 500, including
  companies that later left the index.
* Every result is shown beside simply holding the same stocks, and beside
  holding the index fund.

## Run it

```
pip install -e .
python scripts/download.py    # daily prices, free, into data/
python scripts/baseline.py    # the plain crossover with no model
pytest                        # checks that nothing can see the future
```

## Layout

| Path | What it is |
| --- | --- |
| `src/emalab/signals.py` | Rules that say when to be in a stock |
| `src/emalab/backtest.py` | Works out what following a rule would have returned |
| `scripts/` | Download the data and run a test |
| `results/` | Output of the latest run |
| `original/` | The first version, untouched |
