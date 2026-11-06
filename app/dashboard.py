"""Hormuz Ships & Oil: live dashboard.

Run:  .venv/bin/streamlit run app/dashboard.py
"""
import subprocess
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.data import daily_crossings, main_prices  # noqa: E402
from hormuz.live import sample  # noqa: E402

TANKER_IN, TANKER_OUT, BRENT = "#2a78d6", "#9cc2ef", "#0b0b0b"

st.set_page_config(page_title="Hormuz Ships & Oil", page_icon="🛢️", layout="wide")


@st.cache_data(ttl=600)
def load():
    d = daily_crossings()
    d = d[d["vessel_hours"] > 0]  # days with no GFW data at all are unknown, not zero
    px = main_prices()
    return d, px


@st.cache_data(ttl=600, show_spinner="Listening to aisstream.io for 20 seconds...")
def live_sample():
    return sample(20)


d, px = load()
last_day = d.index.max()
lag_days = (pd.Timestamp.today().normalize() - last_day).days
brent = px["brent"].dropna()

st.title("Can ships predict oil prices?")
st.caption("Tanker crossings through the Strait of Hormuz vs. Brent crude. A Year 13 independent research project. "
           "Ship data: **Powered by [Global Fishing Watch](https://globalfishingwatch.org)** (CC BY-NC 4.0, non-commercial). "
           "Public website: [yousuf6273.github.io/hormuz-ships-oil](https://yousuf6273.github.io/hormuz-ships-oil/).")

# --- headline numbers -------------------------------------------------------
row = d.loc[last_day]
avg28 = d["tanker_total"].loc[last_day - pd.Timedelta(days=28): last_day - pd.Timedelta(days=1)].mean()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest ship data", last_day.strftime("%d %b %Y"), f"{lag_days} days behind today", delta_color="off")
c2.metric("Tanker crossings that day", int(row["tanker_total"]), f"{row['tanker_total'] - avg28:+.1f} vs 28-day average")
c3.metric("In / out of the Gulf", f"{int(row['tanker_inbound'])} / {int(row['tanker_outbound'])}")
c4.metric(f"Brent, {brent.index[-1]:%d %b}", f"${brent.iloc[-1]:.2f}", f"{100 * (brent.iloc[-1] / brent.iloc[-2] - 1):+.1f}% on the day")
st.info("**Why the delay?** Free live AIS (aisstream.io) has no receivers in the strait right now (see the live panel below), "
        "so this dashboard uses Global Fishing Watch, which publishes about 3 to 6 days after the fact.", icon="ℹ️")

# --- 90-day chart -------------------------------------------------------------
st.subheader("Last 90 days: tanker crossings (top) and Brent (bottom)")
start = last_day - pd.Timedelta(days=89)
ships = d.loc[start:, ["tanker_inbound", "tanker_outbound"]].reset_index().rename(columns={"day": "date"})
ships = ships.melt("date", var_name="direction", value_name="crossings")
ships["direction"] = ships["direction"].map({"tanker_inbound": "In (into the Gulf)", "tanker_outbound": "Out (leaving)"})
oil = brent.loc[start:].rename("brent").reset_index()
domain = [start.isoformat(), (brent.index.max() + pd.Timedelta(days=1)).isoformat()]
x = alt.X("date:T", title=None, scale=alt.Scale(domain=domain))
top = alt.Chart(ships).mark_bar().encode(
    x=x, y=alt.Y("crossings:Q", title="tanker crossings / day", stack=True),
    color=alt.Color("direction:N", scale=alt.Scale(range=[TANKER_IN, TANKER_OUT]), legend=alt.Legend(orient="top", title=None)),
    tooltip=[alt.Tooltip("date:T", format="%a %d %b %Y"), "direction:N", "crossings:Q"],
).properties(height=220)
bottom = alt.Chart(oil).mark_line(color=BRENT, strokeWidth=2, point=alt.OverlayMarkDef(size=18, color=BRENT)).encode(
    x=x, y=alt.Y("brent:Q", title="Brent, $ per barrel", scale=alt.Scale(zero=False)),
    tooltip=[alt.Tooltip("date:T", format="%a %d %b %Y"), alt.Tooltip("brent:Q", format="$.2f")],
).properties(height=200)
st.altair_chart(alt.vconcat(top, bottom).resolve_scale(x="shared"), use_container_width=True)
before = d["tanker_total"].loc["2025-01-01":"2026-02-27"].mean()
st.caption(f"For scale: from Jan 2025 to Feb 2026, before the March 2026 restrictions, about {before:.0f} tankers crossed per day.")

# --- findings ---------------------------------------------------------------------
st.subheader("Key findings (pre-registered study, full details in RESULTS.md)")
st.markdown("""
- **In normal times (2022 to mid-2025), ships do not predict oil, and oil does not predict ships.** A 10% drop in tanker crossings
  was followed by Brent moving about −0.1% (wrong direction, not significant). The model also failed the held-out test (Jul 2025 onwards).
- **In the March 2026 crisis, both reacted to the same news, and oil moved first.** Brent rose about 8% more than stocks explain in the
  two weeks *before* ships stopped (weak evidence, t = 1.3). Ships stopped over the weekend of 28 Feb to 1 Mar; Brent jumped +7% at
  Monday's close, its first chance to react.
- **After the closure, oil kept moving (+57% vs stocks by day 20) while crossings stayed near zero.** Ship counts had nothing new to say.
- **Cargo ships (the placebo) show no signal either.**
""")
with st.expander("Charts from the study"):
    for f in ("event_study.png", "crossings_vs_brent.png", "lead_lag.png"):
        st.image(str(ROOT / "figures" / f), use_container_width=True)

# --- update -----------------------------------------------------------------------
st.subheader("Update the data")
st.caption("Re-downloads the last 2 months of GFW data and the latest prices, then rebuilds the counts (a few minutes).")
if st.button("Update now"):
    with st.status("Updating...", expanded=True) as status:
        proc = subprocess.Popen([sys.executable, str(ROOT / "scripts/update_latest.py")], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, cwd=ROOT)
        for line in proc.stdout:
            if line.strip() and "Warning" not in line:
                st.write(line.strip())
        ok = proc.wait() == 0
        status.update(label="Updated" if ok else "Update failed (see messages above)", state="complete" if ok else "error")
    load.clear()
    if ok:
        st.rerun()

# --- live AIS (last, because listening takes 20 seconds) ---------------------------
st.subheader("Live AIS right now (aisstream.io)")
if st.button("Listen again"):
    live_sample.clear()
res = live_sample()
h, w = res["hormuz"], res["world_check"]
if "error" in h:
    st.error(f"Live feed error: {h['error']}")
else:
    l1, l2 = st.columns(2)
    l1.metric("Positions from the Hormuz area (20 s)", h["positions"], f"{h['vessels']} ships", delta_color="off")
    l2.metric("Positions worldwide (5 s check)", w.get("positions", "error"), "feed is working" if w.get("positions") else "feed problem",
              delta_color="off")
    if h["positions"] == 0:
        st.warning("No live positions from the strait. The free feed's volunteer receivers do not cover this water. "
                   "This matches what the yasumorishima/hormuz-ship-tracker project found in Sept 2026.")

st.divider()
st.caption("Data: Global Fishing Watch AIS vessel presence (CC BY-NC 4.0, non-commercial use only); aisstream.io; "
           "Yahoo Finance; FRED, Federal Reserve Bank of St. Louis. Correlation is not causation; AIS misses ships that switch "
           "their transponders off.")
