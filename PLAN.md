# The test plan, written before the results

Trying many strategies and keeping the best one is the easiest way to fool
yourself. So the list, the settings and the scoring were fixed here first,
and this file was committed before any of these strategies were run.

## The strategies

Settings are the common textbook ones. None of them will be tuned.

| Name | Rule |
| --- | --- |
| Hold everything | Every S&P 500 member, equal slices. The yardstick. |
| Golden cross | Each member's slice is invested only while its 50 day average is above its 200 day average. |
| Momentum | At each month end, rank members by their return over the past year, skipping the latest month. Hold the top fifth, equal slices, until the next month end. |
| Market trend filter | Hold everything while SPY is above its 200 day average, checked at each month end. Otherwise hold cash. |
| Dip buying | Buy a member that is above its 200 day average when its 2 day RSI falls under 10. Sell when it closes above its 5 day average, or after 10 trading days. Up to 20 positions of 5 percent each. |

## The rules for all of them

* A decision made at a close is traded at the next open.
* Every trade costs 0.05 percent of its size.
* Only stocks in the index on that day can be held.
* Cash earns nothing.

## The two periods

* **Development: 2005 to the end of 2021.** Looked at first.
* **Final test: 2022 to today.** Run once, after everything above is fixed.
  Whatever it shows is the result that gets reported.

The golden cross had already been run over the whole period before this plan
was written, so its final test number is not a clean surprise. The other
three are.
