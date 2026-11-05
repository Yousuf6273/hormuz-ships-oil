"""Daily closing prices.

Main source (pre-registered): Yahoo Finance via yfinance -- Brent BZ=F, WTI CL=F, S&P 500 ^GSPC, VIX ^VIX.
Backup / robustness source: FRED (St. Louis Fed) -- Brent spot DCOILBRENTEU, WTI spot DCOILWTICO,
S&P 500 SP500 (FRED only keeps the last 10 years), VIX VIXCLS.

Each series is cached under data/raw/prices/ as soon as it downloads, because Yahoo
rate-limits often and a later failure should not throw away a good earlier download.
"""
import io
import time

import pandas as pd
import requests
import yfinance as yf

from .config import RAW

YAHOO = {"brent": "BZ=F", "wti": "CL=F", "sp500": "^GSPC", "vix": "^VIX"}
FRED = {"brent": "DCOILBRENTEU", "wti": "DCOILWTICO", "sp500": "SP500", "vix": "VIXCLS"}
DIR = RAW / "prices"


def _save(s, source, name):
    s = s.dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    s.index.name = "date"
    DIR.mkdir(parents=True, exist_ok=True)
    s.rename(name).to_frame().to_parquet(DIR / f"{source}_{name}.parquet")
    return s


def pull_yahoo(name, start="2012-01-01", tries=4):
    for attempt in range(tries):
        df = yf.download(YAHOO[name], start=start, progress=False, auto_adjust=False)
        if not df.empty:
            return _save(df["Close"].squeeze(), "yahoo", name)
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"Yahoo returned no data for {YAHOO[name]} after {tries} tries")


def pull_fred(name):
    r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": FRED[name]}, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    s = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s.index = pd.to_datetime(df.iloc[:, 0])
    return _save(s, "fred", name)


def pull_all(refresh=False):
    """Download every series that is not cached yet. Returns {(source, name): 'ok' | error}."""
    status = {}
    for source, puller in (("yahoo", pull_yahoo), ("fred", pull_fred)):
        for name in YAHOO:
            if (DIR / f"{source}_{name}.parquet").exists() and not refresh:
                status[(source, name)] = "cached"
                continue
            try:
                puller(name)
                status[(source, name)] = "ok"
            except Exception as e:  # report, never hide
                status[(source, name)] = f"FAILED: {e}"
    return status


def load_prices(source="yahoo"):
    """Wide table of closes (brent, wti, sp500, vix) from one source; missing series are absent."""
    cols = []
    for name in YAHOO:
        f = DIR / f"{source}_{name}.parquet"
        if f.exists():
            cols.append(pd.read_parquet(f)[name])
    if not cols:
        raise FileNotFoundError(f"No cached {source} prices; run scripts/pull_prices.py")
    return pd.concat(cols, axis=1).sort_index()
