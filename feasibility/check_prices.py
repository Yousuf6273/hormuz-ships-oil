"""Feasibility check: can we get daily Brent, WTI, S&P 500 and VIX, and do they line up?"""
import pandas as pd
import yfinance as yf

TICKERS = {"brent": "BZ=F", "wti": "CL=F", "sp500": "^GSPC", "vix": "^VIX"}

closes = {}
for name, tic in TICKERS.items():
    df = yf.download(tic, start="2012-01-01", progress=False, auto_adjust=False)
    s = df["Close"].squeeze().dropna()
    closes[name] = s
    gaps = s.index.to_series().diff().dt.days
    print(f"{name:6s} {tic:6s} rows={len(s):5d}  {s.index.min().date()} -> {s.index.max().date()}  "
          f"longest gap={int(gaps.max())} days  non-positive prices={(s <= 0).sum()}")

px = pd.DataFrame(closes)
brent_days = px["brent"].dropna().index
print("\nOn Brent trading days, share of days each other series is missing:")
print(px.loc[brent_days].isna().mean().round(4).to_string())

print("\nBrent trading days per year:")
print(brent_days.year.value_counts().sort_index().to_string())
