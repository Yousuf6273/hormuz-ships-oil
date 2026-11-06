"""Extension (exploratory, NOT pre-registered): "dark ships" seen by satellite radar.

Sentinel-1 radar sees ships whether or not they broadcast AIS. Global Fishing Watch matches each radar
detection to AIS; unmatched detections are "dark". If tankers kept crossing after March 2026 with AIS
switched off, radar should show far more traffic than our AIS crossing count.

Radar only covers the strait on satellite-pass days (every few days), so results are per pass.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.data import SAMPLE_START, daily_crossings  # noqa: E402
from hormuz.gfw import load_sar  # noqa: E402
from hormuz.plotstyle import TANKER, TEXT_2, THIRD, plt, shade_disruptions, source_note  # noqa: E402

pd.set_option("display.width", 160)
MIN_PASS = 10  # a day counts as a satellite pass if radar saw at least this many ships (drops swath-edge slivers)
OTHER_DARK = "#a8a6a0"
PERIODS = [("2025 (base)", "2025-01-01", "2025-12-31"), ("Jan–Feb 2026", "2026-01-01", "2026-02-27"),
           ("Mar 2026", "2026-03-01", "2026-03-31"), ("Apr–Jun 2026", "2026-04-01", "2026-06-30"),
           ("Jul 2026 → latest", "2026-07-01", None)]

s = load_sar()
s["date"] = pd.to_datetime(s["date"])
s = s[s["date"] >= SAMPLE_START]
day = s.pivot_table(index="date", columns="kind", values="detections", aggfunc="sum", fill_value=0)
day["ais_tanker"] = s[(s["kind"] == "ais") & (s["geartype"] == "tanker")].groupby("date")["detections"].sum()
day = day.fillna(0)
day["dark_other"] = day["dark"] - day["dark_nonfishing"]
day["total"] = day["ais"] + day["dark"]
passes = day[day["total"] >= MIN_PASS].copy()
passes.to_csv(ROOT / "data/processed/sar_passes.csv")
print(f"Satellite passes {passes.index.min():%Y-%m-%d} → {passes.index.max():%Y-%m-%d}: {len(passes)} "
      f"(per year: {passes.groupby(passes.index.year).size().to_dict()})")

# --- 1. Per-pass averages by period, next to the AIS crossing count ---------------------------
cross = daily_crossings()["tanker_total"]
rows = []
for label, a, b in PERIODS:
    p = passes.loc[a:b]
    rows.append({"period": label, "passes": len(p), "radar_with_ais": p["ais"].mean(),
                 "radar_ais_tankers": p["ais_tanker"].mean(), "radar_dark": p["dark"].mean(),
                 "radar_dark_nonfishing": p["dark_nonfishing"].mean(),
                 "dark_share_pct": 100 * p["dark"].sum() / p["total"].sum(),
                 "ais_tanker_crossings_per_day": cross.loc[a:b].mean()})
tab = pd.DataFrame(rows).set_index("period")
pct = 100 * tab.drop(columns=["passes", "dark_share_pct"]) / tab.drop(columns=["passes", "dark_share_pct"]).iloc[0]
print("\n=== Radar ships per satellite pass (and AIS tanker crossings per day) ===")
print(tab.round(1).to_string())
print("\n=== Same, as % of 2025 ===")
print(pct.round(0).to_string())
tab.round(2).to_csv(ROOT / "results/dark_ships_periods.csv")

# --- 2. Figure: what radar saw per pass (top) and three measures indexed to 2025 (bottom) -----
m = passes.resample("MS").mean()
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.6), sharex=True, gridspec_kw={"height_ratios": [1, 1]})
for ax in (a1, a2):
    shade_disruptions(ax)
w = pd.Timedelta(days=24)
a1.bar(m.index, m["ais"], width=w, color=TANKER, label="With AIS (visible to ship trackers)", align="edge")
a1.bar(m.index, m["dark_nonfishing"], width=w, bottom=m["ais"], color=THIRD, label="Dark: likely not fishing boats",
       align="edge")
a1.bar(m.index, m["dark_other"], width=w, bottom=m["ais"] + m["dark_nonfishing"], color=OTHER_DARK,
       label="Dark: other (mostly small or fishing boats)", align="edge")
a1.set_ylabel("ships seen per\nsatellite pass")
a1.set_title("Satellite radar over the strait: ships seen per pass, monthly average", loc="left")
a1.legend(loc="upper left", ncol=3)
a1.set_ylim(0, m["total"].max() * 1.25)

cm = cross.loc[SAMPLE_START:].resample("MS").mean()
base = lambda x: 100 * x / x.loc["2025"].mean()  # noqa: E731
a2.axhline(100, color=TEXT_2, lw=0.8)
a2.plot(cm.index + pd.Timedelta(days=12), base(cm), color=TANKER, label="AIS tanker crossings (this study's count)")
a2.plot(m.index + pd.Timedelta(days=12), base(m["ais_tanker"]), color=TANKER, ls=":", lw=1.6,
        label="Radar: tankers with AIS")
a2.plot(m.index + pd.Timedelta(days=12), base(m["dark_nonfishing"]), color=THIRD, label="Radar: dark, likely not fishing")
a2.set_ylabel("index, 2025 = 100")
a2.set_title("Did traffic carry on in the dark? Three measures, indexed to their 2025 average", loc="left")
a2.legend(loc="upper left", ncol=3)
a2.set_ylim(0, max(base(m["dark_nonfishing"]).max(), base(m["ais_tanker"]).max()) * 1.2)
fig.tight_layout(rect=(0, 0.02, 1, 1))
source_note(fig, "Radar: Sentinel-1 via Global Fishing Watch SAR vessel detections. Exploratory, not pre-registered.")
fig.savefig(ROOT / "figures/dark_ships.png", dpi=160)
print("\nSaved figures/dark_ships.png")
