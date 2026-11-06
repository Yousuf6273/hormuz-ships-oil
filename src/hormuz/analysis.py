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
