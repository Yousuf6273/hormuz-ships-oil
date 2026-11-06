"""Step 4: lead-lag correlations and Granger causality (training; test period repeated for reference)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.analysis import granger, lead_lag  # noqa: E402
from hormuz.config import TEST_START, TRAIN_END  # noqa: E402
from hormuz.data import SAMPLE_START, analysis_table  # noqa: E402
from hormuz.plotstyle import TANKER, TEXT_2, CARGO, plt, source_note  # noqa: E402

pd.set_option("display.width", 140)
tab = analysis_table()
periods = {"train": tab.loc[SAMPLE_START:TRAIN_END], "test": tab.loc[TEST_START:]}
X = "tanker_total_shock"

ll, gr = [], []
train_lags = None
for name, t in periods.items():
    a = lead_lag(t, X).assign(period=name)
    g = granger(t, X, lags=train_lags).assign(period=name)  # test reuses the training lag length
    train_lags = int(g["lags_aic"].iloc[0])
    ll.append(a)
    gr.append(g)
    print(f"\n=== {name}: lead-lag (corr, raw p, BH-adjusted p) ===")
    print(a.round(3).to_string(index=False))
    print(f"\n=== {name}: Granger ===")
    print(g.round(4).to_string(index=False))
pd.concat(ll).to_csv(ROOT / "results/lead_lag.csv", index=False)
pd.concat(gr).to_csv(ROOT / "results/granger.csv", index=False)

# Chart: training-period lead-lag profile (the pre-registered, confirmatory sample)
a = ll[0]
fig, ax = plt.subplots(figsize=(9, 3.8))
s, o = a[a.direction == "ships_lead"], a[a.direction == "oil_leads"]
ax.bar(s["lag"], s["corr"], width=0.6, color=TANKER, label="Ships lead oil: corr(shock today, Brent return k days later)")
ax.bar(-o["lag"], o["corr"], width=0.6, color=CARGO, label="Oil leads ships: corr(Brent return today, shock k days later)")
ax.axhline(0, color=TEXT_2, lw=0.8)
n = int(s["n"].median())
band = 1.96 / n ** 0.5
ax.axhspan(-band, band, color="#e4e3df", alpha=0.6, lw=0, zorder=0)
ax.set_xticks(range(-10, 11))
ax.set_xticklabels([f"{abs(k)}" for k in range(-10, 11)])
ax.set_xlabel("lag in trading days  (left: oil first  |  right: ships first)")
ax.set_ylabel("correlation")
ax.set_title("Lead-lag: tanker crossing shock vs Brent daily return (training 2022 to Jun 2025)", loc="left")
ax.legend(loc="lower left", fontsize=7)
ax.text(10.4, band * 1.08, "grey band: where 95% of correlations\nwould fall by pure chance", fontsize=7, color=TEXT_2, ha="right", va="bottom")
source_note(fig)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(ROOT / "figures/lead_lag.png", dpi=170)
