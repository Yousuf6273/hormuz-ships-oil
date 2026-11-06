# Can Ships Predict Oil Prices?

**🌐 Website: [yousuf6273.github.io/hormuz-ships-oil](https://yousuf6273.github.io/hormuz-ships-oil/)** · **📄 [Paper (PDF)](paper/paper.pdf)** · **📊 [All results](RESULTS.md)**

An independent research project on whether changes in daily tanker crossings through the **Strait of Hormuz** lead **Brent crude** price moves, or whether the market moves first.

- Hypotheses and the full analysis plan were written and committed **before** any data was downloaded: see [HYPOTHESES.md](HYPOTHESES.md).
- **Answer: in normal times, no. In the March 2026 crisis, ships and oil reacted to the same news, with oil moving first.** The pre-registered hypothesis H1 is not supported.
- **Read the paper:** [paper/paper.pdf](paper/paper.pdf) (6 pages, plain English). Full numbers: [RESULTS.md](RESULTS.md). Data checks: [FEASIBILITY.md](FEASIBILITY.md).
- **Extensions** (exploratory, not pre-registered):
  - **Gulf trade pulse:** after the closure, trade moved to Fujairah (outside the strait) while Dubai's Jebel Ali stayed at about a quarter of normal.
  - **Dark ships:** satellite radar confirms the collapse in traffic was real, though some ships kept moving without AIS.
- **Live dashboard:** latest crossings, 90-day chart vs Brent, a live aisstream check and the key findings (see "Dashboard" below).

## Data sources

| What | Source | Notes |
|---|---|---|
| Historical vessel positions | [Global Fishing Watch](https://globalfishingwatch.org) API, AIS Vessel Presence (`public-global-presence`) | One position per vessel per hour. Licence CC BY-NC 4.0: non-commercial use only. |
| Live vessel positions | [aisstream.io](https://aisstream.io) WebSocket | Free beta. Tankers are AIS ship types 80–89. |
| Prices | Yahoo Finance via `yfinance`: Brent `BZ=F`, WTI `CL=F`, S&P 500 `^GSPC`, VIX `^VIX` | Main source (pre-registered). |
| Backup prices | [FRED](https://fred.stlouisfed.org): `DCOILBRENTEU`, `DCOILWTICO`, `SP500`, `VIXCLS` | Used if Yahoo fails and as a robustness check (spot vs futures). S&P 500 and WTI come from here because this network blocks Yahoo for them. |
| Satellite radar ship detections | Global Fishing Watch API, SAR vessel detections (`public-global-sar-presence`) | Sentinel-1 radar, matched or not to AIS. Dark-ships extension only. |

**Powered by [Global Fishing Watch](https://globalfishingwatch.org).** Vessel and radar data © Global Fishing Watch, used under CC BY-NC 4.0 for non-commercial research.

## Ideas reused from other projects (with thanks)

- **KaiErikNiermann/hormuz-crossing-tracker**: the 56.5°E dividing meridian and per-vessel dedup idea (as described in the project brief; the repository was no longer public on GitHub when this project started, so no code was read or copied).
- **[yasumorishima/hormuz-ship-tracker](https://github.com/yasumorishima/hormuz-ship-tracker)**: inbound/outbound transit logic, 6-hour dedup window, Dubai/Jebel Ali and Fujairah zones, and the finding that free aisstream coverage of the strait is near zero.
- **[Blurjp/QuantTrade](https://github.com/Blurjp/QuantTrade)**: CFAR radar ship detection on Sentinel-1, the idea behind the "dark ships" extension. This project used Global Fishing Watch's ready-made Sentinel-1 detections instead of running its own detector.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then paste your GFW token and aisstream key into .env
```

## Reproduce

```bash
.venv/bin/python scripts/pull_gfw.py 2012-01 2026-11   # ~1 hour, cached by month
.venv/bin/python scripts/pull_prices.py
.venv/bin/python feasibility/summarize.py              # daily crossings + coverage report
.venv/bin/python scripts/build_table.py
.venv/bin/python scripts/make_charts.py
.venv/bin/python scripts/run_leadlag_granger.py
.venv/bin/python scripts/run_regressions.py
.venv/bin/python scripts/run_event_oos.py
.venv/bin/python scripts/run_robustness.py
.venv/bin/python -m pytest -q tests

# extensions (exploratory)
.venv/bin/python scripts/pull_zones.py 2022-01 2026-11   # Jebel Ali + Fujairah port zones, ~30 min
.venv/bin/python scripts/run_pulse.py
.venv/bin/python scripts/pull_sar.py 2022-01 2026-11     # satellite radar detections, ~3 min
.venv/bin/python scripts/run_dark.py

# paper (needs Google Chrome for the PDF step)
.venv/bin/python paper/build.py

# website (GitHub Pages serves docs/): rebuild and push it
.venv/bin/python scripts/publish_site.py
```

## Dashboard

**One click (Mac):** run this once, then double-click **Hormuz Dashboard** on your Desktop. It starts the dashboard (if it isn't already running) and opens it in your browser.

```bash
bash scripts/make_mac_app.sh
```

Or start it by hand:

```bash
.venv/bin/streamlit run app/dashboard.py
```

- Shows the latest day of GFW data (about 3–6 days behind), tanker crossings in and out, a 90-day chart of crossings above Brent, and the key findings.
- **Update data and website** re-downloads the last 2 months of GFW data and the latest prices, rebuilds the counts, then rebuilds the public website and pushes it to GitHub (`scripts/update_latest.py --publish`). About a minute later, the website's **↻ Refresh** button shows the new data to anyone viewing it.
- The website can't download ship data by itself: that would put the GFW key on a public page. So new data always comes from this dashboard (or `scripts/publish_site.py`).
- The **live AIS** panel listens to aisstream.io for 20 seconds. It currently receives nothing from the strait (free receivers don't cover it), and says so. A 5-second worldwide check shows the feed itself is working.

## Repository layout

```
HYPOTHESES.md          pre-registered hypotheses and analysis plan
RESULTS.md             all results, extensions and limits
paper/                 the paper (paper.md -> paper.pdf via build.py)
app/dashboard.py       Streamlit dashboard
src/hormuz/            pipeline code (config, GFW + radar download, crossing detection, prices, live AIS)
scripts/               command-line entry points (pull data, build table, charts, tests, extensions)
results/               test outputs (CSV + logs)
feasibility/           data feasibility checks
data/raw/              cached downloads (not committed; rebuild with scripts/)
data/processed/        daily crossing counts, analysis table, port and radar series
figures/               charts
```

## Licence and use

Non-commercial research only, because the Global Fishing Watch data is CC BY-NC 4.0. Code was written with help from an AI coding assistant (Claude, by Anthropic).
