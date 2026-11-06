"""One look for every figure (reference dataviz palette, light mode)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
TANKER = "#2a78d6"   # categorical slot 1
CARGO = "#eb6834"    # categorical slot 2
THIRD = "#1baf7a"    # categorical slot 3
BRENT = "#0b0b0b"    # single-series panels use ink, not a category colour
EVENT = "#d9d7d0"    # neutral band for disruption periods
SOURCE = ("Ships: Global Fishing Watch AIS vessel presence (CC BY-NC 4.0), powered by globalfishingwatch.org. "
          "Prices: Yahoo Finance, FRED.")

DISRUPTIONS = [("2024-04-13", "2024-04-30", "MSC Aries seizure"),
               ("2025-06-13", "2025-06-24", "Israel–Iran war"),
               ("2026-02-28", "2026-03-31", "March 2026 restrictions")]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT_2, "xtick.color": TEXT_2, "ytick.color": TEXT_2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2,
    "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": TEXT,
    "legend.frameon": False, "legend.fontsize": 8,
})


def shade_disruptions(ax, label=False):
    import pandas as pd
    for start, end, name in DISRUPTIONS:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=EVENT, alpha=0.8, lw=0, zorder=0)


def source_note(fig, extra=""):
    fig.text(0.01, 0.005, SOURCE + (" " + extra if extra else ""), fontsize=6.5, color=TEXT_2, ha="left", va="bottom")
