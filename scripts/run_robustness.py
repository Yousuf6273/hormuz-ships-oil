"""Robustness checks for H1 in training (all labelled as checks; the main test is in run_regressions.py)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.analysis import h1_table, out_of_sample  # noqa: E402
from hormuz.config import TEST_START, TRAIN_END  # noqa: E402
from hormuz.data import SAMPLE_START, analysis_table, daily_crossings  # noqa: E402
from hormuz.features import ship_features  # noqa: E402

pd.set_option("display.width", 160)
tab = analysis_table()
daily = daily_crossings()
daily["tanker_plus_unclear"] = daily["tanker_total"] + daily["cargo_or_tanker_total"]
tab = tab.join(ship_features(daily, tab.index, "tanker_plus_unclear")[["tanker_plus_unclear_shock"]])

checks = []


def add(label, t, x="tanker_total_shock", ret="brent"):
    r = h1_table(t, x, ret)
    r.insert(0, "check", label)
    checks.append(r)


train = tab.loc[SAMPLE_START:TRAIN_END]
add("main (2022 start, Yahoo Brent futures)", train)
add("start 2021-01-01", tab.loc["2021-01-01":TRAIN_END])
add("start 2017-01-01", tab.loc["2017-01-01":TRAIN_END])
add("Brent spot (FRED) as outcome", train, ret="brent_spot")
add("WTI as outcome", train, ret="wti")
add("predictor: day-on-day change", train, x="tanker_total_dd")
add("predictor: 7-day vs 28-day", train, x="tanker_total_shock7")
add("predictor: inbound only", train, x="tanker_inbound_shock")
add("predictor: outbound only", train, x="tanker_outbound_shock")
add("tankers + unclear cargo/tanker", train, x="tanker_plus_unclear_shock")
rob = pd.concat(checks, ignore_index=True)
print(rob[["check", "h", "b", "p_raw", "p_holm", "ret_pct_after_10pct_drop", "n"]].round(4).to_string(index=False))
rob.to_csv(ROOT / "results/robustness_h1.csv", index=False)

print("\n=== Held-out test with the 2017-start training model ===")
print(out_of_sample(tab.loc["2017-01-01":TRAIN_END], tab.loc[TEST_START:]).round(4).to_string(index=False))
