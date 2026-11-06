"""Build the public website (GitHub Pages serves the docs/ folder).

Run after updating the data:  .venv/bin/python scripts/build_site.py
Writes docs/index.html plus copies of the paper and the study figures.
"""
import html
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hormuz.data import daily_crossings, main_prices  # noqa: E402

DOCS = ROOT / "docs"
REPO = "https://github.com/Yousuf6273/hormuz-ships-oil"
TANKER_IN, TANKER_OUT, BRENT, TEXT_2, GRID = "#2a78d6", "#9cc2ef", "#0b0b0b", "#52514e", "#e4e3df"
FIGURES = [
    ("crossings_vs_brent.png", "Five years of crossings and Brent",
     "Daily tanker and cargo crossings (7-day average, top) and the Brent price (bottom). Grey bands are disruption "
     "periods; the dashed line starts the held-out test period. Crossings held steady at about 60 a day until March 2026."),
    ("event_study.png", "March 2026: oil moved first",
     "Tanker crossings (top) and Brent's cumulative abnormal return (bottom) around Monday 2 March 2026. Oil rose "
     "before ships stopped, jumped at its first chance after the weekend closure, and kept moving while crossings sat at zero."),
    ("gulf_pulse.png", "Extension: trade moved to Fujairah",
     "Ships present at Dubai's Jebel Ali (inside the Gulf) and Fujairah (outside the strait), as a percentage of 2025. "
     "After the closure Fujairah recovered; Jebel Ali didn't. Exploratory, not pre-registered."),
    ("dark_ships.png", "Extension: were ships hiding?",
     "Satellite radar over the strait. If tankers had kept sailing with AIS switched off, 'dark' detections would have "
     "risen. They fell, so the collapse was real, though dark traffic fell less than AIS traffic. Exploratory."),
]

d = daily_crossings()
d = d[d["vessel_hours"] > 0]  # days with no GFW data at all are unknown, not zero
brent = main_prices()["brent"].dropna()
last = d.index.max()
row = d.loc[last]
avg28 = d["tanker_total"].loc[last - pd.Timedelta(days=28): last - pd.Timedelta(days=1)].mean()
before = d["tanker_total"].loc["2025-01-01":"2026-02-27"].mean()
brent_chg = 100 * (brent.iloc[-1] / brent.iloc[-2] - 1)

# --- 90-day charts: two separate views with one shared date range (never two y-scales) -------------
start = last - pd.Timedelta(days=89)
domain = [start.strftime("%Y-%m-%d"), (brent.index.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")]
ships = d.loc[start:, ["tanker_inbound", "tanker_outbound"]].reset_index().rename(columns={"day": "date"})
ships = ships.melt("date", var_name="direction", value_name="crossings")
ships["direction"] = ships["direction"].map({"tanker_inbound": "In (into the Gulf)", "tanker_outbound": "Out (leaving)"})
ships["date"] = ships["date"].dt.strftime("%Y-%m-%d")
oil = brent.loc[start:].rename("brent").reset_index()
oil["date"] = oil["date"].dt.strftime("%Y-%m-%d")
x = alt.X("date:T", title=None, scale=alt.Scale(domain=domain), axis=alt.Axis(format="%d %b", labelColor=TEXT_2))
cfg = dict(view={"stroke": None}, axis={"gridColor": GRID, "domainColor": GRID, "tickColor": GRID,
                                        "titleColor": TEXT_2, "labelColor": TEXT_2, "titleFontWeight": "normal"})
top = alt.Chart(ships).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
    x=x, y=alt.Y("crossings:Q", title="tanker crossings per day", stack=True),
    color=alt.Color("direction:N", scale=alt.Scale(range=[TANKER_IN, TANKER_OUT]),
                    legend=alt.Legend(orient="top", title=None, labelColor=TEXT_2)),
    tooltip=[alt.Tooltip("date:T", format="%a %d %b %Y", title="Day (UTC)"), alt.Tooltip("direction:N", title="Direction"),
             alt.Tooltip("crossings:Q", title="Crossings")],
).properties(width="container", height=200).configure(**cfg)
bottom = alt.Chart(oil).mark_line(color=BRENT, strokeWidth=2, point=alt.OverlayMarkDef(size=20, color=BRENT)).encode(
    x=x, y=alt.Y("brent:Q", title="Brent, $ per barrel", scale=alt.Scale(zero=False)),
    tooltip=[alt.Tooltip("date:T", format="%a %d %b %Y", title="Close"), alt.Tooltip("brent:Q", format="$.2f", title="Brent")],
).properties(width="container", height=180).configure(**cfg)

# --- copy the paper and figures next to the page ---------------------------------------------------
(DOCS / "figures").mkdir(parents=True, exist_ok=True)
shutil.copy(ROOT / "paper/paper.pdf", DOCS / "paper.pdf")
for f, _, _ in FIGURES:
    shutil.copy(ROOT / "figures" / f, DOCS / "figures" / f)
(DOCS / ".nojekyll").write_text("")

figs = "\n".join(
    f'<figure><h3>{html.escape(t)}</h3><a href="figures/{f}"><img src="figures/{f}" alt="{html.escape(t)}" loading="lazy"></a>'
    f"<figcaption>{html.escape(c)}</figcaption></figure>" for f, t, c in FIGURES)

page = (ROOT / "scripts/site_template.html").read_text()
for key, val in {
    "{{REPO}}": REPO,
    "{{LAST_DAY}}": last.strftime("%d %b %Y"),
    "{{CROSSINGS}}": str(int(row["tanker_total"])),
    "{{IN}}": str(int(row["tanker_inbound"])),
    "{{OUT}}": str(int(row["tanker_outbound"])),
    "{{AVG28}}": f"{avg28:.1f}",
    "{{BEFORE}}": f"{before:.0f}",
    "{{BRENT_DAY}}": brent.index[-1].strftime("%d %b %Y"),
    "{{BRENT}}": f"${brent.iloc[-1]:.2f}",
    "{{BRENT_CHG}}": f"{brent_chg:+.1f}%",
    "{{FIGURES}}": figs,
    "{{SPEC_SHIPS}}": json.dumps(top.to_dict()),
    "{{SPEC_BRENT}}": json.dumps(bottom.to_dict()),
    "{{BUILT}}": datetime.now(timezone.utc).strftime("%d %b %Y"),
}.items():
    page = page.replace(key, val)
(DOCS / "index.html").write_text(page)
print(f"Wrote docs/index.html (ship data to {last:%Y-%m-%d}, Brent to {brent.index[-1]:%Y-%m-%d})")
