"""Fit models directly on the 12 store x department totals.

Claude forecasts each total directly, while the item-level models' totals are sums of
1,437 item forecasts (bottom-up). This script gives AutoARIMA, AutoETS, Chronos and seasonal naive
the same direct view of each total, so the comparison with Claude is like for like.
(LightGBM is a global model; 12 series are too few to train it, so it stays bottom-up.)

Output: outputs/forecasts/direct_agg.parquet  (unique_id = e.g. FOODS_1_CA_1, ds, model columns)
"""
import numpy as np
import pandas as pd
import torch
from chronos import BaseChronosPipeline
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS, SeasonalNaive

from config import PROCESSED, FORECASTS, HORIZON, SEASON, STAT_HISTORY_DAYS, LAST_TRAIN_D
from models_chronos import MODEL, CONTEXT, QUANTILES


def main():
    df = pd.read_parquet(PROCESSED / "sales_long.parquet", columns=["dept_id", "store_id", "d_num", "ds", "y"])
    df = df[df.d_num <= LAST_TRAIN_D]
    df["unique_id"] = df.dept_id.astype(str) + "_" + df.store_id.astype(str)
    agg = df.groupby(["unique_id", "d_num", "ds"], observed=True).y.sum().reset_index()

    hist = agg[agg.d_num > LAST_TRAIN_D - STAT_HISTORY_DAYS]
    sf = StatsForecast(models=[SeasonalNaive(season_length=SEASON), AutoARIMA(season_length=SEASON), AutoETS(season_length=SEASON)],
                       freq="D", n_jobs=-1)
    fc = sf.forecast(df=hist[["unique_id", "ds", "y"]], h=HORIZON)
    fc = fc.reset_index() if "unique_id" not in fc.columns else fc

    wide = agg[agg.d_num > LAST_TRAIN_D - CONTEXT].pivot(index="unique_id", columns="d_num", values="y")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    pipe = BaseChronosPipeline.from_pretrained(MODEL, device_map=device, torch_dtype=torch.float32)
    q, _ = pipe.predict_quantiles(torch.tensor(wide.values, dtype=torch.float32),
                                  prediction_length=HORIZON, quantile_levels=QUANTILES)
    mean = q.cpu().numpy().mean(axis=2)  # average of quantiles, as in models_chronos.py
    dates = pd.date_range(agg.ds.max() + pd.Timedelta(days=1), periods=HORIZON)
    ch = pd.DataFrame({"unique_id": np.repeat(wide.index, HORIZON), "ds": np.tile(dates, len(wide)),
                       "Chronos": mean.reshape(-1)})

    out = fc.merge(ch, on=["unique_id", "ds"])
    cols = ["SeasonalNaive", "AutoARIMA", "AutoETS", "Chronos"]
    out[cols] = out[cols].clip(lower=0)
    out.to_parquet(FORECASTS / "direct_agg.parquet", index=False)
    print(out.head())


if __name__ == "__main__":
    main()
