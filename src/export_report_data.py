"""Export the tables the Quarto report (report/report.qmd) reads, as plain CSV, so the
report's R code needs no parquet support. Run after evaluate.py, evaluate_claude.py and
models_direct_agg.py.

Output: outputs/results/report/*.csv
"""
import numpy as np
import pandas as pd

from config import PROCESSED, ROOT, LAST_TRAIN_D, MARGINS
from evaluate import nb_quantile, chronos_quantile

RESULTS = ROOT / "outputs" / "results"
OUT = RESULTS / "report"
MODELS = ["AutoARIMA", "AutoETS", "LightGBM", "Ensemble", "Chronos", "SeasonalNaive"]


def rmsse_inputs(train):
    tr = train.sort_values(["unique_id", "d_num"])
    started = tr.groupby("unique_id").y.cumsum() > 0
    scale = (tr[started].groupby("unique_id").y.diff() ** 2).groupby(tr.loc[started, "unique_id"]).mean()
    return scale.rename("scale")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sales = pd.read_parquet(PROCESSED / "sales_long.parquet",
                            columns=["unique_id", "ds", "d_num", "y", "snap", "is_test"])
    sales["unique_id"] = sales.unique_id.astype(str)
    train = sales[~sales.is_test]

    # Data description
    weekly = sales.groupby("ds").y.sum().resample("W").sum().iloc[1:]
    weekly.rename("units").rename_axis("week").reset_index().to_csv(OUT / "weekly_sales.csv", index=False)
    wd = train.groupby(train.ds.dt.day_name()).y.mean()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pd.DataFrame({"weekday": order, "index": (wd[order] / wd.mean() * 100).round(1).values}).to_csv(
        OUT / "weekday_index.csv", index=False)
    zero = train[train.d_num > LAST_TRAIN_D - 365].groupby("unique_id").y.apply(lambda s: (s == 0).mean())
    snap = train.groupby("snap").y.mean()
    pd.DataFrame([{"snap_lift": snap[1] / snap[0] - 1, "median_zero_share": zero.median(),
                   "n_series": sales.unique_id.nunique()}]).to_csv(OUT / "data_facts.csv", index=False)

    # Test window, all items summed
    joined = pd.read_parquet(RESULTS / "joined.parquet")
    tot = joined.groupby("ds")[["y"] + MODELS].sum().reset_index()
    tot.to_csv(OUT / "test_window_totals.csv", index=False)

    # Item level: who wins each series, and error by how often an item sells zero
    joined = joined.join(rmsse_inputs(train), on="unique_id")
    g = joined[joined.scale > 0]
    per = g.groupby("unique_id").apply(
        lambda d: pd.Series({m: np.sqrt(((d[m] - d.y) ** 2).mean() / d.scale.iloc[0]) for m in MODELS}),
        include_groups=False)
    best = per[["AutoARIMA", "AutoETS", "LightGBM", "Chronos"]].idxmin(axis=1).value_counts(normalize=True)
    best.rename("share").rename_axis("model").reset_index().to_csv(OUT / "item_best_share.csv", index=False)
    grp = pd.cut(zero, [-0.01, 0.2, 0.5, 0.8, 1.0], labels=["<20%", "20-50%", "50-80%", ">80%"]).rename("zero_days")
    byg = per.join(grp).groupby("zero_days", observed=True)[MODELS].mean()
    byg["n_series"] = grp.value_counts()
    byg.reset_index().to_csv(OUT / "item_rmsse_by_zero_share.csv", index=False)

    # Business insight: newsvendor profit, bootstrap over items, predicted vs actual
    s = joined[joined.sell_price.notna()].copy()
    p, d, phi = s.sell_price.to_numpy(), s.y.to_numpy(), s.phi.to_numpy()
    rng = np.random.default_rng(0)
    boot_rows, pred_rows = [], []
    for m in MARGINS:
        c = p * (1 - m)
        orders = {mod: np.maximum(np.round(nb_quantile(s[mod].to_numpy(), phi, m)), 0)
                  for mod in ["AutoARIMA", "LightGBM"]}
        orders["Chronos"] = np.maximum(np.round(chronos_quantile(s, m)), 0)
        prof = pd.DataFrame({k: p * np.minimum(Q, d) - c * Q for k, Q in orders.items()})
        per_item = prof.groupby(s.unique_id.values).sum()
        for other in ["AutoARIMA", "Chronos"]:
            diff = (per_item[other] - per_item.LightGBM).to_numpy()
            boots = [diff[rng.integers(0, len(diff), len(diff))].sum() for _ in range(2000)]
            boot_rows.append({"margin": m, "comparison": f"{other} minus LightGBM", "diff": diff.sum(),
                              "lo95": np.percentile(boots, 2.5), "hi95": np.percentile(boots, 97.5)})
        for mod in ["AutoARIMA", "LightGBM"]:
            mu = np.maximum(s[mod].to_numpy(), 1e-6)
            sims = [(p * np.minimum(orders[mod], rng.negative_binomial(mu / (phi - 1), 1 / phi)) - c * orders[mod]).sum()
                    for _ in range(200)]
            pred_rows.append({"margin": m, "model": mod, "predicted": np.mean(sims),
                              "pred_lo90": np.percentile(sims, 5), "pred_hi90": np.percentile(sims, 95),
                              "actual": prof[mod].sum()})
    pd.DataFrame(boot_rows).to_csv(OUT / "newsvendor_bootstrap.csv", index=False)
    pd.DataFrame(pred_rows).to_csv(OUT / "newsvendor_predicted_vs_actual.csv", index=False)

    for name in ["accuracy.csv", "accuracy_by_level.csv", "claude_accuracy.csv", "timing.csv", "profit.csv"]:
        (OUT / name).write_bytes((RESULTS / name).read_bytes())
    print(sorted(p.name for p in OUT.glob("*.csv")))


if __name__ == "__main__":
    main()
