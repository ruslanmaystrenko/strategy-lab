"""Run every strategy in PLAN.md through the same test.

python scripts/strategies.py           development years only, 2005 to 2021
python scripts/strategies.py --final   adds the final test, 2022 to today. Run once.
"""
import json
import pathlib
import sys

import pandas as pd

sys.path.insert(0, "src")
from emalab.backtest import summarize  # noqa: E402
from emalab.portfolio import portfolio_returns  # noqa: E402
from emalab.strategies import STRATEGIES  # noqa: E402
from emalab.universe import START, load_prices, membership  # noqa: E402

DEV_END, FINAL_START = "2021-12-31", "2022-01-01"
final = "--final" in sys.argv

wide, spy, info = load_prices()
opens, closes = wide["open"].fillna(wide["close"]), wide["close"]
member = membership(closes.index, list(closes.columns), info) & closes.notna()
if not final:   # the final years are cut off before any strategy sees them
    opens, closes, member, spy = (x.loc[:DEV_END] for x in (opens, closes, member, spy))

daily = pd.DataFrame({name: portfolio_returns(opens, closes, rule(closes, member, spy)) for name, rule in STRATEGIES.items()})
daily["SPY"] = spy.pct_change().reindex(daily.index).fillna(0)
daily = daily.loc[START:]

periods = {"development 2005 to 2021": daily.loc[:DEV_END]}
if final:
    periods["final test 2022 to today"] = daily.loc[FINAL_START:]
report = {}
for period, part in periods.items():
    table = pd.DataFrame({name: summarize(part[name]).as_dict() for name in part}).T
    table["return_per_unit_of_swing"] = (table["yearly_return"] / table["yearly_swing"]).round(2)
    report[period] = table.drop(columns=["days", "total_return"]).to_dict("index")
    print(f"\n{period}\n{table[['yearly_return', 'worst_drop', 'yearly_swing', 'return_per_unit_of_swing']].to_string()}")

tag = "final" if final else "dev"
pathlib.Path(f"results/strategies_{tag}.json").write_text(json.dumps(report, indent=1))
daily.to_csv(f"results/strategies_{tag}_daily.csv")
