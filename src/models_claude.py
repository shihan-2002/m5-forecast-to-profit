"""Forecasts from Claude (a general-purpose LLM) on a sample of series.

Calling an LLM once per series is slow and costs money, so Claude forecasts:
  - the 12 store x department totals (aggregate demand), and
  - a random sample of item-store series (SAMPLE_ITEMS, seed fixed).

Each series is forecast twice, to test whether Claude is recalling M5 (public since
2020) rather than forecasting:
  named  real dates, "Walmart", store and item ids, holiday names
  blind  no names, no dates or year: only "day -364..+28", weekday, a generic holiday flag

Claude sees the last HISTORY_DAYS of sales, plus weekday / holiday / SNAP / price for
history and the 28 days ahead, i.e. roughly what LightGBM sees. It returns, per day, a
mean forecast and the 20/35/50/65/80th percentiles (kept for the later profit analysis).

Each response is cached in outputs/claude_raw/, so reruns skip finished calls.

Usage:
  python models_claude.py --dry-run          # print one prompt, call nothing
  python models_claude.py --limit 2          # try 2 series x 2 conditions
  python models_claude.py                    # full run
Output: outputs/forecasts/claude.parquet
"""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
import numpy as np
import pandas as pd

from config import PROCESSED, FORECASTS, ROOT, HORIZON, LAST_TRAIN_D

MODEL = "claude-opus-5-5"
EFFORT = "medium"
HISTORY_DAYS = 365
SAMPLE_ITEMS = 100
SEED = 42
WORKERS = 6
RAW = ROOT / "outputs" / "claude_raw"
QUANTILES = [20, 35, 50, 65, 80]

DAY_SCHEMA = {
    "type": "object",
    "properties": {"day": {"type": "integer"}, "mean": {"type": "number"},
                   **{f"q{q}": {"type": "number"} for q in QUANTILES}},
    "required": ["day", "mean"] + [f"q{q}" for q in QUANTILES],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {"reasoning": {"type": "string"},
                   "forecast": {"type": "array", "items": DAY_SCHEMA}},
    "required": ["reasoning", "forecast"],
    "additionalProperties": False,
}

SYSTEM = (
    "You are a demand forecaster for a grocery retailer. You will get a daily unit-sales "
    "history and calendar information, and you forecast the next 28 days. Return, for each "
    "future day, your mean (expected) demand and the 20th, 35th, 50th, 65th and 80th "
    "percentiles of demand. Percentiles must be non-decreasing and non-negative. Sales are "
    "whole units, and many items sell zero on most days, so percentiles may be 0. Base the "
    "forecast only on the data given. Keep 'reasoning' to two or three sentences."
)


def select_series(df):
    """12 store x dept totals + a fixed random sample of item-store series."""
    recent = df[(df.d_num > LAST_TRAIN_D - 90) & (df.d_num <= LAST_TRAIN_D)]
    active = recent.groupby("unique_id", observed=True).y.sum()
    active = active[active > 0].index.astype(str)  # skip items with no sales in 90 days
    rng = np.random.default_rng(SEED)
    items = sorted(rng.choice(sorted(active), SAMPLE_ITEMS, replace=False))
    groups = df[["store_id", "dept_id"]].drop_duplicates().astype(str).values.tolist()
    aggs = sorted(f"{d}_{s}" for s, d in groups)
    return aggs, items


def series_frame(df, sid, aggs):
    """Daily rows for one series: sales (NaN in the test window), calendar, price."""
    cols = ["d_num", "ds", "event_name_1", "snap"]
    if sid in aggs:
        dept, store = sid[:7], sid[8:]  # "FOODS_1_CA_1" -> "FOODS_1", "CA_1"
        sub = df[(df.dept_id == dept) & (df.store_id == store)]
        out = sub.groupby(cols, observed=True, dropna=False).y.sum().reset_index()
        out["sell_price"] = np.nan
    else:
        out = df[df.unique_id == sid][cols + ["y", "sell_price"]].copy()
    out = out.sort_values("d_num")
    out = out[out.d_num > LAST_TRAIN_D - HISTORY_DAYS]
    out.loc[out.d_num > LAST_TRAIN_D, "y"] = np.nan
    return out.reset_index(drop=True)


def build_prompt(frame, sid, aggs, blind):
    is_agg = sid in aggs
    if blind:
        what = ("total daily units for one department of one store" if is_agg
                else "daily units of one grocery item in one store")
        header = f"Series: {what} (identity hidden).\n"
    else:
        what = (f"total daily units of department {sid[:7]} in Walmart store {sid[8:]} (California)"
                if is_agg else f"daily units of item {sid.rsplit('_', 2)[0]} in Walmart store {sid[-4:]} (California)")
        header = f"Series: {what}.\n"

    weekday = frame.ds.dt.day_name().str[:3]
    rows = []
    for i, r in frame.iterrows():
        day = f"day {i + 1 - HISTORY_DAYS:+d}" if blind else r.ds.strftime("%Y-%m-%d")
        if blind:
            event = "holiday" if pd.notna(r.event_name_1) else ""
        else:
            event = r.event_name_1 if pd.notna(r.event_name_1) else ""
        price = "" if pd.isna(r.sell_price) else f"{r.sell_price:.2f}"
        sales = "?" if pd.isna(r.y) else str(int(r.y))
        rows.append(f"{day},{weekday.iat[i]},{event},{int(r.snap)},{price},{sales}")

    future_days = (f"days +1 to +{HORIZON}" if blind
                   else f"{frame.ds.iat[-HORIZON]:%Y-%m-%d} to {frame.ds.iat[-1]:%Y-%m-%d}")
    return (
        header
        + "Columns: date, weekday, event, snap (1 = food-stamp payment day), price, units sold.\n"
        + f"The last {HORIZON} rows ({future_days}) are the forecast period; units are '?'.\n"
        + "Return the forecast with 'day' numbered 1 to 28 in that order.\n\n"
        + "date,weekday,event,snap,price,units\n" + "\n".join(rows)
    )


def call_claude(client, prompt):
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"refused: {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("hit max_tokens")
    text = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    if len(data["forecast"]) != HORIZON:
        raise RuntimeError(f"got {len(data['forecast'])} days, expected {HORIZON}")
    data["usage"] = {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
    data["model"] = resp.model
    return data


def run_one(client, df, sid, aggs, cond):
    path = RAW / f"{cond}__{sid}.json"
    if path.exists():
        return "cached"
    frame = series_frame(df, sid, aggs)
    prompt = build_prompt(frame, sid, aggs, blind=(cond == "blind"))
    for attempt in range(3):
        try:
            data = call_claude(client, prompt)
            break
        except (RuntimeError, json.JSONDecodeError, KeyError) as e:
            if attempt == 2:
                return f"failed: {e}"
            time.sleep(2)
    data["dates"] = [d.strftime("%Y-%m-%d") for d in frame.ds.iloc[-HORIZON:]]
    path.write_text(json.dumps(data))
    return "ok"


def collect(aggs, items):
    """Turn cached JSON responses into one long table."""
    rows = []
    for cond in ["named", "blind"]:
        for sid in aggs + items:
            path = RAW / f"{cond}__{sid}.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            for d, f in zip(data["dates"], sorted(data["forecast"], key=lambda f: f["day"])):
                qs = np.maximum.accumulate([max(f[f"q{q}"], 0) for q in QUANTILES])
                rows.append({"unique_id": sid, "level": "store x dept" if sid in aggs else "item x store",
                             "condition": cond, "ds": pd.Timestamp(d), "Claude": max(f["mean"], 0),
                             **{f"q{q}": v for q, v in zip(QUANTILES, qs)}})
    return pd.DataFrame(rows)


def load_env_file():
    """Read ANTHROPIC_API_KEY from the project's .env file if it isn't already set."""
    path = ROOT / ".env"
    if "ANTHROPIC_API_KEY" in os.environ or not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key == "ANTHROPIC_API_KEY":
            os.environ[key] = value.strip().strip('"').strip("'")


def main(dry_run=False, limit=None):
    load_env_file()
    df = pd.read_parquet(PROCESSED / "sales_long.parquet",
                         columns=["unique_id", "dept_id", "store_id", "d_num", "ds", "y",
                                  "sell_price", "event_name_1", "snap"])
    df["unique_id"] = df.unique_id.astype(str)
    aggs, items = select_series(df)
    series = aggs + items
    if limit:
        series = aggs[:1] + items[: limit - 1]

    if dry_run:
        sid = items[0]
        for blind in (False, True):
            p = build_prompt(series_frame(df, sid, aggs), sid, aggs, blind)
            print(("BLIND" if blind else "NAMED") + " prompt, first and last lines:")
            lines = p.splitlines()
            print("\n".join(lines[:8] + ["..."] + lines[-4:]), "\n")
        print(f"{len(aggs)} aggregate + {len(items)} item series x 2 conditions = {2 * len(aggs + items)} calls")
        return

    RAW.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()
    jobs = [(sid, cond) for sid in series for cond in ["named", "blind"]]
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = {pool.submit(run_one, client, df, sid, aggs, cond): (sid, cond) for sid, cond in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            sid, cond = futures[fut]
            print(f"[{i}/{len(jobs)}] {cond:5s} {sid}: {fut.result()}", flush=True)

    out = collect(aggs, items)
    out.to_parquet(FORECASTS / "claude.parquet", index=False)
    usage = [json.loads(p.read_text())["usage"] for p in RAW.glob("*.json")]
    tin, tout = sum(u["input"] for u in usage), sum(u["output"] for u in usage)
    print(f"{out.unique_id.nunique()} series saved. Tokens: {tin:,} in, {tout:,} out "
          f"(about ${tin * 4e-6 + tout * 20e-6:.2f} at Opus 5.5 list prices)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    main(a.dry_run, a.limit)
