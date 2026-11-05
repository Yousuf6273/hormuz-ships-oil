"""Data feasibility summary: GFW date range, daily tanker crossings, gaps, and price alignment.

Run after scripts/pull_gfw.py and scripts/pull_prices.py. Writes:
  data/processed/daily_crossings.csv
  data/processed/daily_coverage.csv
  figures/feasibility_monthly.png
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.config import PROCESSED, TEST_START, TRAIN_END  # noqa: E402
from hormuz.crossings import daily_counts, detect  # noqa: E402
from hormuz.gfw import load_presence  # noqa: E402
from hormuz.prices import load_prices  # noqa: E402

west, east = load_presence("west"), load_presence("east")
print(f"GFW hourly rows: west={len(west):,} east={len(east):,}")

# --- coverage: is anything recorded at all in the strait each day? ---
pres = pd.concat([west.assign(box="west"), east.assign(box="east")])
pres["day"] = pd.to_datetime(pres["date"]).dt.normalize()
cov = pres.groupby("day").agg(vessel_hours=("hours", "sum"), vessels=("vesselId", "nunique"))

# --- crossings ---
cross = detect(west, east)
first_day, last_day = cov.index.min(), cov.index.max()
daily = daily_counts(cross, first_day, last_day)
daily = daily.join(cov, how="left").fillna({"vessel_hours": 0, "vessels": 0})
PROCESSED.mkdir(parents=True, exist_ok=True)
cross.to_parquet(PROCESSED / "crossings.parquet", index=False)
daily.to_csv(PROCESSED / "daily_crossings.csv")
print(f"Crossings detected: {len(cross):,}  from {first_day.date()} to {last_day.date()}")

# --- per-year table ---
daily["year"] = daily.index.year
daily["no_data"] = daily["vessel_hours"] == 0
tbl = daily.groupby("year").agg(
    days=("tanker_total", "size"),
    no_data_days=("no_data", "sum"),
    tanker_per_day=("tanker_total", "mean"),
    tanker_zero_days=("tanker_total", lambda s: int((s == 0).sum())),
    cargo_per_day=("cargo_total", "mean"),
    fishing_per_day=("fishing_total", "mean") if "fishing_total" in daily else ("tanker_total", lambda s: 0),
    vessels_seen_per_day=("vessels", "mean"),
).round(1)
print("\nPer year (UTC days):")
print(tbl.to_string())

# --- longest runs of no-data days ---
nd = daily["no_data"].astype(int)
runs = (nd.diff() != 0).cumsum()
gaps = daily[daily["no_data"]].groupby(runs[daily["no_data"]]).apply(
    lambda g: pd.Series({"start": g.index.min().date(), "end": g.index.max().date(), "days": len(g)}))
if len(gaps):
    print("\nLongest no-data gaps:")
    print(gaps.sort_values("days", ascending=False).head(8).to_string(index=False))
else:
    print("\nNo days without any GFW data in the boxes.")

# --- around the March 2026 disruption ---
m = daily.loc["2026-01-01":"2026-05-31", ["tanker_total", "cargo_total", "vessels"]]
print("\nWeekly average around the 2026 disruption:")
print(m.resample("W").mean().round(1).to_string())

# --- price alignment ---
for source in ("yahoo", "fred"):
    try:
        px = load_prices(source)
    except FileNotFoundError as e:
        print(f"\n{source}: {e}")
        continue
    b = px["brent"].dropna()
    days = b.index[(b.index >= first_day) & (b.index <= last_day)]
    have = daily.reindex(days)["vessel_hours"].fillna(0) > 0
    print(f"\nPrices from {source}: Brent days in GFW range = {len(days)}, with ship data = {int(have.sum())}")
    print(f"  training days (to {TRAIN_END}): {int(have[days <= TRAIN_END].sum())}, "
          f"test days (from {TEST_START}): {int(have[days >= TEST_START].sum())}")
    print(f"  other series coverage on Brent days: " +
          ", ".join(f"{c}={px.reindex(days)[c].notna().mean():.1%}" for c in px.columns if c != "brent"))

# --- chart ---
mon = daily[["tanker_total", "cargo_total"]].resample("MS").mean()
fig, ax = plt.subplots(figsize=(11, 4.5))
ax.plot(mon.index, mon["tanker_total"], label="Tanker crossings / day", color="#1f6f8b")
ax.plot(mon.index, mon["cargo_total"], label="Cargo crossings / day", color="#c9842b", alpha=0.8)
ax.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-03-31"), color="#d64545", alpha=0.15, label="Mar 2026 restrictions")
ax.axvline(pd.Timestamp(TEST_START), color="grey", ls="--", lw=1)
ax.text(pd.Timestamp(TEST_START), ax.get_ylim()[1] * 0.95, " test period ->", color="grey", va="top")
try:
    px = load_prices("yahoo") if (ROOT / "data/raw/prices/yahoo_brent.parquet").exists() else load_prices("fred")
    ax2 = ax.twinx()
    br = px["brent"].resample("MS").mean().loc[mon.index.min():]
    ax2.plot(br.index, br, color="black", lw=1, alpha=0.6, label="Brent ($/bbl, right)")
    ax2.set_ylabel("Brent $/bbl")
except FileNotFoundError:
    pass
ax.set_ylabel("crossings per day (monthly average)")
ax.set_title("Strait of Hormuz crossings detected in Global Fishing Watch AIS data")
ax.legend(loc="upper left", fontsize=8)
fig.text(0.01, 0.01, "Source: Global Fishing Watch AIS vessel presence (CC BY-NC 4.0); prices: Yahoo Finance / FRED",
         fontsize=7, color="grey")
fig.tight_layout()
(ROOT / "figures").mkdir(exist_ok=True)
fig.savefig(ROOT / "figures/feasibility_monthly.png", dpi=150)
print("\nSaved figures/feasibility_monthly.png")
