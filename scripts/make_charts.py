"""Descriptive charts: daily tanker crossings vs Brent (2022 -> latest) and a zoom on the March 2026 closure."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.config import TEST_START  # noqa: E402
from hormuz.data import SAMPLE_START, daily_crossings, main_prices  # noqa: E402
from hormuz.plotstyle import (BRENT, CARGO, TANKER, TEXT_2, plt, shade_disruptions,  # noqa: E402
                              source_note)

FIG = ROOT / "figures"
d = daily_crossings().loc[SAMPLE_START:]
px = main_prices()["brent"].dropna().loc[SAMPLE_START:]

# 1. Whole sample: two panels, shared time axis (never two y-scales on one panel)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.15, 1]})
for ax in (a1, a2):
    shade_disruptions(ax)
    ax.axvline(pd.Timestamp(TEST_START), color=TEXT_2, ls="--", lw=1)
t7, c7 = d["tanker_total"].rolling(7).mean(), d["cargo_total"].rolling(7).mean()
a1.plot(t7.index, t7, color=TANKER, label="Tankers")
a1.plot(c7.index, c7, color=CARGO, label="Cargo ships", lw=1.5)
a1.set_ylabel("crossings per day\n(7-day average)")
a1.set_title("Strait of Hormuz crossings (top) and Brent crude price (bottom), 2022 to Nov 2026", loc="left")
a1.legend(loc="lower left", ncol=2)
a1.text(pd.Timestamp(TEST_START), a1.get_ylim()[1], "  test period", color=TEXT_2, va="top", fontsize=8)
a1.annotate("March 2026\nrestrictions", xy=(pd.Timestamp("2026-03-10"), 5), xytext=(pd.Timestamp("2025-09-01"), 25),
            fontsize=8, color=TEXT_2, arrowprops=dict(arrowstyle="-", color=TEXT_2, lw=0.8))
a2.plot(px.index, px, color=BRENT, lw=1.2)
a2.set_ylabel("Brent, $ per barrel")
a2.text(pd.Timestamp("2024-04-14"), a2.get_ylim()[1], " Apr 2024", color=TEXT_2, va="top", fontsize=7)
a2.text(pd.Timestamp("2025-06-14"), a2.get_ylim()[1], " Jun 2025", color=TEXT_2, va="top", fontsize=7)
fig.text(0.99, 0.005, "Grey bands: disruption periods fixed in advance (HYPOTHESES.md).", fontsize=6.5, color=TEXT_2, ha="right", va="bottom")
source_note(fig)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "crossings_vs_brent.png", dpi=170)

# 2. Zoom on the closure: daily counts by direction + Brent
z0, z1 = "2026-02-09", "2026-03-31"
dz, pz = d.loc[z0:z1], px.loc[z0:z1]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 5.6), sharex=True)
for ax in (a1, a2):
    ax.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-03-31"), color="#d9d7d0", alpha=0.8, lw=0, zorder=0)
w = pd.Timedelta(hours=9)
noon = dz.index + pd.Timedelta(hours=12)  # each UTC day's bars sit in the middle of that day
a1.bar(noon - w / 2, dz["tanker_inbound"], width=w, color=TANKER, label="Tankers in (into the Gulf)")
a1.bar(noon + w / 2, dz["tanker_outbound"], width=w, color="#9cc2ef", label="Tankers out (leaving the Gulf)")
a1.set_ylabel("tanker crossings per day")
a1.set_title("The closure, day by day: ships stopped over the weekend, before oil markets reopened", loc="left")
a1.legend(loc="upper right")
a1.annotate("Sat 28 Feb: closure\nannounced", xy=(pd.Timestamp("2026-02-28"), 30), xytext=(pd.Timestamp("2026-03-08"), 33),
            fontsize=8, color=TEXT_2, arrowprops=dict(arrowstyle="-", color=TEXT_2, lw=0.8))
close_t = pz.index + pd.Timedelta(hours=19, minutes=30)  # Brent settles ~19:30 London
a2.plot(close_t, pz.values, color=BRENT, marker="o", ms=4, lw=1.4)
a2.set_ylabel("Brent, $ per barrel\n(at daily close)")
mon = pd.Timestamp("2026-03-02")
a2.annotate("Mon 2 Mar: first\ntrading day after", xy=(mon + pd.Timedelta(hours=19.5), pz.loc[mon]), xytext=(pd.Timestamp("2026-02-10"), pz.max() * 0.95),
            fontsize=8, color=TEXT_2, arrowprops=dict(arrowstyle="-", color=TEXT_2, lw=0.8))
import matplotlib.dates as mdates  # noqa: E402
a2.xaxis.set_major_formatter(mdates.DateFormatter("%-d %b"))
source_note(fig)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "closure_zoom.png", dpi=170)
print("saved figures/crossings_vs_brent.png and figures/closure_zoom.png")
