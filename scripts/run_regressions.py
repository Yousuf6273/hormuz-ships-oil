"""Step 5: H1 predictive regressions, H2 disruption interaction, H3 placebo (cargo, fishing)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.analysis import correct, dummy_for, h1_table, h2_table  # noqa: E402
from hormuz.config import TEST_START, TRAIN_END  # noqa: E402
from hormuz.data import SAMPLE_START, analysis_table  # noqa: E402

pd.set_option("display.width", 160)
tab = analysis_table()
train, test = tab.loc[SAMPLE_START:TRAIN_END], tab.loc[TEST_START:]

print("=== H1 (training): Brent forward return on tanker crossing shock + controls ===")
h1 = h1_table(train)
print(h1.round(4).to_string(index=False))

print("\n=== H2 (training): extra effect inside the Apr 2024 and Jun 2025 disruption windows ===")
h2a = h2_table(train, dummy_for(train.index, [("2024-04-13", "2024-04-30"), ("2025-06-13", "2025-06-24")]))
print(h2a.round(4).to_string(index=False))
print("\n=== H2 (test, out of sample): extra effect inside the March 2026 window ===")
h2b = h2_table(test, dummy_for(test.index, [("2026-02-28", "2026-03-31")]))
print(h2b.round(4).to_string(index=False))

print("\n=== H3 placebo (training): cargo and fishing crossing shocks ===")
h3 = pd.concat([h1_table(train, "cargo_total_shock"), h1_table(train, "fishing_total_shock")], ignore_index=True)
h3["p_holm"] = correct(h3["p_raw"], "holm")  # one family of 6 tests, as pre-registered
print(h3.round(4).to_string(index=False))

out = pd.concat([h1.assign(test="H1", period="train"), h2a.assign(test="H2", period="train"),
                 h2b.assign(test="H2", period="test"), h3.assign(test="H3", period="train")], ignore_index=True)
out.to_csv(ROOT / "results/h1_h2_h3.csv", index=False)
