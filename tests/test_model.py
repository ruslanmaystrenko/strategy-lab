import numpy as np
import pandas as pd

from emalab.features import FEATURES, crossover_events, describe_days
from emalab.model import skill, walk_forward


def stock(seed, n=3000):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2004-01-01", periods=n)
    close = pd.Series(40 * np.exp(np.cumsum(rng.normal(0.0002, 0.02, n))), index=days)
    return pd.DataFrame({"open": close * np.exp(rng.normal(0, 0.003, n)), "high": close * 1.01, "low": close * 0.99, "close": close,
                         "volume": rng.integers(1e5, 1e6, n).astype(float)}, index=days)


def test_what_was_known_never_uses_the_future():
    frame, market = stock(1), stock(2)["close"]
    changed = frame.copy()
    changed.iloc[1501:] *= 2.5
    a, b = describe_days(frame, market), describe_days(changed, market)
    pd.testing.assert_frame_equal(a.iloc[:1501], b.iloc[:1501])


def test_outcomes_start_at_the_next_open():
    frame, market = stock(3), stock(4)["close"]
    events = crossover_events(frame, market, cost=0)
    assert len(events) > 3
    first = events.iloc[0]
    i = frame.index.get_loc(first["date"])
    assert np.isclose(first["forward_10"], frame["close"].iloc[i + 10] / frame["open"].iloc[i + 1] - 1)
    done = events.dropna(subset=["known_on"])
    assert (done["known_on"] > done["date"]).all()


def test_walk_forward_trains_only_on_the_past_and_finds_no_skill_in_noise():
    market = stock(99)["close"]
    events = pd.concat([crossover_events(stock(s), market).assign(ticker=s) for s in range(120)], ignore_index=True)
    events["good"] = events["trade_result"] > 0
    scored = walk_forward(events, "good", "known_on", first_year=2010)
    assert set(FEATURES) <= set(scored.columns)
    assert scored["date"].dt.year.min() >= 2010
    # These prices are pure chance, so an honest test must find close to no skill.
    assert 0.42 < skill(scored, "good") < 0.58
