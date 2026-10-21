"""Simple, untuned average of AutoETS and LightGBM, the two most accurate single models.

Averaging a statistical and a machine-learning forecast is a classic forecasting result
(and the combination our teammate's Shelf Signal dashboard uses with ETS and GBM).
No weights are fitted, so the test window is not used to build it.

Output: outputs/forecasts/ensemble.parquet  (unique_id, ds, Ensemble)
"""
import pandas as pd

from config import FORECASTS


def main():
    stat = pd.read_parquet(FORECASTS / "stat.parquet", columns=["unique_id", "ds", "AutoETS"])
    lgb = pd.read_parquet(FORECASTS / "lgb.parquet")
    out = stat.merge(lgb, on=["unique_id", "ds"])
    out["Ensemble"] = (out.AutoETS + out.LightGBM) / 2
    out[["unique_id", "ds", "Ensemble"]].to_parquet(FORECASTS / "ensemble.parquet", index=False)
    print(out.Ensemble.describe())


if __name__ == "__main__":
    main()
