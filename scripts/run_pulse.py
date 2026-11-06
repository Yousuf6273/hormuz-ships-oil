"""Extension (exploratory, NOT pre-registered): the "Gulf trade pulse".

Ships present each day at two UAE ports:
  - Jebel Ali (Dubai), inside the Gulf: every ship must pass Hormuz to get there.
  - Fujairah, outside the strait on the Gulf of Oman: the Habshan-Fujairah pipeline lets UAE crude skip Hormuz.
Question: when the strait closed in March 2026, did Fujairah hold up better than Jebel Ali?
Also: does a drop in either port's traffic predict Brent in the training period (same model as H1)?
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.analysis import correct, h1_table  # noqa: E402
from hormuz.config import TRAIN_END  # noqa: E402
from hormuz.crossings import vessel_class  # noqa: E402
from hormuz.data import SAMPLE_START, analysis_table, daily_crossings  # noqa: E402
from hormuz.features import ship_features  # noqa: E402
from hormuz.gfw import load_zone  # noqa: E402
from hormuz.plotstyle import CARGO, TANKER, TEXT_2, plt, shade_disruptions, source_note  # noqa: E402

pd.set_option("display.width", 160)
ZONES = {"jebel_ali": "Jebel Ali, Dubai (inside the Gulf)", "fujairah": "Fujairah (outside the strait)"}
CLASSES = ("tanker", "cargo")
PERIODS = [("2025 average (base)", "2025-01-01", "2025-12-31"), ("Jan–Feb 2026", "2026-01-01", "2026-02-27"),
           ("Mar 2026", "2026-03-01", "2026-03-31"), ("Apr 2026 → latest", "2026-04-01", None)]


def zone_daily(zone):
    """Unique vessels present per UTC day, by class, plus total vessel-hours (0 = no data that day)."""
    z = load_zone(zone)
    z["day"] = pd.to_datetime(z["date"])
    z["vclass"] = [vessel_class(g, v) for g, v in zip(z["geartype"], z["vesselType"])]
    counts = z[z["vclass"].isin(CLASSES)].pivot_table(index="day", columns="vclass", values="vesselId", aggfunc="nunique")
    hours = z.groupby("day")["hours"].sum().rename("vessel_hours")
    idx = pd.date_range(z["day"].min(), z["day"].max(), freq="D", name="day")
    out = pd.concat([counts, hours], axis=1).reindex(idx).astype(float).fillna(0)
    return out.add_prefix(f"{zone}_")


pulse = pd.concat([zone_daily(z) for z in ZONES], axis=1)
strait = daily_crossings()[["tanker_total", "cargo_total", "vessel_hours"]].add_prefix("strait_")
pulse = pulse.join(strait, how="left").loc[SAMPLE_START:]
pulse.round(1).to_csv(ROOT / "data/processed/gulf_pulse.csv")
print(f"Days: {pulse.index.min():%Y-%m-%d} → {pulse.index.max():%Y-%m-%d}; "
      f"days with no data: jebel_ali {int((pulse['jebel_ali_vessel_hours'] == 0).sum())}, "
      f"fujairah {int((pulse['fujairah_vessel_hours'] == 0).sum())}")

# --- 1. Period averages, as % of the 2025 average ------------------------------------------
series = {f"{p}_{c}": pulse[f"{p}_{c}" if p != "strait" else f"strait_{c}_total"].where(pulse[f"{p}_vessel_hours"] > 0)
          for p in ("strait", *ZONES) for c in CLASSES}
rows = []
for name, s in series.items():
    base = s.loc["2025"].mean()
    for label, a, b in PERIODS:
        m = s.loc[a:b].mean()
        rows.append((name, label, m, 100 * m / base))
tab = pd.DataFrame(rows, columns=["series", "period", "ships_per_day", "pct_of_2025"]).round(1)
print("\n=== Ships per day, and as % of the 2025 average ===")
print(tab.pivot(index="series", columns="period", values="pct_of_2025")[[p[0] for p in PERIODS]].to_string())
print(tab.pivot(index="series", columns="period", values="ships_per_day")[[p[0] for p in PERIODS]].to_string())
tab.to_csv(ROOT / "results/gulf_pulse_periods.csv", index=False)

# --- 2. Figure: 7-day averages indexed to 2025 = 100, one panel per place -----------------
panels = [("strait", "Strait of Hormuz: crossings"), ("jebel_ali", f"{ZONES['jebel_ali']}: ships present"),
          ("fujairah", f"{ZONES['fujairah']}: ships present")]
fig, axes = plt.subplots(3, 1, figsize=(11, 7.6), sharex=True, sharey=True)
for ax, (p, title) in zip(axes, panels):
    shade_disruptions(ax)
    ax.axhline(100, color=TEXT_2, lw=0.8)
    for c, color, lab in (("tanker", TANKER, "Tankers"), ("cargo", CARGO, "Cargo ships")):
        s = series[f"{p}_{c}"]
        idx = 100 * s.rolling(7, min_periods=4).mean() / s.loc["2025"].mean()
        ax.plot(idx.index, idx, color=color, lw=1.6 if c == "tanker" else 1.3, label=lab)
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_ylabel("index, 2025 = 100")
axes[0].legend(loc="upper left", ncol=2)
axes[0].set_ylim(0, None)
fig.suptitle("Gulf trade pulse: what happened at the ports when the strait closed (7-day averages)",
             x=0.01, ha="left", fontweight="bold", fontsize=11)
fig.tight_layout(rect=(0, 0.02, 1, 1))
source_note(fig, "Grey bands: disruption periods. Exploratory, not pre-registered.")
fig.savefig(ROOT / "figures/gulf_pulse.png", dpi=160)
print("\nSaved figures/gulf_pulse.png")

# --- 3. Exploratory: do port-traffic shocks predict Brent? (training period, H1 model) ------
t = analysis_table().loc[SAMPLE_START:TRAIN_END]
regs = []
for p in ZONES:
    daily = pulse[[f"{p}_{c}" for c in CLASSES]].copy()
    daily["vessel_hours"] = pulse[f"{p}_vessel_hours"]
    for c in CLASSES:
        col = f"{p}_{c}"
        t = t.join(ship_features(daily, t.index, col)[[f"{col}_shock"]])
        regs.append(h1_table(t, f"{col}_shock"))
regs = pd.concat(regs, ignore_index=True)
regs["p_holm"] = correct(regs["p_raw"], "holm")  # one family: 4 predictors x 3 horizons
print("\n=== Exploratory (training): Brent forward return on port-traffic shock + controls ===")
print(regs.round(4).to_string(index=False))
regs.to_csv(ROOT / "results/gulf_pulse_regressions.csv", index=False)
