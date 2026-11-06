"""Statistical tests from HYPOTHESES.md. Every function takes the analysis table already cut to one period."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.api import VAR

from .features import HORIZONS

CONTROLS = ["sp500_ret", "dlog_vix", "brent_ret"]


def hac_ols(y, X, lags):
    """OLS with Newey-West (HAC) standard errors; drops rows with any missing value."""
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def correct(pvals, method):
    """Holm or Benjamini-Hochberg adjusted p-values (method 'holm' or 'fdr_bh')."""
    p = np.asarray(pvals, dtype=float)
    ok = ~np.isnan(p)
    out = np.full_like(p, np.nan)
    if ok.any():
        out[ok] = multipletests(p[ok], method=method)[1]
    return out


def lead_lag(t, x, ret="brent_ret", max_lag=10):
    """Correlations at lags 0..max_lag in both directions, with HAC p-values and BH correction.

    ships_lead k: corr(x_t, ret_{t+k}), k = 0..max_lag
    oil_leads  k: corr(ret_t, x_{t+k}), k = 1..max_lag
    """
    rows = []
    for k in range(0, max_lag + 1):
        y = t[ret].shift(-k)
        fit = hac_ols(y.rename("y"), t[[x]], lags=5)
        rows.append(("ships_lead", k, t[x].corr(y), fit.pvalues[x], int(fit.nobs)))
    for k in range(1, max_lag + 1):
        y = t[x].shift(-k)
        fit = hac_ols(y.rename("y"), t[[ret]], lags=5)
        rows.append(("oil_leads", k, t[ret].corr(y), fit.pvalues[ret], int(fit.nobs)))
    out = pd.DataFrame(rows, columns=["direction", "lag", "corr", "p_raw", "n"])
    out["p_bh"] = correct(out["p_raw"], "fdr_bh")
    return out


def granger(t, x, ret="brent_ret", max_lag=10, lags=None):
    """Two-variable VAR; F-tests in both directions with Holm correction.

    lags=None chooses the lag length by AIC (max 10) -- used on training data only.
    Pass the training choice as `lags` when testing another period, as pre-registered.
    """
    d = t[[ret, x]].dropna().reset_index(drop=True)
    if lags is None:
        lags = max(VAR(d).select_order(maxlags=max_lag).aic, 1)
    fit = VAR(d).fit(lags)
    lag = lags
    rows = []
    for caused, causing, label in ((ret, x, "ships -> oil"), (x, ret, "oil -> ships")):
        res = fit.test_causality(caused, [causing], kind="f")
        rows.append((label, lag, float(res.test_statistic), float(res.pvalue), int(fit.nobs)))
    out = pd.DataFrame(rows, columns=["direction", "lags_aic", "F", "p_raw", "n"])
    out["p_holm"] = correct(out["p_raw"], "holm")
    return out


def drop_tail(t, h):
    """Drop the last h rows so h-day forward returns never use prices from outside the period."""
    return t.iloc[:-h] if h > 0 else t


def predictive(t, x, h, ret="brent", extra=()):
    """R_{t,h} = a + b*x_t + controls (+ extra regressors); Newey-West lag max(h, 5)."""
    t = drop_tail(t, h)
    X = t[[x, *CONTROLS, *extra]]
    return hac_ols(t[f"{ret}_fwd{h}"].rename("y"), X, lags=max(h, 5))


def per_10pct_drop(b):
    """Change in h-day return (in %) that follows a 10% drop in crossings: x = log(0.9)."""
    return 100 * b * np.log(0.9)


def h1_table(t, x="tanker_total_shock", ret="brent"):
    rows = []
    for h in HORIZONS:
        f = predictive(t, x, h, ret)
        rows.append((x, h, f.params[x], f.bse[x], f.pvalues[x], per_10pct_drop(f.params[x]), f.rsquared, int(f.nobs)))
    out = pd.DataFrame(rows, columns=["predictor", "h", "b", "se", "p_raw", "ret_pct_after_10pct_drop", "r2", "n"])
    out["p_holm"] = correct(out["p_raw"], "holm")
    return out


def h2_table(t, dummy, x="tanker_total_shock", ret="brent"):
    """Adds disruption dummy D and x*D. H2 predicts the interaction is negative."""
    t = t.assign(D=dummy.reindex(t.index).fillna(0).astype(float))
    t = t.assign(xD=t[x] * t["D"])
    rows = []
    for h in HORIZONS:
        f = predictive(t, x, h, ret, extra=("D", "xD"))
        rows.append((h, f.params[x], f.params["xD"], f.bse["xD"], f.pvalues["xD"], int(t["D"].sum()), int(f.nobs)))
    out = pd.DataFrame(rows, columns=["h", "b_normal", "b_extra_in_disruption", "se", "p_raw", "disruption_days", "n"])
    out["p_holm"] = correct(out["p_raw"], "holm")
    return out


def dummy_for(index, periods):
    d = pd.Series(0, index=index)
    for start, end in periods:
        d.loc[start:end] = 1
    return d
