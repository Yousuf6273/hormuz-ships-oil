# Can Ships Predict Oil Prices?

An independent research project on whether changes in daily tanker crossings through the **Strait of Hormuz** lead **Brent crude** price moves, or whether the market moves first.

- Hypotheses and the full analysis plan were written and committed **before** any data was downloaded: see [HYPOTHESES.md](HYPOTHESES.md).
- Status: core analysis done. **Answer: in normal times, no. In the March 2026 crisis, ships and oil reacted to the same news, with oil moving first.** See [RESULTS.md](RESULTS.md) and [FEASIBILITY.md](FEASIBILITY.md).

## Data sources

| What | Source | Notes |
|---|---|---|
| Historical vessel positions | [Global Fishing Watch](https://globalfishingwatch.org) API, AIS Vessel Presence (`public-global-presence`) | One position per vessel per hour. Licence CC BY-NC 4.0: non-commercial use only. |
| Live vessel positions | [aisstream.io](https://aisstream.io) WebSocket | Free beta. Tankers are AIS ship types 80–89. |
| Prices | Yahoo Finance via `yfinance`: Brent `BZ=F`, WTI `CL=F`, S&P 500 `^GSPC`, VIX `^VIX` | Main source (pre-registered). |
| Backup prices | [FRED](https://fred.stlouisfed.org): `DCOILBRENTEU`, `DCOILWTICO`, `SP500`, `VIXCLS` | Used if Yahoo fails and as a robustness check (spot vs futures). |

**Powered by [Global Fishing Watch](https://globalfishingwatch.org).** Vessel data © Global Fishing Watch, used under CC BY-NC 4.0 for non-commercial research.

## Ideas reused from other projects (with thanks)

- **KaiErikNiermann/hormuz-crossing-tracker**: the 56.5°E dividing meridian and per-vessel dedup idea (as described in the project brief; the repository was no longer public on GitHub when this project started, so no code was read or copied).
- **[yasumorishima/hormuz-ship-tracker](https://github.com/yasumorishima/hormuz-ship-tracker)**: inbound/outbound transit logic, 6-hour dedup window, Dubai/Jebel Ali and Fujairah zones, and the finding that free aisstream coverage of the strait is near zero.
- **[Blurjp/QuantTrade](https://github.com/Blurjp/QuantTrade)**: CFAR radar ship detection on Sentinel-1 (for the optional "dark ships" extension).

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
```

## Repository layout

```
HYPOTHESES.md          pre-registered hypotheses and analysis plan
src/hormuz/            pipeline code (config, GFW download, crossing detection, prices)
scripts/               command-line entry points (pull data, build table, charts, tests)
results/               test outputs (CSV + logs)
feasibility/           data feasibility checks
data/raw/              cached downloads (not committed; rebuild with scripts/)
data/processed/        daily crossing counts
figures/               charts
```
