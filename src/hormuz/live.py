"""Short live sample from aisstream.io: how many AIS positions arrive from the Hormuz area right now?"""
import asyncio
import json
import os
import ssl
import time

import certifi
import websockets
from dotenv import load_dotenv

from .config import ROOT

load_dotenv(ROOT / ".env")
URL = "wss://stream.aisstream.io/v0/stream"
HORMUZ_BOX = [[[25.5, 55.5], [27.2, 57.5]]]  # [[lat_min, lon_min], [lat_max, lon_max]]
WORLD_BOX = [[[-90, -180], [90, 180]]]


async def _listen(boxes, seconds):
    key = os.environ.get("AISSTREAM_API_KEY", "").strip()
    if not key:
        return {"error": "AISSTREAM_API_KEY is empty in .env"}
    sub = {"APIKey": key, "BoundingBoxes": boxes, "FilterMessageTypes": ["PositionReport", "ShipStaticData"]}
    ctx = ssl.create_default_context(cafile=certifi.where())
    positions, vessels, tankers = 0, set(), set()
    t0 = time.time()
    try:
        async with websockets.connect(URL, open_timeout=15, ssl=ctx) as ws:
            await ws.send(json.dumps(sub))
            while time.time() - t0 < seconds:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(0.5, seconds - (time.time() - t0)))
                except asyncio.TimeoutError:
                    break
                msg = json.loads(raw)
                if "error" in msg:
                    return {"error": msg["error"]}
                mmsi = msg.get("MetaData", {}).get("MMSI")
                if msg.get("MessageType") == "PositionReport":
                    positions += 1
                    vessels.add(mmsi)
                elif msg.get("MessageType") == "ShipStaticData":
                    t = msg["Message"]["ShipStaticData"].get("Type")
                    if t is not None and 80 <= t <= 89:  # AIS ship types 80-89 = tankers
                        tankers.add(mmsi)
    except Exception as e:  # report, never hide
        return {"error": f"{type(e).__name__}: {e}"}
    return {"positions": positions, "vessels": len(vessels), "tankers": len(tankers), "seconds": seconds}


def sample(seconds=20):
    """Listen to the Hormuz area, then 5 s of the whole world as a check that the feed works."""
    return {"hormuz": asyncio.run(_listen(HORMUZ_BOX, seconds)), "world_check": asyncio.run(_listen(WORLD_BOX, 5))}
