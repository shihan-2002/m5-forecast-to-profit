"""Zero-shot forecasts from Amazon's Chronos-Bolt foundation model.

Chronos is never trained on our data: it reads the last CONTEXT days of each series
and outputs a forecast distribution (quantiles 0.1..0.9) directly.

Output: outputs/forecasts/chronos.parquet  (unique_id, ds, Chronos, q10..q90)
"""
import time

import numpy as np
import pandas as pd
import torch
from chronos import BaseChronosPipeline

from config import PROCESSED, FORECASTS, HORIZON, LAST_TRAIN_D

MODEL = "amazon/chronos-bolt-small"
CONTEXT = 512
BATCH = 256
QUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def main():
    df = pd.read_parquet(PROCESSED / "sales_long.parquet", columns=["unique_id", "d_num", "ds", "y"])
    df = df[(df.d_num <= LAST_TRAIN_D) & (df.d_num > LAST_TRAIN_D - CONTEXT)]
    df["unique_id"] = df.unique_id.astype(str)
    wide = df.pivot(index="unique_id", columns="d_num", values="y")
    ids = wide.index.tolist()
    ctx = torch.tensor(wide.values, dtype=torch.float32)

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    pipe = BaseChronosPipeline.from_pretrained(MODEL, device_map=device, torch_dtype=torch.float32)

    t0 = time.time()
    qs = []
    for i in range(0, len(ids), BATCH):
        q, _ = pipe.predict_quantiles(ctx[i:i + BATCH], prediction_length=HORIZON,
                                      quantile_levels=QUANTILES)
        qs.append(q.cpu().numpy())
    q = np.clip(np.concatenate(qs), 0, None)  # (series, horizon, quantile)
    # Chronos-Bolt's "mean" is really its median, which sits below the mean for
    # intermittent, right-skewed sales. Average the nine quantiles to approximate the mean.
    mean = q.mean(axis=2)
    print(f"{len(ids)} series in {time.time() - t0:.0f}s on {device}")

    dates = pd.date_range(df.ds.max() + pd.Timedelta(days=1), periods=HORIZON)
    out = pd.DataFrame({
        "unique_id": np.repeat(ids, HORIZON),
        "ds": np.tile(dates, len(ids)),
        "Chronos": mean.reshape(-1),
    })
    for j, ql in enumerate(QUANTILES):
        out[f"q{int(ql * 100)}"] = q[:, :, j].reshape(-1)
    out.to_parquet(FORECASTS / "chronos.parquet", index=False)
    print(out.head())


if __name__ == "__main__":
    main()
