"""Build data/processed/analysis_table.csv: one row per Brent trading day (all years; samples are cut later)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hormuz.config import PROCESSED  # noqa: E402
from hormuz.data import daily_crossings, fred_brent_prices, main_prices  # noqa: E402
from hormuz.features import build_table  # noqa: E402

daily = daily_crossings()
tab = build_table(daily, main_prices())
fb = build_table(daily, fred_brent_prices(), ship_cols=())
tab["brent_spot_ret"] = fb["brent_ret"]
for h in (1, 3, 7):
    tab[f"brent_spot_fwd{h}"] = fb[f"brent_fwd{h}"]
tab.to_csv(PROCESSED / "analysis_table.csv")
print(tab.shape, tab.index.min().date(), tab.index.max().date())
