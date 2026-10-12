"""Global LightGBM model across all item-store series.

Uses only lags of 28+ days, so all 28 test days are predicted in one shot with no
recursion. The number of boosting rounds is picked by early stopping on the last 28
training days (d_1914..d_1941), then the model is refit on all training data.

Output: outputs/forecasts/lgb.parquet  (unique_id, ds, LightGBM)
"""
import lightgbm as lgb
import numpy as np
import pandas as pd

from config import PROCESSED, FORECASTS, HORIZON, LAST_TRAIN_D

FIRST_D = 1000  # ~2.6 years of training rows is plenty and keeps memory low
CATS = ["dept_id", "store_id", "event_name_1", "event_type_1"]


def build_features(df):
    df = df.sort_values(["unique_id", "d_num"]).copy()
    g = df.groupby("unique_id", observed=True)["y"]
    for lag in [28, 35, 42, 49, 56]:
        df[f"lag_{lag}"] = g.shift(lag)
    lag28 = g.shift(28)
    by_id = lag28.groupby(df.unique_id, observed=True)
    for w in [7, 28, 56, 180]:
        df[f"rmean_{w}"] = by_id.transform(lambda s: s.rolling(w, min_periods=1).mean())
    df["rstd_28"] = by_id.transform(lambda s: s.rolling(28, min_periods=2).std())

    p = df.groupby("unique_id", observed=True)["sell_price"]
    df["price_rel"] = df.sell_price / p.transform("mean")
    df["price_chg"] = df.sell_price / p.shift(7) - 1
    df["mday"] = df.ds.dt.day
    return df


def main():
    cols = ["unique_id", "d_num", "ds", "y", "sell_price", "wday", "month", "snap"] + CATS
    df = pd.read_parquet(PROCESSED / "sales_long.parquet", columns=cols)
    df = df[df.d_num >= FIRST_D - 240]  # extra history for the long rolling windows
    df = build_features(df)
    df = df[(df.d_num >= FIRST_D) & df.sell_price.notna()]

    feats = [c for c in df.columns if c not in ("unique_id", "d_num", "ds", "y")]
    params = dict(objective="tweedie", tweedie_variance_power=1.1, learning_rate=0.03,
                  num_leaves=127, min_data_in_leaf=100, feature_fraction=0.8,
                  bagging_fraction=0.8, bagging_freq=1, lambda_l2=0.1, verbose=-1, n_jobs=-1)

    train = df[df.d_num <= LAST_TRAIN_D]
    fit_part = train[train.d_num <= LAST_TRAIN_D - HORIZON]
    val_part = train[train.d_num > LAST_TRAIN_D - HORIZON]
    dtr = lgb.Dataset(fit_part[feats], fit_part.y, categorical_feature=CATS)
    dval = lgb.Dataset(val_part[feats], val_part.y, categorical_feature=CATS, reference=dtr)
    m = lgb.train(params, dtr, num_boost_round=3000, valid_sets=[dval],
                  callbacks=[lgb.early_stopping(100), lgb.log_evaluation(100)])
    best = m.best_iteration
    print("best rounds:", best)

    full = lgb.train(params, lgb.Dataset(train[feats], train.y, categorical_feature=CATS),
                     num_boost_round=best)
    test = df[df.d_num > LAST_TRAIN_D]
    out = test[["unique_id", "ds"]].copy()
    out["unique_id"] = out.unique_id.astype(str)
    out["LightGBM"] = np.clip(full.predict(test[feats]), 0, None)

    # Series with no price in the test window are off the shelf: forecast zero
    ids = pd.read_parquet(PROCESSED / "meta.parquet").unique_id
    dates = pd.date_range(test.ds.min(), periods=HORIZON)
    grid = pd.MultiIndex.from_product([ids, dates], names=["unique_id", "ds"]).to_frame(index=False)
    out = grid.merge(out, on=["unique_id", "ds"], how="left").fillna({"LightGBM": 0.0})
    out.to_parquet(FORECASTS / "lgb.parquet", index=False)

    imp = pd.Series(full.feature_importance("gain"), index=feats).sort_values(ascending=False)
    imp.to_frame("gain").to_parquet(FORECASTS / "lgb_importance.parquet")
    print(imp.head(10))


if __name__ == "__main__":
    main()
