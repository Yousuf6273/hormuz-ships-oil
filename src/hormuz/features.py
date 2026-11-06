"""Build the analysis table exactly as defined in HYPOTHESES.md.

One row per Brent trading day t:
  ship variables use crossings up to the end of UTC day t-1 only (no look-ahead),
  price variables are log returns, forward returns R_{t,h} = log(P_{t+h} / P_t).
"""
import numpy as np
import pandas as pd

BASELINE_DAYS = 28
HORIZONS = (1, 3, 7)


def ship_features(daily, trade_days, col):
    """Crossing shock and robustness versions for one daily count column.

    daily: calendar-day (UTC) frame with `col` and `vessel_hours`; trade_days: sorted DatetimeIndex.
    """
    c = daily[col].astype(float).copy()
    c[daily["vessel_hours"] <= 0] = np.nan  # no GFW data at all that day -> unknown, not zero
    cs = c.fillna(0).cumsum()
    n = c.notna().astype(int).cumsum()

    def window_mean(first, last):
        """Mean of available days in [first, last] (inclusive), NaN if none."""
        lo, hi = first - pd.Timedelta(days=1), last
        tot = cs.reindex([hi]).values - cs.reindex([lo]).fillna(0).values
        cnt = n.reindex([hi]).values - n.reindex([lo]).fillna(0).values
        return float(tot[0] / cnt[0]) if cnt[0] > 0 else np.nan

    out = []
    prev = trade_days[0] - pd.Timedelta(days=1)
    for t in trade_days:
        w_first, w_last = prev, t - pd.Timedelta(days=1)          # since last close, up to t-1
        base_first, base_last = w_first - pd.Timedelta(days=BASELINE_DAYS), w_first - pd.Timedelta(days=1)
        last7_first = w_last - pd.Timedelta(days=6)
        b7_first, b7_last = last7_first - pd.Timedelta(days=BASELINE_DAYS), last7_first - pd.Timedelta(days=1)
        out.append((t, window_mean(w_first, w_last), window_mean(base_first, base_last),
                    window_mean(last7_first, w_last), window_mean(b7_first, b7_last)))
        prev = t
    f = pd.DataFrame(out, columns=["date", "c_win", "c_base", "c_7", "c_base7"]).set_index("date")
    res = pd.DataFrame(index=f.index)
    res[f"{col}_shock"] = np.log1p(f["c_win"]) - np.log1p(f["c_base"])
    res[f"{col}_dd"] = np.log1p(f["c_win"]) - np.log1p(f["c_win"].shift(1))
    res[f"{col}_shock7"] = np.log1p(f["c_7"]) - np.log1p(f["c_base7"])
    res[f"{col}_level"] = f["c_win"]
    return res


def price_features(px):
    """Returns on Brent trading days. VIX is forward-filled (the only fill allowed); returns are never filled."""
    b = px["brent"].dropna()
    b = b[b > 0]
    days = b.index
    p = px.reindex(days)
    p["vix"] = px["vix"].ffill().reindex(days)
    res = pd.DataFrame(index=days)
    res["brent_ret"] = np.log(b / b.shift(1))
    for h in HORIZONS:
        res[f"brent_fwd{h}"] = np.log(b.shift(-h) / b)
    wti = p["wti"].where(p["wti"] > 0)
    res["wti_ret"] = np.log(wti / wti.shift(1))
    for h in HORIZONS:
        res[f"wti_fwd{h}"] = np.log(wti.shift(-h) / wti)
    res["sp500_ret"] = np.log(p["sp500"] / p["sp500"].shift(1))
    res["dlog_vix"] = np.log(p["vix"] / p["vix"].shift(1))
    return res


def build_table(daily, px, ship_cols=("tanker_total", "tanker_inbound", "tanker_outbound",
                                      "cargo_total", "fishing_total", "cargo_or_tanker_total")):
    pf = price_features(px)
    days = pf.index[(pf.index > daily.index.min() + pd.Timedelta(days=BASELINE_DAYS + 7))
                    & (pf.index <= daily.index.max() + pd.Timedelta(days=1))]
    parts = [pf.loc[days]]
    for col in ship_cols:
        if col in daily:
            parts.append(ship_features(daily, days, col))
    return pd.concat(parts, axis=1)
