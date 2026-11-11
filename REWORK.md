# Why this project was reworked

The first version of this project is kept in `original/`, exactly as it was:
four notebooks, a report and a slide deck. It trained a model to tell good
golden crosses from bad ones and reported strong results, including a
backtest that turned 10,000 dollars into about 28,450.

Reading it back carefully, those results do not hold up. This page says why,
in plain terms. The rest of the repo is the version that fixes each problem.

## What went wrong

**1. The model was handed the answer.**
A crossover was labeled good if the stock rose more than 3 percent in the next
10 days, or if MACD was above its signal line and RSI was above 50. MACD, the
signal line and RSI were also inputs to the model. So the model mostly
relearned a rule that was written into its own labels. That is why precision
on the good class came out near 1.00, and why MACD and RSI topped the feature
importance chart.

**2. Training used the future.**
The data was split into training and test rows at random. Crossovers from
2024 helped predict crossovers from 2012, and the same market day showed up
on both sides through different stocks. A real trader only ever has the past.

**3. The backtest traded on the true label, not the model's prediction.**
The buy rule checked the real label, and the real label contains the next 10
days of returns. The backtest was a strategy that already knew what happened
next.

**4. Even so, it lost to doing nothing.**
The backtest shown was Apple, with a gain of 184 percent. Simply holding
Apple over the same years returned several times that.

**5. Only the survivors were tested.**
The stock list was the S&P 500 as it stands today, applied back to 2010.
Every company that failed, shrank or was bought along the way was left out,
which makes any strategy look better than it was.

**6. Raw prices were used as inputs.**
Values like the 10 day average price were fed in directly, so a 30 dollar
stock and a 300 dollar stock looked like different things to the model.

## What the rework does about each one

| Problem | Fix |
| --- | --- |
| Labels contain the inputs | Labels come from future returns only |
| Random split across time | Train on early years, test on later years the model never saw |
| Backtest reads the label | Decisions use only prices up to that day's close, and trade at the next open |
| No comparison | Every result is shown beside holding the stock and holding the index |
| Survivors only | Stocks are tested only on the days they were in the index, using a public record of past members |
| Raw prices | Inputs are ratios and percentages |

Trading costs are included everywhere.

## What stays

The idea is still the same one: a golden cross is a common signal, and it is
worth knowing when it has worked and when it has not. The original work is the
reason this version exists.
