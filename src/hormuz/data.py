"""Load the inputs used by the analysis, with the sources fixed in HYPOTHESES.md (Deviations, 2026-11-06)."""
import pandas as pd

from .config import PROCESSED
from .prices import load_prices, settled

SAMPLE_START = "2022-01-01"


def main_prices():
    """Brent and VIX from Yahoo; S&P 500 and WTI from FRED. Only settled closes (no live prices from today)."""
    y, f = load_prices("yahoo"), load_prices("fred")
    return settled(pd.concat([y["brent"], f["wti"], f["sp500"], y["vix"]], axis=1, sort=True))


def fred_brent_prices():
    """Robustness: FRED Brent spot instead of Yahoo Brent futures."""
    p = main_prices()
    p["brent"] = load_prices("fred")["brent"]
    return p


def daily_crossings():
    return pd.read_csv(PROCESSED / "daily_crossings.csv", index_col=0, parse_dates=True)


def analysis_table():
    return pd.read_csv(PROCESSED / "analysis_table.csv", index_col=0, parse_dates=True)
