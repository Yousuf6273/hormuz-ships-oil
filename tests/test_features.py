"""Checks that ship variables only use data up to the day before each trading day."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hormuz.features import ship_features  # noqa: E402


def _daily():
    days = pd.date_range("2025-01-01", "2025-03-31", freq="D")
    d = pd.DataFrame({"tanker_total": 10.0, "vessel_hours": 100.0}, index=days)
    d.loc["2025-03-07", "tanker_total"] = 40  # Friday
    d.loc["2025-03-08", "tanker_total"] = 70  # Saturday
    d.loc["2025-03-10", "tanker_total"] = 1000  # Monday: must NOT be visible on Monday
    return d


def test_monday_uses_friday_to_sunday_only():
    trade = pd.bdate_range("2025-02-10", "2025-03-14")
    f = ship_features(_daily(), trade, "tanker_total")
    # Monday 10 Mar: window = Fri 7, Sat 8, Sun 9 -> mean (40 + 70 + 10) / 3 = 40
    assert f.loc["2025-03-10", "tanker_total_level"] == 40
    # Tuesday 11 Mar: window = Mon 10 only -> 1000 (now visible)
    assert f.loc["2025-03-11", "tanker_total_level"] == 1000
    # Shock on Monday compares 40 with the 28 days before Friday (all 10s)
    assert np.isclose(f.loc["2025-03-10", "tanker_total_shock"], np.log1p(40) - np.log1p(10))


def test_no_data_days_are_unknown_not_zero():
    d = _daily()
    d.loc["2025-03-12", "vessel_hours"] = 0
    trade = pd.bdate_range("2025-02-10", "2025-03-14")
    f = ship_features(d, trade, "tanker_total")
    assert np.isnan(f.loc["2025-03-13", "tanker_total_level"])
