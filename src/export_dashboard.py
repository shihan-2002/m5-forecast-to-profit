"""Build the Shelf Signal v2 dashboard: one self-contained HTML page with its data inline.

Series included:
  - every aggregate level: total (4 stores), each store, each department, each store x dept
  - items: Claude's 100 sampled item-store series, plus the 15 store-CA_1 items from our
    teammate's original Shelf Signal dashboard
For each series: the last 56 training days, the 28 test days, every model's forecast,
and per-model MAE and RMSSE on the test window. Item series also carry price and the
negative binomial dispersion used by the order planner.

Run after evaluate.py, evaluate_claude.py, models_direct_agg.py, models_ensemble.py and
export_report_data.py.
Output: docs/index.html (template: dashboard/template.html)
"""
import json

import numpy as np
import pandas as pd

from config import PROCESSED, FORECASTS, ROOT, LAST_TRAIN_D

RESULTS = ROOT / "outputs" / "results"
REPORT = RESULTS / "report"
HISTORY = 56
MODELS = ["SeasonalNaive", "AutoARIMA", "AutoETS", "LightGBM", "Ensemble", "Chronos"]
SHELF_SIGNAL_ITEMS = ["FOODS_1_018", "FOODS_1_085", "FOODS_1_099", "FOODS_1_161", "FOODS_1_218",
                      "FOODS_2_019", "FOODS_2_197", "FOODS_2_244", "FOODS_2_276", "FOODS_2_371",
                      "FOODS_3_064", "FOODS_3_120", "FOODS_3_252", "FOODS_3_282", "FOODS_3_586"]


def rmsse(y_train, y_test, f):
    y_train = np.asarray(y_train, float)
    nz = np.nonzero(y_train)[0]
    if len(nz) == 0:
        return None
    scale = np.mean(np.diff(y_train[nz[0]:]) ** 2)
    if scale == 0:
        return None
    return float(np.sqrt(np.mean((np.asarray(f) - np.asarray(y_test)) ** 2) / scale))


def r(x, d=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def main():
    sales = pd.read_parquet(PROCESSED / "sales_long.parquet",
                            columns=["unique_id", "item_id", "dept_id", "store_id", "d_num", "ds", "y", "sell_price"])
    for c in ["unique_id", "item_id", "dept_id", "store_id"]:
        sales[c] = sales[c].astype(str)
    joined = pd.read_parquet(RESULTS / "joined.parquet")
    joined["unique_id"] = joined.unique_id.astype(str)
    claude = pd.read_parquet(FORECASTS / "claude.parquet")
    direct = pd.read_parquet(FORECASTS / "direct_agg.parquet")
    test_dates = sorted(joined.ds.unique())
    first_hist = LAST_TRAIN_D - HISTORY

    def pack(sid, label, level, group, hist_frame, test_frame, fcs, extra=None):
        """hist_frame/test_frame: y by d_num; fcs: {model: array of 28}."""
        tr = hist_frame
        y_hist = tr[tr.d_num > first_hist].sort_values("d_num").y.to_numpy()
        y_test = test_frame.sort_values("ds").y.to_numpy()
        metrics = {m: {"mae": r(np.mean(np.abs(np.asarray(f) - y_test)), 3),
                       "rmsse": r(rmsse(tr.sort_values("d_num").y.to_numpy(), y_test, f), 3)} for m, f in fcs.items()}
        out = {"id": sid, "label": label, "level": level, "group": group,
               "hist": [r(v, 1) for v in y_hist], "actual": [r(v, 1) for v in y_test],
               "fc": {m: [r(v, 2) for v in f] for m, f in fcs.items()}, "metrics": metrics}
        if extra:
            out.update(extra)
        return out

    series = []
    # ---- aggregates (forecasts = sums of item forecasts; store x dept also direct fits and Claude)
    train_all = sales[sales.d_num <= LAST_TRAIN_D]
    levels = [("Total", [], "All 4 California stores"), ("Store", ["store_id"], None),
              ("Department", ["dept_id"], None), ("Store x dept", ["store_id", "dept_id"], None)]
    for level, keys, fixed_label in levels:
        k = keys or ["_all"]
        tr = train_all.assign(_all="all").groupby(k + ["d_num"]).y.sum().reset_index()
        te = joined.assign(_all="all").groupby(k + ["ds"])[["y"] + MODELS].sum().reset_index()
        for key, g in te.groupby(k, observed=True):
            key = key if isinstance(key, tuple) else (key,)
            mask = np.logical_and.reduce([tr[c] == v for c, v in zip(k, key)])
            fcs = {m: g.sort_values("ds")[m].to_numpy() for m in MODELS}
            label = fixed_label or " · ".join(key)
            sid = "_".join(key) if keys else "TOTAL"
            if level == "Store x dept":
                store, dept = key
                did = f"{dept}_{store}"
                d = direct[direct.unique_id == did].sort_values("ds")
                for m in ["AutoARIMA", "AutoETS", "Chronos"]:
                    fcs[f"{m} (direct)"] = d[m].to_numpy()
                for cond in ["blind", "named"]:
                    c = claude[(claude.unique_id == did) & (claude.condition == cond)].sort_values("ds")
                    if len(c):
                        fcs[f"Claude ({cond})"] = c.Claude.to_numpy()
                sid = did
            series.append(pack(sid, label, level, None, tr[mask], g, fcs))

    # ---- items
    claude_items = sorted(claude.loc[claude.level == "item x store", "unique_id"].unique())
    shelf = [f"{i}_CA_1" for i in SHELF_SIGNAL_ITEMS]
    items = list(dict.fromkeys(shelf + claude_items))
    phi = joined.groupby("unique_id").phi.first()
    for uid in items:
        tr = train_all[train_all.unique_id == uid]
        te = joined[joined.unique_id == uid].sort_values("ds")
        fcs = {m: te[m].to_numpy() for m in MODELS}
        for cond in ["blind", "named"]:
            c = claude[(claude.unique_id == uid) & (claude.condition == cond)].sort_values("ds")
            if len(c):
                fcs[f"Claude ({cond})"] = c.Claude.to_numpy()
        group = "Shelf Signal items (store CA_1)" if uid in shelf else "Claude sample items"
        if uid in shelf and uid in claude_items:
            group = "Shelf Signal items (store CA_1)"
        series.append(pack(uid, f"{uid[:-5]} · {uid[-4:]}", "Item", group, tr, te, fcs,
                           {"price": [r(v, 2) for v in te.sell_price.to_numpy()], "phi": r(phi.get(uid, 1.5), 3),
                            "in_claude": uid in claude_items}))

    # ---- Claude reasoning text
    reasoning = {}
    for p in sorted((ROOT / "outputs" / "claude_raw").glob("*.json")):
        cond, sid = p.stem.split("__", 1)
        reasoning.setdefault(sid, {})[cond] = json.loads(p.read_text()).get("reasoning", "")

    # ---- global tables
    acc = pd.read_csv(RESULTS / "accuracy.csv", index_col=0)
    acc = acc.loc[["Ensemble", "LightGBM", "AutoETS", "SeasonalNaive", "AutoARIMA", "Chronos"]]
    by_level = pd.read_csv(RESULTS / "accuracy_by_level.csv", index_col=0)
    timing = pd.read_csv(RESULTS / "timing.csv")
    claude_acc = pd.read_csv(RESULTS / "claude_accuracy.csv")
    best = pd.read_csv(REPORT / "item_best_share.csv")
    weekly = pd.read_csv(REPORT / "weekly_sales.csv")
    weekday = pd.read_csv(REPORT / "weekday_index.csv")
    facts = pd.read_csv(REPORT / "data_facts.csv").iloc[0]
    boot = pd.read_csv(REPORT / "newsvendor_bootstrap.csv")

    data = {
        "test_dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in test_dates],
        "hist_days": HISTORY,
        "series": series,
        "reasoning": reasoning,
        "accuracy": [{"model": m, **{k: r(v, 3) for k, v in row.items()}} for m, row in acc.iterrows()],
        "by_level": {"levels": list(by_level.index), **{m: [r(v, 3) for v in by_level[m]]
                     for m in ["Ensemble", "LightGBM", "AutoETS", "AutoARIMA", "Chronos", "SeasonalNaive"]}},
        "timing": timing.to_dict(orient="records"),
        "claude_accuracy": [{k: (r(v, 3) if isinstance(v, float) else v) for k, v in row.items()}
                            for row in claude_acc.to_dict(orient="records")],
        "best_share": best.to_dict(orient="records"),
        "weekly": {"week": weekly.week.tolist(), "units": weekly.units.round(0).tolist()},
        "weekday": weekday.to_dict(orient="records"),
        "facts": {"snap_lift": r(facts.snap_lift, 3), "median_zero_share": r(facts.median_zero_share, 3)},
        "bootstrap": boot.round(1).to_dict(orient="records"),
    }
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    template = (ROOT / "dashboard" / "template.html").read_text()
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(template.replace("/*__DATA__*/null", payload))
    print(f"{len(series)} series ({len(items)} items), {out.stat().st_size / 1e6:.2f} MB -> {out}")


if __name__ == "__main__":
    main()
