# Can AI Foundation Models Beat Traditional Statistical Models? Forecasting Walmart Demand

**Group 3:** Charlotte Zhu, Shihan Wang, Jing Chang, Rachel Liu
UCLA Anderson, Time Series Analysis and Forecasting (Dr. William Yu), fall 2026.

## Research question
**Can modern AI foundation models produce more accurate and computationally efficient retail
demand forecasts than traditional statistical and machine-learning methods?**

We compare classical time series models and LightGBM, the machine-learning method that dominated
the M5 competition, against two AI models that need no training on our data: Chronos (a time
series foundation model) and Claude (a general-purpose LLM). We close with a business insight:
the best order quantity is a margin-dependent quantile of demand (the newsvendor problem), not the
forecast itself.

## Deliverables
| | |
|---|---|
| Final report | [`report/report.pdf`](report/report.pdf) (HTML: `report/report.html`, source: `report/report.qmd`) |
| Slide deck | [`presentation/Group3_Forecasting_Presentation.pptx`](presentation/Group3_Forecasting_Presentation.pptx) and [PDF](presentation/Group3_Forecasting_Presentation.pdf) |
| Interactive dashboard | **Shelf Signal**: https://jing0712.github.io/shelf-signal/#planner (source: `docs/index.html`) |
| Code | `src/` (Python pipeline) and `report/report.qmd` (R) |

## Data
[M5 Forecasting competition](https://www.kaggle.com/competitions/m5-forecasting-accuracy)
(Walmart, 2011-01-29 to 2016-06-19), downloaded from Nixtla's public mirror of the same files.

Scope: **4 California stores x 1,437 FOODS items = 5,748 daily item-store series**, with prices,
holidays/events, and SNAP (food-stamp) days.

- Training: d_1 to d_1941 (to 2016-05-22)
- Test: d_1942 to d_1969 (28 days, 2016-05-23 to 2016-06-19), the official M5 evaluation window. No model sees it during fitting or tuning.

## Models
| Model | Family | Trained on our data? | Notes |
|---|---|---|---|
| AutoETS | Classical statistics | Yes, one model per series | statsforecast, weekly season, last 730 days |
| AutoARIMA | Classical statistics | Yes, one model per series | statsforecast, weekly season, last 730 days |
| LightGBM | Machine learning | Yes, one global model | Tweedie loss, lags of 28+ days, rolling means, price and calendar features; rounds by early stopping on the last 28 training days |
| Ensemble | Combination | No extra fitting | Unweighted average of AutoETS and LightGBM |
| Chronos-Bolt (small) | AI foundation model for time series (Amazon) | No (zero-shot) | Last 512 days; nine quantiles per day; M5 held out of its training data |
| Claude Opus 5.5 | General-purpose LLM (Anthropic) | No (zero-shot) | 112 series (12 store x dept totals + 100 sampled items), each run "named" and "blind" |
| Seasonal naive | Benchmark | No | Same weekday last week |

## Results (one 28-day test window)
| Finding | Numbers |
|---|---|
| Traditional methods lead on accuracy | WRMSSE: ensemble 0.604, LightGBM 0.646, AutoETS 0.661; seasonal naive 0.814, AutoARIMA 0.892, Chronos 0.949 (lower is better) |
| The gaps are at aggregate levels; single items are close | No model is best on more than about a third of items |
| Chronos is by far the fastest | 10 s for all series with no training, vs LightGBM 80 s, AutoETS 86 s, AutoARIMA 39 min |
| Chronos runs low on sparse items | Right weekly shape, but its total is about 11% low, mostly from items that rarely sell |
| Claude matches the best traditional approach on totals | WRMSSE 0.579 (named) / 0.583 (blind) on the 12 store x dept totals, level with the ensemble |
| Fitting totals directly matters as much as the model | AutoARIMA 0.900 -> 0.644, Chronos 0.969 -> 0.637 when fitted on totals instead of summed |
| No sign Claude recalls the public data | Named and blind forecasts are equally accurate (this cannot fully rule out contamination) |
| Accuracy is not profit | In a newsvendor test, the more accurate model earned significantly more only at high margins |

**Answer: not yet on accuracy, yes on speed.**

## How to run
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p data/raw && curl -L -o data/raw/m5.zip https://github.com/Nixtla/m5-forecasts/raw/main/datasets/m5.zip
unzip data/raw/m5.zip -d data/raw     # raw data is not in the repo (about 450 MB)
cd src
../.venv/bin/python prep.py                       # build data/processed (about 1 min)
../.venv/bin/python models_stat.py                # AutoETS, AutoARIMA, seasonal naive (about 40-50 min on 10 cores)
../.venv/bin/python models_lgb.py                 # LightGBM (about 1-2 min)
../.venv/bin/python models_chronos.py             # Chronos-Bolt (downloads about 200 MB of weights the first time)
../.venv/bin/python models_ensemble.py            # AutoETS + LightGBM average
../.venv/bin/python evaluate.py                   # accuracy tables -> outputs/results/
../.venv/bin/python models_direct_agg.py          # models fitted directly on the 12 totals
../.venv/bin/python models_claude.py              # Claude forecasts (needs an API key; about $14)
../.venv/bin/python evaluate_claude.py            # Claude comparison -> outputs/results/claude_accuracy.csv
../.venv/bin/python export_report_data.py         # CSVs for the report -> outputs/results/report/
../.venv/bin/python export_chronos_diagnostics.py # Chronos bias by volume and quantile calibration
../.venv/bin/python export_dashboard.py           # dashboard -> docs/index.html
cd ../report && quarto render report.qmd          # report.html and report.pdf (needs R + tidyverse)
```
Claude needs an Anthropic API key in a `.env` file at the project root (`ANTHROPIC_API_KEY="..."`).
The file is git-ignored. Saved Claude responses are in `outputs/claude_raw/`, so you can skip
`models_claude.py` and still run `evaluate_claude.py`.

The dashboard is a single self-contained page (data inline, Chart.js from a CDN): open
`docs/index.html` in any browser. Its template is `dashboard/template.html`. It extends our
teammate's original Shelf Signal ([code](https://github.com/Jing0712/shelf-signal)) with this project's models.

## Project layout
```
data/raw/            M5 csv files (not committed)
data/processed/      CA/FOODS slice in long format (not committed)
src/                 pipeline scripts (config, prep, models_*, evaluate*, export_*)
outputs/forecasts/   one parquet file per model family
outputs/claude_raw/  every Claude response (JSON), for reproducibility
outputs/results/     accuracy, Claude comparison and timing tables; report/ holds the report's CSVs
dashboard/           dashboard template
docs/                built dashboard (index.html)
report/              final report (Quarto, R)
presentation/        slide deck (pptx and PDF)
notebooks/           exploratory notebooks
```

## Limitations
- One 28-day test window; close rankings could change in another month.
- Claude tested on 112 series; the blind test cannot fully rule out that it saw this public data.
- Demand is measured by sales, so stock-out days look like zero demand.
- LightGBM uses one fixed setting; M5 winners tuned and ensembled many models.
- The newsvendor analysis is exploratory (zero salvage value, assumed demand distribution).

## Use of AI tools
Chronos and Claude are forecasting models under test. We also used Claude Code to write the
pipeline, evaluation code, charts, dashboard and slides, and to draft the report; we reviewed and
corrected its output, and every number in the report is read from the pipeline's output files.
