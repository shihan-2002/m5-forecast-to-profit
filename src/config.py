"""Shared paths and project settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FORECASTS = ROOT / "outputs" / "forecasts"
FIGURES = ROOT / "outputs" / "figures"

# Scope: California stores, FOODS category
STATE = "CA"
CATEGORY = "FOODS"

# Forecast setup: train on d_1..d_1941, test on d_1942..d_1969 (the official M5 evaluation window)
HORIZON = 28
LAST_TRAIN_D = 1941
SEASON = 7

# Statistical models only see the most recent history (keeps AutoARIMA fast)
STAT_HISTORY_DAYS = 730

# Margins swept in the inventory simulation (gross margin = (price - cost) / price)
MARGINS = [0.2, 0.35, 0.5, 0.65, 0.8]
