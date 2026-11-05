# Pre-registered hypotheses and analysis plan

**Project:** Can Ships Predict Oil Prices?
**Question:** Do changes in daily tanker crossings through the Strait of Hormuz lead Brent crude oil price moves, or does the market move first?

This file was written and committed to git **before any shipping or price data was downloaded or looked at**. The git commit date is the proof. Anything changed after that commit is listed under "Deviations" at the bottom, with the date and the reason.

---

## Hypotheses

- **H1.** A drop in daily tanker crossings predicts *higher* Brent returns over the next 1, 3 and 7 trading days.
  - In the regression below this means the crossing coefficient is **negative**.
- **H2.** The effect is *stronger* during disruption periods (especially the March 2026 restrictions) than in normal periods.
  - In the regression this means the disruption interaction term is **negative** (adds to the H1 effect).
- **H3 (placebo).** Non-tanker crossings (cargo, fishing) should **not** predict oil prices.
  - If they do, the tanker "signal" is probably seasonality, noise, or a general "war risk" effect rather than oil supply.

## Held-out test

- **Training period:** start of usable data → 2025-06-30.
- **Test period:** 2025-07-01 → end of usable data.
- Every choice (variables, lags, model settings) is fixed using the training period only.
- The test period is used once, at the end, to score the models. Nothing is tuned on it.
- Note: the March 2026 disruption falls inside the test period. So H2 for March 2026 is a pure out-of-sample check. Earlier disruptions in the training period are listed below.

---

## Definitions (fixed now)

### Crossings
- A **crossing** is a vessel passing the Strait of Hormuz gate line.
  - **Inbound** = east → west (into the Gulf).
  - **Outbound** = west → east (out of the Gulf).
- **Dedup rule:** at most one crossing per vessel per 6 hours.
- **Tanker:** AIS ship type 80–89, or the closest tanker category the data source offers (documented in the data notes before analysis starts).
- `C_d` = number of tanker crossings (both directions) on UTC calendar day `d`.

### Lining up ships with prices (no look-ahead)
- Brent settles around 19:30 UTC, before the UTC day ends. So at the close on trading day `t` we only fully know crossings up to the end of day `t-1`.
- `C~_t` = average daily crossings on calendar days from the previous trading day up to `t-1`.
  - Example: for a Monday, this is the average of Friday, Saturday and Sunday.
- **Main predictor (crossing shock):**
  `X_t = log(1 + C~_t) − log(1 + average C_d over the 28 calendar days before that window)`
  - In plain words: "How does traffic since the last close compare to the past four weeks?" Negative = a drop.
- **Robustness predictors** (reported, not used to decide anything):
  - day-on-day change: `log(1 + C~_t) − log(1 + C~_{t-1})`
  - 7-day average versus the previous 28 days.
  - inbound and outbound counted separately.

### Prices
- Brent = `BZ=F`, WTI = `CL=F`, S&P 500 = `^GSPC`, VIX = `^VIX` (daily, Yahoo Finance via yfinance).
- Daily Brent return `r_t = log(P_t / P_{t-1})`.
- Forward return over `h` days: `R_{t,h} = log(P_{t+h} / P_t)` for `h = 1, 3, 7` trading days.
- Brent trading days are the calendar. Days where any control is missing use the last known value for VIX only; returns are never filled.

---

## Tests

### 1. Lead–lag correlations
- Ships lead oil: `corr(X_t, r_{t+k})` for `k = 0 … 10`.
- Oil leads ships: `corr(r_t, X_{t+k})` for `k = 1 … 10`.
- 21 correlations in total.

### 2. Predictive regression (H1)
- `R_{t,h} = a + b·X_t + c1·SP500_return_t + c2·ΔlogVIX_t + c3·r_t + error`
- Standard errors: Newey–West (handles overlapping returns), lag = max(h, 5).
- H1 is supported in training if `b < 0` and significant after correction (below).

### 3. Granger causality (both directions)
- Two-variable model of `r_t` and `X_t`.
- Number of lags chosen by AIC on the training data (maximum 10).
- Test 1: do past crossings help predict oil returns?
- Test 2: do past oil returns help predict crossings?

### 4. Disruption effect (H2)
- Add a disruption dummy `D_t` and the interaction `X_t·D_t` to the H1 regression.
- Disruption periods, taken from news dates (not from the data):
  1. 2019-05-12 → 2019-07-31: Fujairah tanker sabotage, Gulf of Oman tanker attacks, Stena Impero seizure.
  2. 2024-04-13 → 2024-04-30: MSC Aries seizure and Iran–Israel strikes.
  3. 2025-06-13 → 2025-06-24: Israel–Iran war.
  4. **2026-02-28 → 2026-03-31: March 2026 Hormuz restrictions (primary H2 window).**
- Periods 1–3 are in training (if the data reaches back that far). Period 4 is in the test period.

### 5. Event study (March 2026)
- Event day 0 = **2026-03-02** (first trading day after the 2026-02-28 closure announcement, a Saturday).
- Window: 10 trading days before to 20 after.
- Brent abnormal return = Brent return minus what the S&P 500 would predict (model fitted on days −250 to −30).
- Plot cumulative abnormal return and daily crossings on the same time axis to see which moved first.
- Weekend crossings (Sat/Sun) fall before Monday's trading by construction. This is noted when reading the chart, so a weekend drop is not mistaken for ships "predicting" oil.

### 6. Placebo (H3)
- Re-run test 2 with cargo crossings, then fishing crossings, in place of tanker crossings.
- If fishing crossings average under 1 per day, the fishing placebo is reported but called uninformative.
- Caveat written now: cargo ships also react to war news. So a cargo "signal" during crises could mean shared war risk, not seasonality.

### 7. Held-out evaluation
- Fit the H1 model on training. Forecast `R_{t,h}` in the test period.
- Score: out-of-sample R² versus a "historical average return" forecast, plus a Clark–West test.
- Also re-estimate `b` on the test period alone and check the sign matches.

---

## Correcting for many tests

- Testing many lags and horizons raises the chance of a lucky "significant" result. We correct for this:
  - **H1 (3 horizons):** Holm correction, 5% level. This is the main, confirmatory test.
  - **H2 (3 horizons):** Holm, 5%.
  - **H3 (2 placebos × 3 horizons = 6 tests):** Holm, 5%.
  - **Granger (2 directions):** Holm, 5%.
  - **Lead–lag (21 correlations):** Benjamini–Hochberg, 5% false discovery rate. Treated as exploratory.
- Both raw and corrected p-values are reported.

## What counts as success for H1

H1 is called **supported** only if all three hold:
1. `b < 0` and significant after Holm correction in training, for at least one horizon;
2. the cargo placebo is not significant after Holm for that horizon;
3. out-of-sample R² > 0 in the test period with Clark–West p < 0.05 (one-sided).

Anything less is reported as "not supported" or "mixed", with the numbers. Null results are reported in full.

---

## Deviations

_None yet. Any change after this commit is logged here with the date and reason._
