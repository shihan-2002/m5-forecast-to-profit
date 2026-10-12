"""Build the CA / FOODS slice of M5 in long format.

Outputs (data/processed):
  sales_long.parquet  one row per item-store-day, d_1..d_1969, with price and calendar fields
  meta.parquet        one row per series (unique_id, item_id, dept_id, store_id)
"""
import pandas as pd

from config import RAW, PROCESSED, STATE, CATEGORY, LAST_TRAIN_D

ID_COLS = ["item_id", "dept_id", "cat_id", "store_id", "state_id"]


def load_wide():
    train = pd.read_csv(RAW / "sales_train_evaluation.csv")
    test = pd.read_csv(RAW / "sales_test_evaluation.csv")
    wide = train.merge(test, on=ID_COLS)
    wide = wide[(wide.state_id == STATE) & (wide.cat_id == CATEGORY)].reset_index(drop=True)
    wide.insert(0, "unique_id", wide.item_id + "_" + wide.store_id)
    return wide


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    wide = load_wide()
    meta = wide[["unique_id"] + ID_COLS]

    long = wide.melt(id_vars=["unique_id"] + ID_COLS, var_name="d", value_name="y")
    long["d_num"] = long.d.str[2:].astype(int)

    cal = pd.read_csv(RAW / "calendar.csv", parse_dates=["date"])
    cal["d_num"] = range(1, len(cal) + 1)
    cal = cal[["d_num", "date", "wm_yr_wk", "wday", "month", "year",
               "event_name_1", "event_type_1", f"snap_{STATE}"]].rename(columns={f"snap_{STATE}": "snap"})
    long = long.merge(cal, on="d_num", how="left")

    prices = pd.read_csv(RAW / "sell_prices.csv")
    prices = prices[prices.store_id.str.startswith(STATE) & prices.item_id.str.startswith(CATEGORY)]
    long = long.merge(prices, on=["store_id", "item_id", "wm_yr_wk"], how="left")

    long = long.rename(columns={"date": "ds"}).drop(columns=["d", "cat_id", "state_id"])
    long = long.sort_values(["unique_id", "d_num"]).reset_index(drop=True)
    long["is_test"] = long.d_num > LAST_TRAIN_D

    for c in ["item_id", "dept_id", "store_id", "event_name_1", "event_type_1"]:
        long[c] = long[c].astype("category")

    long.to_parquet(PROCESSED / "sales_long.parquet", index=False)
    meta.to_parquet(PROCESSED / "meta.parquet", index=False)
    print(f"{meta.shape[0]} series, {long.shape[0]:,} rows, "
          f"{long.ds.min().date()} to {long.ds.max().date()}")
    print(meta.groupby(["store_id", "dept_id"]).size().unstack())


if __name__ == "__main__":
    main()
