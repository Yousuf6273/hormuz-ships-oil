"""Shared settings: paths, areas and dates. Change things here, not inside the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"

# Two boxes either side of the 56.5E dividing meridian (idea from the
# KaiErikNiermann/hormuz-crossing-tracker reference). A 0.1 degree gap between
# them means a ship has to actually travel through the strait to appear in both.
# Rings are [lon, lat]. Latitude stops at 26.95N to leave out Bandar Abbas port.
BOXES = {
    "west": [[56.10, 26.00], [56.45, 26.00], [56.45, 26.95], [56.10, 26.95], [56.10, 26.00]],
    "east": [[56.55, 26.00], [56.90, 26.00], [56.90, 26.95], [56.55, 26.95], [56.55, 26.00]],
}

# Port zones for the "Gulf trade pulse" extension (centres and radii from the
# yasumorishima/hormuz-ship-tracker reference). Jebel Ali is inside the Gulf;
# Fujairah is outside the strait, at the end of the UAE's bypass pipeline.
ZONES = {
    "jebel_ali": {"lat": 25.05, "lon": 55.05, "radius_nm": 12},
    "fujairah": {"lat": 25.15, "lon": 56.40, "radius_nm": 10},
}

TRAIN_END = "2025-06-30"
TEST_START = "2025-07-01"
