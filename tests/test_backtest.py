import numpy as np
import pandas as pd
import pytest

from emalab.backtest import strategy_returns, summarize, trades
from emalab.signals import ema_crossover


def days(n):
    return pd.bdate_range("2015-01-01", periods=n)


def test_signal_never_uses_the_future():
    # Changing prices after day 400 must not change any decision made on or before day 400.
    rng = np.random.default_rng(1)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 800))), index=days(800))
    changed = close.copy()
    changed.iloc[401:] *= 3
    assert ema_crossover(close).iloc[:401].equals(ema_crossover(changed).iloc[:401])


def test_signal_waits_for_a_real_cross():
    # A steady climb from day one: the fast line is above the slow line the whole time, so there is never a cross.
    close = pd.Series(np.linspace(10, 100, 600), index=days(600))
    assert ema_crossover(close).sum() == 0


def test_signal_opens_on_a_cross_and_closes_on_the_cross_back():
    down, up, down_again = np.linspace(100, 50, 400), np.linspace(50, 150, 300), np.linspace(150, 40, 300)
    close = pd.Series(np.concatenate([down, up, down_again]), index=days(1000))
    wanted = ema_crossover(close)
    changes = wanted.diff().fillna(0)
    assert (changes == 1).sum() == 1 and (changes == -1).sum() == 1
    assert 400 < int(np.argmax(wanted.to_numpy())) < 700          # opens during the climb
    assert wanted.iloc[-1] == 0                                   # and is out by the end


def test_trading_happens_at_the_next_open_and_costs_money():
    idx = days(5)
    open_ = pd.Series([10, 10, 11, 12, 12.0], index=idx)
    close = pd.Series([10, 10, 12, 12, 11.0], index=idx)
    wanted = pd.Series([0, 1, 1, 0, 0], index=idx)   # decide to buy at the close of day 1, to sell at the close of day 3
    out = strategy_returns(open_, close, wanted, cost=0.01)
    assert list(out["held"]) == [0, 0, 1, 1, 0]
    assert out["strategy"].iloc[1] == 0                                # nothing happens on the day of the decision
    assert out["strategy"].iloc[2] == pytest.approx(12 / 11 * 0.99 - 1)  # bought at day 2's open of 11
    assert out["strategy"].iloc[3] == pytest.approx(12 / 12 - 1)         # held close to close
    assert out["strategy"].iloc[4] == pytest.approx(12 / 12 * 0.99 - 1)  # sold at day 4's open of 12
    log = trades(out, open_, cost=0.01)
    assert len(log) == 1
    assert log["result"].iloc[0] == pytest.approx((12 * 0.99) / (11 / 0.99) - 1)
    # The daily returns multiply out to the same result as the trade log.
    assert (1 + out["strategy"]).prod() - 1 == pytest.approx(log["result"].iloc[0])


def test_always_in_matches_holding_apart_from_the_first_day():
    rng = np.random.default_rng(2)
    close = pd.Series(50 * np.exp(np.cumsum(rng.normal(0, 0.01, 300))), index=days(300))
    out = strategy_returns(close, close, pd.Series(1, index=close.index), cost=0)
    assert np.allclose(out["strategy"].iloc[2:], out["hold"].iloc[2:])


def test_summary_numbers():
    daily = pd.Series([0.10, -0.50, 0.20] + [0.0] * 249)
    s = summarize(daily)
    assert s.total_return == pytest.approx(1.1 * 0.5 * 1.2 - 1)
    assert s.worst_drop == pytest.approx(-0.5)
    assert s.days == 252
    assert s.yearly_return == pytest.approx(s.total_return)   # exactly one year of days
