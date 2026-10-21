# Can AI Foundation Models Beat LightGBM? Forecasting Walmart Demand

**Group 3:** Charlotte Zhu, Shihan Wang, Jing Chang, Rachel Liu
UCLA Anderson, Time Series Analysis and Forecasting (Dr. William Yu). Due Oct 26, 2026.

## Research question
**Can modern AI foundation models produce more accurate and computationally efficient retail
demand forecasts than traditional statistical and machine-learning methods?**

LightGBM dominated the M5 forecasting competition. We test it against a classical time series
model and two AI foundation models that need no training on our data.

- **Part 1 (done):** forecast accuracy and computational efficiency.
- **Part 2 (planned):** do the forecasts lead to better inventory decisions? (newsvendor ordering)

Report: [Can AI Foundation Models Beat LightGBM? (Part 1)](https://claude.ai/code/artifact/fbff8ef5-6e2a-41bb-81d6-400296d70f3e)

## Data
[M5 Forecasting competition](https://www.kaggle.com/competitions/m5-forecasting-accuracy)
(Walmart, 2011-01-29 to 2016-06-19), downloaded from Nixtla's public mirror of the same files.

Scope: **4 California stores x 1,437 FOODS items = 5,748 daily series**, with prices,
holidays/events, and SNAP (food-stamp) days.

- Training: d_1 to d_1941 (to 2016-05-22)
- Test: d_1942 to d_1969 (28 days, 2016-05-23 to 2016-06-19), the official M5 evaluation window. No model sees it during fitting or tuning.

## Models
| Model | Family | Trained on our data? | Notes |
|---|---|---|---|
| AutoARIMA | Classical statistics | Yes, one model per series | statsforecast, weekly season, last 730 days |
| LightGBM | Machine learning | Yes, one global model | Tweedie loss, lags of 28+ days, rolling means, price and calendar features; rounds by early stopping on the last 28 training days |
| Chronos-Bolt (small) | AI foundation model for time series (Amazon) | No (zero-shot) | M5 was held out of its training data |
| Claude Opus 5.5 | General-purpose LLM (Anthropic) | No (zero-shot) | 112 series only (12 store x dept totals + 100 sampled items), each run "named" and "blind" |
| Seasonal naive | Benchmark | No | Same weekday last week |

## Part 1 results (one 28-day test window)
| Finding | Numbers |
|---|---|
| LightGBM is most accurate across all 5,748 series | WRMSSE 0.646 vs AutoARIMA 0.892, Chronos 0.949, seasonal naive 0.814 |
| Its edge is at aggregate levels; at item level all models are close | Each of the three main models is best on about a third of items |
| Claude is most accurate on the 12 store x dept totals | WRMSSE 0.58, about 8% better than the next model |
| Fitting totals directly matters as much as the model | AutoARIMA 0.900 -> 0.644, Chronos 0.969 -> 0.637 when fitted on totals instead of summed |
| No sign Claude recalls the public data | Named 0.579 vs blind 0.583 on totals |
| Chronos is by far the most efficient | 10 s for all series vs LightGBM 80 s, AutoARIMA 39 min, Claude about 3.7 h and $347 (estimated) |

Caveats: one test window, and Claude on 112 of 5,748 series. A rolling backtest is the next step.

## How to run
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p data/raw && curl -L -o data/raw/m5.zip https://github.com/Nixtla/m5-forecasts/raw/main/datasets/m5.zip
unzip data/raw/m5.zip -d data/raw     # raw data is not in the repo (about 450 MB)
cd src
../.venv/bin/python prep.py              # build data/processed (about 1 min)
../.venv/bin/python models_stat.py       # AutoARIMA and other classical models (about 40-50 min on 10 cores)
../.venv/bin/python models_lgb.py        # LightGBM (about 1-2 min)
../.venv/bin/python models_chronos.py    # Chronos-Bolt (downloads about 200 MB of weights the first time)
../.venv/bin/python evaluate.py          # accuracy tables -> outputs/results/
../.venv/bin/python models_direct_agg.py # AutoARIMA, Chronos, naive fitted directly on the 12 totals
../.venv/bin/python models_claude.py     # Claude forecasts (needs an API key; about $14)
../.venv/bin/python evaluate_claude.py   # Claude comparison -> outputs/results/claude_accuracy.csv
```
Claude needs an Anthropic API key in a `.env` file at the project root (`ANTHROPIC_API_KEY="..."`).
The file is git-ignored. Saved Claude responses are in `outputs/claude_raw/`, so you can skip
`models_claude.py` and still run `evaluate_claude.py`.

Then open `notebooks/01_forecast_accuracy.ipynb`; it rebuilds every chart into `outputs/figures/part1/`.

**Dashboard (Shelf Signal v2):** live at https://shihan-2002.github.io/shelf-signal-dashboard/ (deployed from the `shelf-signal-dashboard` repo; after rebuilding, copy `docs/index.html` there as `index.html` and push).
```bash
cd src && ../.venv/bin/python models_ensemble.py && ../.venv/bin/python export_dashboard.py   # writes docs/index.html
```
`docs/index.html` is a single self-contained page (data inline, Chart.js from a CDN): open it in any browser.
It extends our teammate's [Shelf Signal](https://jing0712.github.io/shelf-signal/) with this project's models.
Template: `dashboard/template.html`. Once the repo is public, GitHub Pages can serve `docs/`.

**Final report (R / Quarto):**
```bash
cd src && ../.venv/bin/python export_report_data.py   # writes outputs/results/report/*.csv
cd ../report && quarto render report.qmd               # report.html and report.pdf (needs R + tidyverse)
```
`report/report.qmd` is written in R and reads only the CSVs in `outputs/results/report/`.
In RStudio, open it and click Render.

## Project layout
```
data/raw/            M5 csv files (not committed)
data/processed/      CA/FOODS slice in long format (not committed)
src/                 pipeline scripts (config, prep, models_*, evaluate*)
outputs/forecasts/   one parquet file per model family
outputs/claude_raw/  every Claude response (JSON), for reproducibility
outputs/results/     accuracy, Claude comparison and timing tables
outputs/figures/     charts (part1/ = forecast accuracy)
notebooks/           01_forecast_accuracy.ipynb (Part 1); analysis.ipynb (early profit draft, Part 2)
```

## Next steps
- [ ] Rolling-origin backtest over 3-4 earlier 28-day windows
- [ ] Confirm in the M5 paper the share of top teams that used LightGBM
- [ ] Part 2: each model's own uncertainty (ARIMA intervals, LightGBM quantile regression, Chronos and Claude quantiles), scored by pinball loss and profit
- [ ] 10-slide deck and recorded demo

## Timeline
| Dates | Milestone |
|---|---|
| Oct 12-20 | Part 1 built and written up (done) |
| Oct 21-23 | Rolling backtest; Part 2 if time allows |
| Oct 23-25 | Slides, final report, demo recording |
| Oct 26 | Submit |

## Limitations
- One 28-day test window; Claude tested on 112 series.
- Demand is measured by sales, so stock-out days look like zero demand.
- LightGBM uses one fixed setting; M5 winners tuned and ensembled many models.
- Claude's forecasts can vary slightly between runs.
