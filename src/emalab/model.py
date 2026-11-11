"""Can a model tell good golden crosses from bad ones before the fact?

The test is walk forward. To score the crossovers of a given year, the model
is trained only on crossovers whose outcome was already known before that
year began. Then it moves on a year and repeats. Nothing from the future is
ever in the training data.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from .features import FEATURES


def new_model() -> HistGradientBoostingClassifier:
    # Small and cautious on purpose. Market data is mostly noise, and a big model memorizes noise.
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=40, l2_regularization=1.0, random_state=0)


def walk_forward(events: pd.DataFrame, label: str, known: str, first_year: int = 2010, shuffle: bool = False) -> pd.DataFrame:
    """Score every crossover from `first_year` on, using only the past each time.

    `label` is a True or False column. `known` is the date each row's label
    became knowable. Rows get two new columns: `score`, the model's estimated
    chance of a good outcome, and `picked`, True for the scores the model
    would have ranked in its own top third at the time.

    With shuffle=True the training labels are scrambled. A sound test must
    then score no better than a coin flip, which makes this a check on the
    test itself.
    """
    events = events.dropna(subset=[label, known]).sort_values("date").reset_index(drop=True)
    rng = np.random.default_rng(0)
    scored = []
    for year in range(first_year, int(events["date"].dt.year.max()) + 1):
        start = pd.Timestamp(year=year, month=1, day=1)
        train = events[events[known] < start]
        test = events[events["date"].dt.year == year]
        if len(train) < 500 or len(test) == 0:
            continue
        y = train[label].astype(int).to_numpy()
        if shuffle:
            y = rng.permutation(y)
        model = new_model().fit(train[FEATURES], y)
        bar = np.quantile(model.predict_proba(train[FEATURES])[:, 1], 2 / 3)   # set from the past only
        score = model.predict_proba(test[FEATURES])[:, 1]
        scored.append(test.assign(score=score, picked=score >= bar, trained_on=len(train)))
    return pd.concat(scored, ignore_index=True)


def skill(scored: pd.DataFrame, label: str) -> float:
    """How well the scores rank good outcomes above bad ones. 0.5 is a coin flip, 1.0 is perfect."""
    return float(roc_auc_score(scored[label].astype(int), scored["score"]))


def compare_groups(scored: pd.DataFrame) -> pd.DataFrame:
    """Results of the crossovers the model picked, the ones it skipped, and all of them together."""
    groups = {"picked by the model": scored[scored["picked"]], "skipped by the model": scored[~scored["picked"]], "all crossovers": scored}
    rows = []
    for name, g in groups.items():
        rows.append({"group": name, "crossovers": len(g),
                     "share that made money": (g["trade_result"] > 0).mean(), "average trade": g["trade_result"].mean(),
                     "typical trade": g["trade_result"].median(), "average next 10 days": g["forward_10"].mean()})
    return pd.DataFrame(rows).set_index("group")
