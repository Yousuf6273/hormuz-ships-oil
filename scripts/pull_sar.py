"""Download Sentinel-1 radar ship detections over the strait (both crossing boxes and the gap between them).

Usage: python scripts/pull_sar.py 2022-01 2026-11
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.config import BOXES  # noqa: E402
from hormuz.gfw import pull_sar_month  # noqa: E402

STRAIT = [[BOXES["west"][0][0], BOXES["west"][0][1]], [BOXES["east"][1][0], BOXES["east"][1][1]],
          [BOXES["east"][2][0], BOXES["east"][2][1]], [BOXES["west"][3][0], BOXES["west"][3][1]],
          [BOXES["west"][0][0], BOXES["west"][0][1]]]

if __name__ == "__main__":
    first, last = sys.argv[1], sys.argv[2]
    print("strait polygon:", STRAIT)
    for m in pd.period_range(first, last, freq="M").astype(str):
        try:
            df = pull_sar_month(STRAIT, m, refresh=m >= last)
            print(m, df.groupby("kind")["detections"].sum().to_dict(), flush=True)
        except Exception as e:
            print(m, "FAILED", e, flush=True)
