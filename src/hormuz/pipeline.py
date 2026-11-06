"""Rebuild processed data from the cached downloads, and refresh the newest months."""
import pandas as pd

from .config import PROCESSED
from .crossings import daily_counts, detect
from .gfw import load_presence, pull_month


def build_daily():
    """Detect crossings from all cached hourly presence and write daily_crossings.csv."""
    west, east = load_presence("west"), load_presence("east")
    pres = pd.concat([west.assign(box="west"), east.assign(box="east")])
    pres["day"] = pd.to_datetime(pres["date"]).dt.normalize()
    cov = pres.groupby("day").agg(vessel_hours=("hours", "sum"), vessels=("vesselId", "nunique"))
    cross = detect(west, east)
    daily = daily_counts(cross, cov.index.min(), cov.index.max())
    daily = daily.join(cov, how="left").fillna({"vessel_hours": 0, "vessels": 0})
    PROCESSED.mkdir(parents=True, exist_ok=True)
    cross.to_parquet(PROCESSED / "crossings.parquet", index=False)
    daily.to_csv(PROCESSED / "daily_crossings.csv")
    return daily


def refresh_recent_gfw(months_back=2, log=print):
    """Re-download the last `months_back` months for both strait boxes (GFW keeps adding days)."""
    today = pd.Timestamp.today()
    months = [p.strftime("%Y-%m") for p in pd.period_range(today - pd.DateOffset(months=months_back - 1), today, freq="M")]
    for m in months:
        for box in ("west", "east"):
            log(f"GFW {m} {box}: {pull_month(box, m, refresh=True)} rows")
