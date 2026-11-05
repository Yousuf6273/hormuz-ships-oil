"""Turn per-vessel box presence into Strait of Hormuz crossings.

A crossing is a vessel seen in one box and next seen in the other box within
MAX_GAP_H hours. West -> east = outbound (leaving the Gulf); east -> west = inbound.
Dedup: at most one crossing per vessel per DEDUP_H hours (from the
yasumorishima/hormuz-ship-tracker reference, which uses a 6-hour window).
"""
import pandas as pd

MAX_GAP_H = 24
DEDUP_H = 6
MERGE_H = 3  # same-box sightings with a gap of 3 hours or less are one visit


def vessel_class(geartype, vessel_type):
    """Map GFW labels to the groups used in the study."""
    g, v = str(geartype).upper(), str(vessel_type).upper()
    if g == "TANKER":
        return "tanker"
    if g == "CARGO_OR_TANKER":
        return "cargo_or_tanker"
    if g == "CARGO":
        return "cargo"
    if v == "FISHING":
        return "fishing"
    return "other"


def visits(presence):
    """Collapse hourly box sightings into continuous visits per vessel and box."""
    df = presence.copy()
    df["t_in"] = pd.to_datetime(df["date"], utc=True)
    df["t_out"] = df["t_in"]
    df = df.sort_values(["vesselId", "t_in"])
    new_visit = (
        (df["vesselId"] != df["vesselId"].shift())
        | (df["box"] != df["box"].shift())
        | ((df["t_in"] - df["t_out"].shift()) > pd.Timedelta(hours=MERGE_H))
    )
    df["visit"] = new_visit.cumsum()
    return df.groupby("visit").agg(
        vesselId=("vesselId", "first"), mmsi=("mmsi", "first"), shipName=("shipName", "first"),
        geartype=("geartype", "first"), vesselType=("vesselType", "first"), flag=("flag", "first"),
        box=("box", "first"), t_in=("t_in", "min"), t_out=("t_out", "max"), hours=("hours", "sum"),
        speed=("speed", "mean"),
    ).reset_index(drop=True)


def detect(west, east):
    """Return one row per deduplicated crossing."""
    pres = pd.concat([west.assign(box="west"), east.assign(box="east")], ignore_index=True)
    v = visits(pres).sort_values(["vesselId", "t_in", "t_out"]).reset_index(drop=True)
    nxt = v.groupby("vesselId").shift(-1)
    gap_h = (nxt["t_in"] - v["t_out"]).dt.total_seconds() / 3600
    is_cross = nxt["box"].notna() & (nxt["box"] != v["box"]) & (gap_h <= MAX_GAP_H)
    c = v[is_cross].copy()
    nx = nxt[is_cross]
    c["direction"] = c["box"].map({"west": "outbound", "east": "inbound"})
    c["overlap"] = gap_h[is_cross] <= 0  # seen in both boxes in the same hour (should not happen)
    c["time"] = c["t_out"] + (nx["t_in"] - c["t_out"]) / 2
    c["gap_h"] = gap_h[is_cross]
    c["vclass"] = [vessel_class(g, t) for g, t in zip(c["geartype"], c["vesselType"])]
    c = c.sort_values(["vesselId", "time"])
    keep, last = [], {}
    for vid, t in zip(c["vesselId"], c["time"]):
        ok = vid not in last or (t - last[vid]) >= pd.Timedelta(hours=DEDUP_H)
        keep.append(ok)
        if ok:
            last[vid] = t
    c = c[keep]
    cols = ["time", "vesselId", "mmsi", "shipName", "flag", "geartype", "vesselType", "vclass",
            "direction", "gap_h", "overlap"]
    return c[cols].sort_values("time").reset_index(drop=True)


def daily_counts(crossings, start=None, end=None):
    """Daily (UTC) crossing counts by vessel class and direction, with zero-filled days."""
    c = crossings.copy()
    c["day"] = c["time"].dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    wide = c.pivot_table(index="day", columns=["vclass", "direction"], values="vesselId",
                         aggfunc="count", fill_value=0)
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    idx = pd.date_range(start or wide.index.min(), end or wide.index.max(), freq="D", name="day")
    wide = wide.reindex(idx, fill_value=0)
    for cls in sorted({col.rsplit("_", 1)[0] for col in wide.columns}):
        wide[f"{cls}_total"] = wide.get(f"{cls}_inbound", 0) + wide.get(f"{cls}_outbound", 0)
    return wide
