"""Download GFW presence for both Hormuz boxes, month by month (cached; safe to re-run).

Usage: python scripts/pull_gfw.py 2012-01 2026-11 [--refresh-last N]
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hormuz.gfw import pull_month  # noqa: E402

first, last = sys.argv[1], sys.argv[2]
refresh_last = int(sys.argv[sys.argv.index("--refresh-last") + 1]) if "--refresh-last" in sys.argv else 0
months = [p.strftime("%Y-%m") for p in pd.period_range(first, last, freq="M")]
for i, m in enumerate(months):
    refresh = i >= len(months) - refresh_last
    for box in ("west", "east"):
        try:
            n = pull_month(box, m, refresh=refresh)
            print(f"{m} {box:4s} rows={n}", flush=True)
        except Exception as e:  # keep going; failures are listed and can be re-run
            print(f"{m} {box:4s} FAILED {e}", flush=True)
