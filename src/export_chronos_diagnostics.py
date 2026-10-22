"""Two diagnostics on Chronos for the report: why its summed forecast runs low, and how
well its quantiles are calibrated (what the newsvendor order uses).

Run after evaluate.py.
Output: outputs/results/report/chronos_bias_by_volume.csv, chronos_calibration.csv
"""
import pandas as pd

from config import PROCESSED, FORECASTS, ROOT, LAST_TRAIN_D

RESULTS = ROOT / "outputs" / "results"
OUT = RESULTS / "report"
QUANTILES = ["q10", "q20", "q30", "q40", "q50", "q60", "q70", "q80", "q90"]


def main():
    joined = pd.read_parquet(RESULTS / "joined.parquet", columns=["unique_id", "ds", "y", "Chronos"])
    joined["unique_id"] = joined.unique_id.astype(str)

    # Shortfall by sales volume: items split into quarters by their last 56 training days
    sales = pd.read_parquet(PROCESSED / "sales_long.parquet", columns=["unique_id", "d_num", "y"])
    sales["unique_id"] = sales.unique_id.astype(str)
    recent = sales[(sales.d_num > LAST_TRAIN_D - 56) & (sales.d_num <= LAST_TRAIN_D)]
    volume = recent.groupby("unique_id").y.mean().rename("recent_mean")
    items = joined.groupby("unique_id")[["y", "Chronos"]].sum().join(volume)
    items["group"] = pd.qcut(items.recent_mean.rank(method="first"), 4,
                             labels=["Sparsest quarter", "Low", "Middle", "Busiest quarter"])
    by_vol = items.groupby("group", observed=True)[["y", "Chronos"]].sum()
    by_vol["gap"] = by_vol.Chronos / by_vol.y - 1
    by_vol.reset_index().to_csv(OUT / "chronos_bias_by_volume.csv", index=False)

    # Calibration: share of item-days with actual sales at or below each quantile
    q = pd.read_parquet(FORECASTS / "chronos.parquet", columns=["unique_id", "ds"] + QUANTILES)
    q["unique_id"] = q.unique_id.astype(str)
    m = q.merge(joined[["unique_id", "ds", "y"]], on=["unique_id", "ds"])
    pd.DataFrame({"quantile": [int(c[1:]) / 100 for c in QUANTILES],
                  "coverage": [(m.y <= m[c]).mean() for c in QUANTILES]}).to_csv(
        OUT / "chronos_calibration.csv", index=False)
    print(by_vol.round(3), "\n", pd.read_csv(OUT / "chronos_calibration.csv").round(3))


if __name__ == "__main__":
    main()
