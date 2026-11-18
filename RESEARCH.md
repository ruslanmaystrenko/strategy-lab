# What the research says about predicting stock returns

Notes written in November 2026 to put this project's results in context. Figures were read from the sources listed at the end unless marked otherwise.

## What quant funds do

| Family | What it does | Typical hold |
| --- | --- | --- |
| Factor investing | Buy stocks sharing traits linked to higher returns: cheap, profitable, rising, low risk | Months to years |
| Trend following | Buy what is rising and sell what is falling, across stocks, bonds, currencies and commodities | Days to weeks |
| Statistical arbitrage | Bet that related securities that drifted apart will come back together | A day to weeks |
| Event driven | Trade the predictable moves around earnings, buybacks and analyst changes | Days to weeks |
| Systematic macro | Rules linking economic cycles to markets | A month or more |
| Risk parity | Balance risk across asset classes | Months to years |

Their edge comes from holding hundreds of small bets at once, trading cheaply, and being able to short. It does not come from one rule that says when to buy.

## Signals for single stocks exist, and they fade

* McLean and Pontiff (2016) studied 97 published predictors. Returns were 26 percent lower on new data and 58 percent lower after publication. Trading in those stocks rose after publication, which suggests investors learned the signal and traded it away.
* Chen and Velikov studied 120. After trading costs, the average published signal earned about nothing once it was public.
* Chen and Welch (a July 2026 working paper, not yet reviewed) studied about 200. The typical monthly return in large stocks fell from 0.48 percent before 2005 to 0.07 percent after. Profitability was the only category still clearly positive.
* Jensen, Kelly and Pedersen give a more positive reading: about 85 percent of 153 factors replicate with their method. They agree returns shrink by about a third on new data.

## Timing the whole market is harder

* Goyal, Welch and Zafirov (2024) rechecked 46 variables proposed to predict the market. Most fail on new data. A small number still work.
* Rapach, Ringgenberg and Zhou (2016) call total short interest "arguably the strongest known predictor" of market returns.
* A study of trend following across 67 markets from 1880 to 2016 found gains in eight of the ten worst stock and bond drawdowns. It was weak for several years after 2009.

## What this means here

The result of this project, that no simple rule beat holding, is what the research would predict. The golden cross and the other rules tested are public, price based and decades old.

## Sources

* [McLean and Pontiff, Does Academic Research Destroy Stock Return Predictability?](https://counterpointfunds.com/wp-content/uploads/2017/07/PredictabilityMcleanPontiff.pdf)
* [Chen and Velikov, Accounting for the Anomaly Zoo](https://jacobslevycenter.wharton.upenn.edu/wp-content/uploads/2019/09/Accounting-for-the-Anomaly-Zoo.pdf)
* [Chen and Welch, What Useful Alphas?](https://arxiv.org/pdf/2607.06502)
* [Jensen, Kelly and Pedersen, Is There a Replication Crisis in Finance?](https://nber.org/system/files/working_papers/w28432/w28432.pdf)
* [Goyal, Welch and Zafirov, A Comprehensive 2022 Look at Equity Premium Prediction](https://sfi.ch/en/publications/a-comprehensive-2022-look-at-the-empirical-performance-of-equity-premium-prediction)
* [Rapach, Ringgenberg and Zhou, Short Interest and Aggregate Stock Returns](https://ideas.repec.org/a/eee/jfinec/v121y2016i1p46-65.html)
* [Alpha Architect, Trend Following: The Historical Evidence](https://alphaarchitect.com/time-series-momentum-aka-trend-following-the-historical-evidence/)
* [Bloomberg, Your guide to the many flavors of quant investing](https://www.bloomberg.com/professional/blog/guide-many-flavors-quant-investing)
