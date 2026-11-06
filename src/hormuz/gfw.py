"""Download and cache Global Fishing Watch AIS vessel presence for the Hormuz boxes.

Data: Global Fishing Watch, AIS Vessel Presence (public-global-presence), CC BY-NC 4.0.
One HOURLY request per box per calendar month, saved to data/raw/gfw/presence_hourly/<box>/<YYYY-MM>.parquet.
Each row is one vessel seen in one box during one UTC hour (GFW keeps one position per vessel per hour).
"""
import math
import os
import signal
import time

import pandas as pd
import requests
from dotenv import load_dotenv

from .config import BOXES, RAW, ROOT, ZONES

load_dotenv(ROOT / ".env")
BASE = "https://gateway.api.globalfishingwatch.org/v3"
DATASET = "public-global-presence:latest"
KEEP = ["date", "vesselId", "mmsi", "imo", "shipName", "flag", "vesselType", "geartype", "hours", "speed"]


def _token():
    tok = os.environ.get("GFW_API_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("GFW_API_TOKEN is empty in .env")
    return tok


def _geojson(ring):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


def presence_report(ring, start, end, temporal="HOURLY"):
    """One 4Wings report: per-vessel presence inside `ring` between start and end (end excluded)."""
    params = {"datasets[0]": DATASET, "format": "JSON", "temporal-resolution": temporal,
              "group-by": "VESSEL_ID", "spatial-aggregation": "true", "date-range": f"{start},{end}"}
    head = {"Authorization": f"Bearer {_token()}"}
    last = None
    for attempt in range(8):
        try:
            js = _post_json(f"{BASE}/4wings/report", params, head, {"geojson": _geojson(ring)})
            rows = [row for e in js.get("entries", []) for v in e.values() for row in v]
            return pd.DataFrame(rows)
        except RetryableError as e:
            last = e
        except requests.RequestException as e:
            last = e
        print(f"  retry {attempt + 1} for {start}..{end}: {last}", flush=True)
        time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"GFW report failed for {start}..{end}: {last}")


class RetryableError(Exception):
    pass


def _post_json(url, params, head, body, max_seconds=240):
    """POST and read the whole reply, but give up after max_seconds in total.

    The server sometimes keeps a connection open while dribbling out a few bytes, so
    normal socket timeouts never fire. An OS alarm interrupts the request regardless.
    """
    def _alarm(signum, frame):
        raise RetryableError(f"no complete reply after {max_seconds}s")

    old_handler = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(max_seconds)
    try:
        r = requests.post(url, params=params, headers=head, json=body, timeout=(20, 60))
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    if r.status_code in (429, 500, 502, 503, 504, 524):
        raise RetryableError(f"HTTP {r.status_code}")
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def month_path(box, month):
    return RAW / "gfw" / "presence_hourly" / box / f"{month}.parquet"


def circle(lat, lon, radius_nm, n=32):
    """Polygon ring ([lon, lat] points) approximating a circle of radius_nm nautical miles."""
    dlat = radius_nm / 60
    dlon = radius_nm / (60 * math.cos(math.radians(lat)))
    pts = [[lon + dlon * math.cos(2 * math.pi * k / n), lat + dlat * math.sin(2 * math.pi * k / n)] for k in range(n)]
    return pts + [pts[0]]


def pull_month(box, month, refresh=False):
    """Download one box-month (month like '2025-01') unless already cached. Returns row count."""
    return _pull(BOXES[box], month_path(box, month), month, "HOURLY", refresh)


def zone_path(zone, month):
    return RAW / "gfw" / "zones_daily" / zone / f"{month}.parquet"


def pull_zone_month(zone, month, refresh=False):
    """Daily per-vessel presence in a port zone (see config.ZONES)."""
    z = ZONES[zone]
    return _pull(circle(z["lat"], z["lon"], z["radius_nm"]), zone_path(zone, month), month, "DAILY", refresh)


def _pull(ring, path, month, temporal, refresh):
    if path.exists() and not refresh:
        return len(pd.read_parquet(path))
    start = pd.Timestamp(f"{month}-01")
    end = start + pd.offsets.MonthBegin(1)
    df = presence_report(ring, start.date(), end.date(), temporal=temporal)
    if not df.empty:
        df = df[[c for c in KEEP if c in df.columns]]
        df = df[pd.to_datetime(df["date"]).dt.strftime("%Y-%m") == month]
    else:
        df = pd.DataFrame(columns=KEEP)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return len(df)


def load_presence(box):
    return _load(RAW / "gfw" / "presence_hourly" / box)


def load_zone(zone):
    return _load(RAW / "gfw" / "zones_daily" / zone)


def _load(folder):
    files = sorted(folder.glob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else pd.DataFrame()


# --- Satellite radar (Sentinel-1 SAR) detections: ships seen by radar, matched or not to an AIS signal ---
SAR_DATASET = "public-global-sar-presence:latest"


SAR_KINDS = {"ais": "matched='true'",                      # radar ship matched to an AIS signal
             "dark": "matched='false'",                     # radar ship with no AIS signal
             "dark_nonfishing": "matched='false' AND neural_vessel_type='Likely non-fishing'"}


def sar_report(ring, start, end, filt):
    """Daily radar detections inside `ring` that pass the 4Wings filter `filt`, by AIS gear type."""
    params = {"datasets[0]": SAR_DATASET, "filters[0]": filt, "format": "JSON",
              "temporal-resolution": "DAILY", "spatial-aggregation": "true", "group-by": "GEARTYPE",
              "date-range": f"{start},{end}"}
    head = {"Authorization": f"Bearer {_token()}"}
    last = None
    for attempt in range(8):
        try:
            js = _post_json(f"{BASE}/4wings/report", params, head, {"geojson": _geojson(ring)}, max_seconds=120)
            rows = [row for e in js.get("entries", []) for v in e.values() for row in v]
            return pd.DataFrame(rows, columns=["date", "geartype", "detections"])
        except (RetryableError, requests.RequestException) as e:
            last = e
        print(f"  retry {attempt + 1} for SAR {start}..{end}: {last}", flush=True)
        time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"GFW SAR report failed for {start}..{end}: {last}")


def pull_sar_month(ring, month, refresh=False):
    """Radar detections of each kind (SAR_KINDS) for one month, cached to data/raw/gfw/sar_daily/<month>.parquet."""
    path = RAW / "gfw" / "sar_daily" / f"{month}.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    start = pd.Timestamp(f"{month}-01")
    end = start + pd.offsets.MonthBegin(1)
    parts = [sar_report(ring, start.date(), end.date(), f).assign(kind=k) for k, f in SAR_KINDS.items()]
    df = pd.concat(parts, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def load_sar():
    return _load(RAW / "gfw" / "sar_daily")
