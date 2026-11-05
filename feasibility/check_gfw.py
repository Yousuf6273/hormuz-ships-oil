"""Feasibility check: what Global Fishing Watch (GFW) data can we get for the Strait of Hormuz?

Step 1  token works?
Step 2  one-week sample: which fields and vessel types come back?
Step 3  how far back does usable data go, and how recent is it?
"""
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("GFW_API_TOKEN", "").strip()
BASE = "https://gateway.api.globalfishingwatch.org/v3"
HEAD = {"Authorization": f"Bearer {TOKEN}"}

# Two boxes either side of the 56.5E dividing meridian, with a small gap so a ship
# must actually move through the strait to appear in both.
WEST = [[56.10, 26.00], [56.45, 26.00], [56.45, 26.95], [56.10, 26.95], [56.10, 26.00]]
EAST = [[56.55, 26.00], [56.90, 26.00], [56.90, 26.95], [56.55, 26.95], [56.55, 26.00]]


def geojson(ring):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


def report(ring, start, end, dataset="public-global-presence:latest", temporal="DAILY", group="VESSEL_ID", filters=None):
    params = {"datasets[0]": dataset, "format": "JSON", "temporal-resolution": temporal,
              "group-by": group, "spatial-aggregation": "true", "date-range": f"{start},{end}"}
    if filters:
        params["filters[0]"] = filters
    for attempt in range(6):
        r = requests.post(f"{BASE}/4wings/report", params=params, headers=HEAD,
                          json={"geojson": geojson(ring)}, timeout=180)
        if r.status_code in (429, 503, 524):
            time.sleep(10 * (attempt + 1))
            continue
        return r
    return r


def rows(resp):
    js = resp.json()
    out = []
    for e in js.get("entries", []):
        for _, v in e.items():
            out.extend(v)
    return out


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("GFW_API_TOKEN is empty in .env")
    step = sys.argv[1] if len(sys.argv) > 1 else "sample"
    if step == "sample":
        r = report(WEST, "2025-01-06", "2025-01-08")
        print("HTTP", r.status_code)
        if r.status_code != 200:
            print(r.text[:1500])
            sys.exit(1)
        rs = rows(r)
        print("rows:", len(rs))
        if rs:
            print("fields:", sorted(rs[0].keys()))
            print("example:", json.dumps(rs[0], indent=1)[:1500])
            from collections import Counter
            print("vesselType counts:", Counter(x.get("vesselType") for x in rs).most_common())
            print("geartype counts:", Counter(x.get("geartype") for x in rs).most_common(15))
