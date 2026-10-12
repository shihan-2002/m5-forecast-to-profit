# Forecast to Profit: Turning Walmart Demand Forecasts into Inventory Decisions

**Group 3:** Charlotte Zhu, Shihan Wang, Jing Chang, Rachel Liu
UCLA Anderson, Time Series Analysis and Forecasting (Dr. William Yu). Due Oct 26, 2026.

## Question
Does the most accurate demand forecast also make the most money?

Most forecasting projects stop at accuracy (MAE, RMSE). A store manager cares about
something else: how much to order. Ordering too little loses sales; ordering too much
wastes food. We forecast daily demand for every food item in Walmart's California
stores, turn each forecast into an order, and compare models on **profit** as well as
accuracy.

## Data
[M5 Forecasting competition](https://www.kaggle.com/competitions/m5-forecasting-accuracy)
(Walmart, 2011-01-29 to 2016-06-19), downloaded from Nixtla's public mirror of the same files.

Scope: **4 California stores x 1,437 FOODS items = 5,748 daily series**, with prices,
holidays/events, and SNAP (food-stamp) days.

- Training: d_1 to d_1941 (to 2016-05-22)
- Test: d_1942 to d_1969 (28 days, 2016-05-23 to 2016-06-19), the official M5 evaluation window. No model sees it during fitting or tuning.

## Models
| Family | Models | Notes |
|---|---|---|
| Benchmarks | Seasonal naive (7-day), 28-day moving average | |
| Classical | AutoETS, AutoARIMA (weekly season) | statsforecast, last 730 days |
| Intermittent demand | Croston (optimized), ADIDA | For items that often sell zero |
| Machine learning | LightGBM, one global model | Tweedie loss, lags of 28+ days, rolling means, price and calendar features. Rounds picked by early stopping on the last 28 *training* days. |
| AI foundation model | Chronos-Bolt (Amazon) | Zero-shot: never trained on our data. Outputs a full forecast distribution. |

## Evaluation
1. **Accuracy:** WRMSSE (the M5 metric) over six levels: total, store, dept, store x dept, item, item x store. Also MAE, RMSE and bias.
2. **Profit (newsvendor):** each day the store orders Q units per item. Food is treated as perishable (unsold units are written off at cost). With price p and gross margin m:
   `profit = p * min(Q, demand) - p(1-m) * Q`.
   The best order is the **m-quantile** of demand, so the right order depends on the margin, not just the point forecast. Ordering policies:
   - `point`: order the rounded point forecast (the common default)
   - `nb`: order the m-quantile of a negative binomial distribution centred on the forecast
   - `native`: Chronos's own predicted m-quantile
   Results are reported as a percentage of perfect-foresight profit, for margins from 20% to 80%.

## First results (Oct 12, one 28-day test window)
| Model | WRMSSE | MAE | Profit at 50% margin, quantile orders |
|---|---|---|---|
| LightGBM | **0.646** | 1.547 | $114.6k |
| AutoETS | 0.661 | 1.548 | **$118.5k** |
| Seasonal naive | 0.814 | 1.855 | $36.0k |
| AutoARIMA | 0.892 | 1.563 | $116.6k |
| Chronos (zero-shot) | 0.949 | **1.523** | $115.8k (own quantiles) |

1. **The most accurate model is not the most profitable.** LightGBM has the best WRMSSE, but AutoETS earns the most at 50-65% margins, and LightGBM is not the top earner at any margin below 80%. Chronos ranks 5th on WRMSSE but 1st on MAE, so the choice of metric changes the winner.
2. **The ordering rule matters far more than the model.** Ordering the point forecast loses money at low margins (about -$175k at a 20% margin). Ordering the margin-quantile breaks even. At a 35% margin it turns a $37k loss into a $39k profit. The gap between the best models is only a few thousand dollars.
3. **Chronos under-forecasts** (bias -0.24 units/day). That hurts its WRMSSE but helps when margins are thin, because it orders less and wastes less.
4. The differences between the top models are small and come from a single test window. A rolling backtest over several windows is needed before drawing firm conclusions.

## How to run
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p data/raw && curl -L -o data/raw/m5.zip https://github.com/Nixtla/m5-forecasts/raw/main/datasets/m5.zip
unzip data/raw/m5.zip -d data/raw     # raw data is not in the repo (about 450 MB)
cd src
../.venv/bin/python prep.py            # build data/processed (about 1 min)
../.venv/bin/python models_stat.py     # classical models (about 40 min on 10 cores)
../.venv/bin/python models_lgb.py      # LightGBM (about 10 min)
../.venv/bin/python models_chronos.py  # Chronos-Bolt (downloads about 200 MB of weights the first time)
../.venv/bin/python evaluate.py        # writes outputs/results/*.csv
```
Then open `notebooks/analysis.ipynb` for the charts.

## Project layout
```
data/raw/          M5 csv files (not committed)
data/processed/    CA/FOODS slice in long format
src/               pipeline scripts (config, prep, models_*, evaluate)
outputs/forecasts/ one parquet file per model family
outputs/results/   accuracy and profit tables
notebooks/         analysis and charts for the report and slides
```

## Still to do
- [ ] Streamlit dashboard: pick a margin, store and department, then compare models on profit vs accuracy
- [ ] Claude "demand-planning assistant" in the dashboard that explains why an order quantity was chosen
- [ ] Optional: hierarchical reconciliation (bottom-up vs MinT) at store and dept levels
- [ ] 10-slide deck and recorded demo
- [ ] Section on how we used AI tools (required by the brief)

## Suggested roles
| Person | Owns |
|---|---|
| A | Data and classical models, accuracy section |
| B | LightGBM and Chronos, model comparison |
| C | Newsvendor/profit analysis, business story |
| D | Dashboard, Claude assistant, slides and demo |

## Timeline
| Dates | Milestone |
|---|---|
| Oct 12-14 | Pipeline runs end to end (done: first pass) |
| Oct 15-18 | Review results, improve models, sensitivity checks (salvage value, carry-over) |
| Oct 19-22 | Dashboard and Claude assistant |
| Oct 23-25 | Slides, report/README, demo recording |
| Oct 26 | Submit |

## Limitations
- Demand is measured by sales, so stockout days look like zero demand.
- Perishable, no-carry-over inventory is a simplification. A sensitivity check with salvage value is planned.
- Chronos may have seen M5 during pre-training, since M5 is public. Check the Chronos paper's list of training data and report it.
