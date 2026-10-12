"""Classical forecasts for every item-store series with statsforecast.

Usage: python models_stat.py [--sample N]
Output: outputs/forecasts/stat.parquet  (unique_id, ds, one column per model)
"""
import argparse
import time

import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import (
    AutoARIMA, AutoETS, CrostonOptimized, ADIDA, SeasonalNaive, WindowAverage,
)

from config import PROCESSED, FORECASTS, HORIZON, SEASON, STAT_HISTORY_DAYS, LAST_TRAIN_D


def main(sample=None):
    df = pd.read_parquet(PROCESSED / "sales_long.parquet", columns=["unique_id", "ds", "y", "d_num"])
    df = df[(df.d_num <= LAST_TRAIN_D) & (df.d_num > LAST_TRAIN_D - STAT_HISTORY_DAYS)]
    df["unique_id"] = df.unique_id.astype(str)
    if sample:
        keep = df.unique_id.drop_duplicates().sample(sample, random_state=0)
        df = df[df.unique_id.isin(keep)]

    models = [
        SeasonalNaive(season_length=SEASON),
        WindowAverage(window_size=28),
        AutoETS(season_length=SEASON),
        AutoARIMA(season_length=SEASON),
        CrostonOptimized(),
        ADIDA(),
    ]
    sf = StatsForecast(models=models, freq="D", n_jobs=-1)
    t0 = time.time()
    fc = sf.forecast(df=df[["unique_id", "ds", "y"]], h=HORIZON)
    print(f"{df.unique_id.nunique()} series in {time.time() - t0:.0f}s")

    fc = fc.reset_index() if "unique_id" not in fc.columns else fc
    model_cols = [c for c in fc.columns if c not in ("unique_id", "ds")]
    fc[model_cols] = fc[model_cols].clip(lower=0)
    if not sample:
        FORECASTS.mkdir(parents=True, exist_ok=True)
        fc.to_parquet(FORECASTS / "stat.parquet", index=False)
    print(fc.head())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int)
    main(p.parse_args().sample)
