"""Download daily GFW presence for the port zones (Jebel Ali, Fujairah), month by month (cached).

Usage: python scripts/pull_zones.py 2022-01 2026-11 [--refresh-last N]
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hormuz.config import ZONES  # noqa: E402
from hormuz.gfw import pull_zone_month  # noqa: E402

first, last = sys.argv[1], sys.argv[2]
refresh_last = int(sys.argv[sys.argv.index("--refresh-last") + 1]) if "--refresh-last" in sys.argv else 0
months = [p.strftime("%Y-%m") for p in pd.period_range(first, last, freq="M")]
for i, m in enumerate(months):
    for zone in ZONES:
        try:
            print(f"{m} {zone:9s} rows={pull_zone_month(zone, m, refresh=i >= len(months) - refresh_last)}", flush=True)
        except Exception as e:  # keep going; failures are listed and can be re-run
            print(f"{m} {zone:9s} FAILED {e}", flush=True)
