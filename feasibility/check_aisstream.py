"""Feasibility check: does aisstream.io deliver live AIS positions in the Strait of Hormuz?

Listens for a fixed time to (1) the Hormuz / Gulf area and (2) the whole world,
then reports how many positions and vessels each returned.
"""
import asyncio
import json
import os
import ssl
import sys
import time

import certifi
import websockets
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ.get("AISSTREAM_API_KEY", "").strip()
URL = "wss://stream.aisstream.io/v0/stream"
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

# [[lat_min, lon_min], [lat_max, lon_max]]
BOXES = {
    "hormuz_and_gulf": [[[23.5, 47.5], [30.5, 60.0]]],
    "whole_world": [[[-90, -180], [90, 180]]],
}


async def listen(boxes, seconds):
    sub = {"APIKey": KEY, "BoundingBoxes": boxes, "FilterMessageTypes": ["PositionReport", "ShipStaticData"]}
    positions, vessels, tankers, sample = 0, set(), set(), []
    t0 = time.time()
    try:
        async with websockets.connect(URL, open_timeout=20, ssl=SSL_CTX) as ws:
            await ws.send(json.dumps(sub))
            while time.time() - t0 < seconds:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(1, seconds - (time.time() - t0)))
                except asyncio.TimeoutError:
                    break
                msg = json.loads(raw)
                if "error" in msg:
                    return {"error": msg["error"]}
                meta = msg.get("MetaData", {})
                mmsi = meta.get("MMSI")
                if msg.get("MessageType") == "PositionReport":
                    positions += 1
                    vessels.add(mmsi)
                    if len(sample) < 3:
                        sample.append((round(meta.get("latitude", 0), 2), round(meta.get("longitude", 0), 2)))
                elif msg.get("MessageType") == "ShipStaticData":
                    t = msg["Message"]["ShipStaticData"].get("Type")
                    if t is not None and 80 <= t <= 89:
                        tankers.add(mmsi)
    except Exception as e:  # report, don't hide
        return {"error": f"{type(e).__name__}: {e}"}
    return {"positions": positions, "vessels": len(vessels), "tankers_seen_static": len(tankers), "sample_latlon": sample}


async def main():
    if not KEY:
        sys.exit("AISSTREAM_API_KEY is empty in .env")
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    for name, box in BOXES.items():
        res = await listen(box, secs if name != "whole_world" else 60)
        print(name, res, flush=True)


asyncio.run(main())
