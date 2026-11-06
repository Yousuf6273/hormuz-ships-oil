"""Step 6: March 2026 event study and held-out (out-of-sample) evaluation of the H1 model."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.analysis import event_study, h1_table, out_of_sample  # noqa: E402
from hormuz.config import TEST_START, TRAIN_END  # noqa: E402
from hormuz.data import SAMPLE_START, analysis_table  # noqa: E402
from hormuz.plotstyle import BRENT, TANKER, TEXT_2, plt, source_note  # noqa: E402

pd.set_option("display.width", 160)
tab = analysis_table()
train, test = tab.loc[SAMPLE_START:TRAIN_END], tab.loc[TEST_START:]

print("=== Held-out test: model fitted on training, used unchanged on Jul 2025 -> latest ===")
oos = out_of_sample(train, test)
print(oos.round(4).to_string(index=False))
print("\n=== Same regression re-estimated on the test period alone (sign check) ===")
h1_test = h1_table(test)
print(h1_test.round(4).to_string(index=False))
print("\n=== Test period WITHOUT Mar 2026 - Nov 2026 (crisis removed; exploratory) ===")
pre_crisis = test.loc[:"2026-02-27"]
print(h1_table(pre_crisis).round(4).to_string(index=False))
oos.to_csv(ROOT / "results/out_of_sample.csv", index=False)
h1_test.to_csv(ROOT / "results/h1_test_period.csv", index=False)

print("\n=== Event study: day 0 = Mon 2 Mar 2026 ===")
w, mm, sigma = event_study(tab, "2026-03-02")
print(f"market model (days -250..-30): alpha={mm.params['const']:.5f} beta={mm.params['sp500_ret']:.3f} sigma={sigma:.4f}")
show = w[["event_day", "brent_ret", "abnormal", "car", "car_t", "tanker_total_level"]]
print(show.round(4).to_string())
w.to_csv(ROOT / "results/event_study.csv")

fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.5, 5.6), sharex=True)
a1.bar(w["event_day"], w["tanker_total_level"], color=TANKER, width=0.7)
a1.set_ylabel("tanker crossings per day\n(since previous close)")
a1.set_title("March 2026 event study: tanker crossings (top) and Brent abnormal return (bottom)", loc="left")
a2.plot(w["event_day"], 100 * w["car"], color=BRENT, marker="o", ms=4, lw=1.6)
band = 1.96 * sigma * np.sqrt(np.arange(1, len(w) + 1)) * 100
a2.fill_between(w["event_day"], -band, band, color="#e4e3df", lw=0, zorder=0)
a2.set_ylabel("cumulative abnormal\nBrent return, %")
a2.set_xlabel("trading days relative to Mon 2 Mar 2026 (day 0)")
for ax in (a1, a2):
    ax.axvline(-0.5, color=TEXT_2, ls="--", lw=1)
a2.text(-0.4, a2.get_ylim()[1] * 0.92, " weekend of 28 Feb - 1 Mar", color=TEXT_2, fontsize=8)
a2.text(20, -band.max() * 0.85, "grey: range expected from normal\nday-to-day noise (95%)", color=TEXT_2, fontsize=7, ha="right")
a2.text(-10, band.max() * 2.6, "abnormal = Brent return minus what the\nS&P 500 predicts (fitted on days -250 to -30)", color=TEXT_2, fontsize=7, va="top")
source_note(fig)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(ROOT / "figures/event_study.png", dpi=170)
