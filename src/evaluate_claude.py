"""Compare Claude with AutoARIMA, LightGBM, Chronos (and seasonal naive) on the series
Claude forecast. Run after models_claude.py and evaluate.py.

Two comparisons on the same 28-day test window:
  item x store  the sampled item-store series
  store x dept  the 12 store x dept totals: Claude forecasts each total directly; the
                other models are summed up from their item forecasts (bottom-up)

Claude appears twice: Claude (named) and Claude (blind). If named beats blind clearly,
Claude may be recalling the public M5 data rather than forecasting.

Output: outputs/results/claude_accuracy.csv
"""
import numpy as np
import pandas as pd

from config import FORECASTS, ROOT, LAST_TRAIN_D

RESULTS = ROOT / "outputs" / "results"
BASE = ["SeasonalNaive", "AutoARIMA", "AutoETS", "LightGBM", "Ensemble", "Chronos"]


def scale_and_weight(train):
    """Per-series RMSSE scale (naive one-step error from first sale) and dollar weight."""
    train = train.sort_values(["unique_id", "d_num"])
    started = train.groupby("unique_id").y.cumsum() > 0
    diffs = train[started].groupby("unique_id").y.diff()
    scale = (diffs ** 2).groupby(train.loc[started, "unique_id"]).mean()
    last = train[train.d_num > LAST_TRAIN_D - 28]
    w = last.groupby("unique_id").dollars.sum()
    return pd.DataFrame({"scale": scale, "w": w / w.sum()})


def accuracy(test, train, models):
    sw = scale_and_weight(train)
    rows = {}
    for m in models:
        err = test[m] - test.y
        mse = (err ** 2).groupby(test.unique_id).mean()
        info = sw.join(mse.rename("mse"), how="inner")
        info = info[info.scale > 0]
        rows[m] = {
            "WRMSSE": (np.sqrt(info.mse / info.scale) * info.w).sum() / info.w.sum(),
            "MAE": err.abs().mean(),
            "RMSE": np.sqrt((err ** 2).mean()),
            "MAPE of total (%)": (test.groupby("ds")[m].sum() - test.groupby("ds").y.sum()).abs().div(
                test.groupby("ds").y.sum()).mean() * 100,
            "Bias (%)": (test[m].sum() / test.y.sum() - 1) * 100,
        }
    return pd.DataFrame(rows).T


def main():
    joined = pd.read_parquet(RESULTS / "joined.parquet")
    claude = pd.read_parquet(FORECASTS / "claude.parquet")
    data = pd.read_parquet(ROOT / "data/processed/sales_long.parquet",
                           columns=["unique_id", "dept_id", "store_id", "d_num", "y", "sell_price"])
    data["unique_id"] = data.unique_id.astype(str)
    data["dollars"] = data.y * data.sell_price.fillna(0)
    train = data[data.d_num <= LAST_TRAIN_D]

    wide = claude.pivot_table(index=["unique_id", "ds"], columns="condition", values="Claude").reset_index()
    wide = wide.rename(columns={"named": "Claude (named)", "blind": "Claude (blind)"})
    models = BASE + [c for c in ["Claude (named)", "Claude (blind)"] if c in wide]

    items = claude.loc[claude.level == "item x store", "unique_id"].unique()
    it = joined[joined.unique_id.isin(items)].merge(wide, on=["unique_id", "ds"], how="inner")
    acc_items = accuracy(it, train[train.unique_id.isin(items)], models).assign(level="item x store")

    joined["agg_id"] = joined.dept_id.astype(str) + "_" + joined.store_id.astype(str)
    ag = joined.groupby(["agg_id", "ds"], observed=True)[["y"] + BASE].sum().reset_index()
    ag = ag.rename(columns={"agg_id": "unique_id"}).merge(wide, on=["unique_id", "ds"], how="inner")
    ag = ag.rename(columns={m: f"{m} (sum of items)" for m in BASE})
    direct = pd.read_parquet(FORECASTS / "direct_agg.parquet")
    direct = direct.rename(columns={m: f"{m} (direct)" for m in ["SeasonalNaive", "AutoARIMA", "AutoETS", "Chronos"]})
    ag = ag.merge(direct, on=["unique_id", "ds"], how="inner")
    agg_models = [c for c in ag.columns if c not in ("unique_id", "ds", "y")]
    tr = train.assign(unique_id=train.dept_id.astype(str) + "_" + train.store_id.astype(str))
    tr = tr.groupby(["unique_id", "d_num"], observed=True)[["y", "dollars"]].sum().reset_index()
    acc_aggs = accuracy(ag, tr, agg_models).assign(level="store x dept")
    ag.to_parquet(RESULTS / "claude_agg_joined.parquet", index=False)
    it.to_parquet(RESULTS / "claude_items_joined.parquet", index=False)

    acc = pd.concat([acc_aggs, acc_items]).rename_axis("model").reset_index()
    acc.to_csv(RESULTS / "claude_accuracy.csv", index=False)
    pd.set_option("display.width", 160)
    print(f"{ag.unique_id.nunique()} store x dept totals, {len(items)} item series\n")
    print(acc.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
