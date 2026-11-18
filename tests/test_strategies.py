import numpy as np
import pandas as pd
import pytest

from emalab.portfolio import portfolio_returns
from emalab.strategies import STRATEGIES


def market(stocks=30, n=1500, seed=5):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2004-01-01", periods=n)
    closes = pd.DataFrame(50 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, (n, stocks)), axis=0)), index=days, columns=[f"S{i}" for i in range(stocks)])
    opens = closes.shift(1).fillna(closes) * np.exp(rng.normal(0, 0.004, (n, stocks)))
    member = pd.DataFrame(True, index=days, columns=closes.columns)
    member.iloc[:, :5] = False   # five stocks are never in the index
    return opens, closes, member, closes.mean(axis=1)


def test_trades_at_the_next_open_and_pays_for_what_changed():
    days = pd.bdate_range("2020-01-01", periods=4)
    opens = pd.DataFrame({"A": [10, 10, 11, 12.0]}, index=days)
    closes = pd.DataFrame({"A": [10, 10, 12, 12.0]}, index=days)
    weights = pd.DataFrame({"A": [0, 1, 1, 1.0]}, index=days)          # decide to buy at the close of day 1
    out = portfolio_returns(opens, closes, weights, cost=0.01)
    assert out.iloc[1] == 0                                               # nothing on the day of the decision
    assert out.iloc[2] == pytest.approx(0.99 * 12 / 11 - 1)               # bought at day 2's open, minus the cost
    assert out.iloc[3] == pytest.approx(12 / 12 - 1)


def test_keeping_equal_shares_costs_money_when_prices_move_apart():
    days = pd.bdate_range("2020-01-01", periods=4)
    closes = pd.DataFrame({"A": [10, 10, 20, 20.0], "B": [10, 10, 10, 10.0]}, index=days)   # A doubles during day 2
    opens = closes.shift(1).fillna(closes)
    weights = pd.DataFrame(0.5, index=days, columns=["A", "B"])
    free = portfolio_returns(opens, closes, weights, cost=0)
    charged = portfolio_returns(opens, closes, weights, cost=0.01)
    assert charged.iloc[3] < free.iloc[3]                                 # day 3 opens two thirds in A and must sell back to half
    assert charged.iloc[3] == pytest.approx(-0.01 * 2 * (2 / 3 - 0.5))


@pytest.mark.parametrize("name", STRATEGIES)
def test_every_strategy_is_valid_and_cannot_see_the_future(name):
    opens, closes, member, spy = market()
    weights = STRATEGIES[name](closes, member, spy)
    assert (weights >= 0).all().all() and (weights.sum(axis=1) <= 1 + 1e-9).all()   # no borrowing, no shorting
    assert (weights.loc[:, ~member.iloc[0]] == 0).all().all()                          # never holds a stock outside the index
    changed = closes.copy()
    changed.iloc[1001:] *= np.linspace(1, 3, len(closes) - 1001)[:, None]              # rewrite the future
    again = STRATEGIES[name](changed, member, changed.mean(axis=1))
    pd.testing.assert_frame_equal(weights.iloc[:1001], again.iloc[:1001])              # the past decisions must not move
