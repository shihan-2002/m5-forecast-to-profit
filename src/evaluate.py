"""Score every model on accuracy (WRMSSE) and on inventory profit (newsvendor).

Accuracy follows the M5 recipe restricted to our CA / FOODS slice: RMSSE per series,
weighted by each series' dollar sales in the last 28 training days, averaged over six
aggregation levels (total, store, dept, store x dept, item, item x store).

Profit: each day the store orders Q units of each item. Food is treated as perishable,
so unsold units are written off at cost and there is no carry-over. With price p and
gross margin m (cost c = p(1-m)):
    profit = p * min(Q, demand) - c * Q
The profit-maximizing order is the m-quantile of the demand distribution (the
newsvendor critical ratio cu / (cu + co) = m when leftovers are worth nothing).

Policies compared for each model:
  point     order the rounded point forecast (what most teams do)
  nb        order the m-quantile of a negative binomial centred on the forecast
  native    Chronos only: order its own predicted m-quantile

Outputs (outputs/results): accuracy.csv, accuracy_by_level.csv, profit.csv, joined.parquet
"""
import numpy as np
import pandas as pd
from scipy import stats

from config import PROCESSED, FORECASTS, ROOT, HORIZON, LAST_TRAIN_D, MARGINS

RESULTS = ROOT / "outputs" / "results"
LEVELS = {
    "L1 total": [],
    "L2 store": ["store_id"],
    "L3 dept": ["dept_id"],
    "L4 store x dept": ["store_id", "dept_id"],
    "L5 item": ["item_id"],
    "L6 item x store": ["item_id", "store_id"],
}


def load_forecasts():
    fc = pd.read_parquet(FORECASTS / "stat.parquet")
    for name in ["lgb", "chronos", "ensemble"]:
        path = FORECASTS / f"{name}.parquet"
        if path.exists():
            fc = fc.merge(pd.read_parquet(path), on=["unique_id", "ds"], how="left")
    return fc


def model_columns(fc):
    return [c for c in fc.columns if c not in ("unique_id", "ds") and not c.startswith("q")]


def wrmsse(train, test, models):
    """train: unique_id, d_num, y, dollars, keys.  test: unique_id, ds, y, models, keys."""
    rows, per_level = [], {}
    for level, keys in LEVELS.items():
        k = keys or ["_all"]
        tr = train.assign(_all="all").groupby(k + ["d_num"], observed=True)[["y", "dollars"]].sum().reset_index()
        te = test.assign(_all="all").groupby(k + ["ds"], observed=True)[["y"] + models].sum().reset_index()

        # Scale: mean squared one-step naive error, from each series' first sale onward
        tr = tr.sort_values(k + ["d_num"])
        started = tr.groupby(k, observed=True)["y"].cumsum() > 0
        diffs = tr[started].groupby(k, observed=True)["y"].diff()
        scale = (diffs ** 2).groupby([tr.loc[started, c] for c in k], observed=True).mean().rename("scale")

        last = tr[tr.d_num > LAST_TRAIN_D - HORIZON]
        w = last.groupby(k, observed=True)["dollars"].sum()
        w = (w / w.sum()).rename("w")

        mse = te.groupby(k, observed=True).apply(
            lambda g: pd.Series({m: ((g[m] - g.y) ** 2).mean() for m in models}), include_groups=False)
        info = pd.concat([scale, w], axis=1).join(mse, how="inner")
        info = info[info.scale > 0]
        rmsse = np.sqrt(info[models].div(info.scale, axis=0))
        per_level[level] = (rmsse.mul(info.w, axis=0)).sum() / info.w.sum()
    by_level = pd.DataFrame(per_level).T
    return by_level, by_level.mean().rename("WRMSSE")


def dispersion(train):
    """Variance-to-mean ratio of each series' last 180 days of sales (floored at 1)."""
    recent = train[train.d_num > LAST_TRAIN_D - 180]
    g = recent.groupby("unique_id", observed=True)["y"]
    phi = (g.var() / g.mean().replace(0, np.nan)).fillna(1).clip(lower=1.01, upper=50)
    return phi.rename("phi")


def nb_quantile(mu, phi, q):
    """Negative binomial with mean mu and variance phi * mu."""
    mu = np.maximum(mu, 1e-6)
    n = mu / (phi - 1)
    p = 1 / phi
    return stats.nbinom.ppf(q, n, p)


def chronos_quantile(df, q):
    levels = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90]) / 100
    Q = df[[f"q{int(l * 100)}" for l in levels]].to_numpy()
    q = np.clip(q, levels[0], levels[-1])
    hi = np.searchsorted(levels, q)
    hi = np.clip(hi, 1, len(levels) - 1)
    lo = hi - 1
    t = (q - levels[lo]) / (levels[hi] - levels[lo])
    return Q[:, lo] * (1 - t) + Q[:, hi] * t


def profit_table(test, models):
    rows = []
    sold = test[test.sell_price.notna()].copy()
    d, p = sold.y.to_numpy(), sold.sell_price.to_numpy()
    for m in MARGINS:
        c = p * (1 - m)
        perfect = (p * m * d).sum()

        def score(model, policy, Q):
            Q = np.maximum(np.round(Q), 0)
            prof = (p * np.minimum(Q, d) - c * Q).sum()
            rows.append(dict(margin=m, model=model, policy=policy, profit=prof,
                             pct_of_perfect=prof / perfect,
                             fill_rate=np.minimum(Q, d).sum() / d.sum(),
                             waste_units=np.maximum(Q - d, 0).sum()))

        for model in models:
            score(model, "point", sold[model].to_numpy())
            score(model, "nb", nb_quantile(sold[model].to_numpy(), sold.phi.to_numpy(), m))
        if "q50" in sold:
            score("Chronos", "native", chronos_quantile(sold, m))
    return pd.DataFrame(rows)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    data = pd.read_parquet(PROCESSED / "sales_long.parquet",
                           columns=["unique_id", "item_id", "dept_id", "store_id", "d_num", "ds", "y", "sell_price"])
    data["unique_id"] = data.unique_id.astype(str)
    data["dollars"] = data.y * data.sell_price.fillna(0)
    train = data[data.d_num <= LAST_TRAIN_D]
    test = data[data.d_num > LAST_TRAIN_D].drop(columns=["dollars"])

    fc = load_forecasts()
    models = model_columns(fc)
    test = test.merge(fc, on=["unique_id", "ds"], how="left")
    test = test.merge(dispersion(train), left_on="unique_id", right_index=True, how="left")
    test.to_parquet(RESULTS / "joined.parquet", index=False)

    by_level, total = wrmsse(train, test, models)
    err = test[models].sub(test.y, axis=0)
    acc = pd.DataFrame({
        "WRMSSE": total,
        "MAE": err.abs().mean(),
        "RMSE": np.sqrt((err ** 2).mean()),
        "Bias (units/day)": err.mean(),
    }).sort_values("WRMSSE")
    acc.to_csv(RESULTS / "accuracy.csv")
    by_level.to_csv(RESULTS / "accuracy_by_level.csv")

    prof = profit_table(test, models)
    prof.to_csv(RESULTS / "profit.csv", index=False)

    pd.set_option("display.width", 160)
    print(acc.round(3))
    print(by_level.round(3))
    best = prof.loc[prof.groupby("margin").profit.idxmax()]
    print("\nMost profitable model/policy by margin:\n", best.round(3))
    print(prof.pivot_table(index=["model", "policy"], columns="margin", values="pct_of_perfect").round(3))


if __name__ == "__main__":
    main()
