"""The rolling evaluation of the extension (notebook 12): one portfolio path per specification, month by month.

A path is one variant (a covariance estimator, or the robust portfolio built from all of them) under one
constraint set. It starts as the index. In every evaluation month the covariance is estimated on the data before
the month, the optimiser solves for the weights with the drifted previous weights as the turnover reference, the
portfolio and the benchmark earn the month's returns, and the active return, the forecast tracking error, the
turnover and the state of the cap are recorded. The measures of a path are computed from its records: realised
tracking error, forecast tracking error and its calibration, active return gross and net of trading costs,
turnover and relaxed-cap months, holdings.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C
from . import optimiser as O

PERIODS_PER_YEAR = 12


def run_path(months, Sigmas, weights: pd.DataFrame, returns: pd.DataFrame, constraints: tuple,
             tilt_mask: np.ndarray, exclude_mask: np.ndarray | None, robust: bool = False, keep_weights: bool = False) -> pd.DataFrame:
    """One path. `Sigmas` maps a month to its covariance (or to the list of covariances when `robust`).

    Returns one record per month: forecast tracking error (per year), active return, one-way turnover, the cap
    used and whether it was relaxed, the effective number of holdings, the industries held, and the weights when
    asked. The previous portfolio of the first month is the benchmark of that month (constants.EVAL_START_PORTFOLIO).
    """
    records = []
    w_prev = None
    prev_month = None
    for month in months:
        b = weights.loc[month].to_numpy()
        r = returns.loc[month].to_numpy()
        if w_prev is None:
            w0 = b.copy()
            b_drift = b.copy()
        else:
            w0 = O.drifted_weights(w_prev, returns.loc[prev_month].to_numpy())
            b_drift = O.drifted_weights(weights.loc[prev_month].to_numpy(), returns.loc[prev_month].to_numpy())
        kwargs = dict(w_prev=w0, tilt_mask=tilt_mask, exclude_mask=exclude_mask)
        sol = O.solve_robust(Sigmas[month], b, constraints, **kwargs) if robust else O.solve(Sigmas[month], b, constraints, **kwargs)
        rec = {"month": month, "forecast_te": sol.tracking_error, "active_return": float(sol.weights @ r - b @ r),
               "turnover": sol.turnover, "cap_used": sol.turnover_cap_used if "turnover_cap" in constraints else np.nan,
               "relaxed": bool(sol.relaxed), "effective_number": O.effective_number(sol.weights), "held": int((sol.weights > 1e-6).sum()),
               "status": sol.status,
               "benchmark_turnover": O.one_way_turnover(b, b_drift)}       # the index's own turnover: how far its weights moved beyond what its returns did
        if keep_weights:
            rec["weights"] = sol.weights
        records.append(rec)
        w_prev, prev_month = sol.weights, month
    return pd.DataFrame(records).set_index("month")


def realised_tracking_error(active: pd.Series | np.ndarray) -> float:
    """The standard deviation of the monthly active returns, times the square root of 12."""
    return float(np.std(np.asarray(active, dtype=float), ddof=1) * np.sqrt(PERIODS_PER_YEAR))


def bias_statistic(active: np.ndarray, forecast_te: np.ndarray, scale: np.ndarray | None = None) -> float:
    """sd(active return / forecast monthly standard deviation); `scale` multiplies the forecast variance (the variance-ratio
    correction). nan when a forecast is zero, as under the sets in which the portfolio is the benchmark."""
    f = np.asarray(forecast_te, dtype=float) / np.sqrt(PERIODS_PER_YEAR)
    if scale is not None:
        f = f * np.sqrt(np.asarray(scale, dtype=float))
    if (np.asarray(forecast_te, dtype=float) <= C.OPT_TOL_TE).any():     # a forecast of zero (the portfolio is the benchmark) has no calibration
        return float("nan")
    return float(np.std(np.asarray(active, dtype=float) / f, ddof=1))


def summarise(path: pd.DataFrame, vr_scale: pd.Series | None = None) -> dict:
    """The measures of one path, in return units per year where they are returns or risks."""
    active = path["active_return"].to_numpy()
    te = realised_tracking_error(active)
    gross = PERIODS_PER_YEAR * float(np.mean(active))
    turnover = float(path["turnover"].mean())
    out = {"realised TE": te, "forecast TE (mean)": float(path["forecast_te"].mean()),
           "bias": bias_statistic(active, path["forecast_te"].to_numpy()),
           "bias (variance ratio)": bias_statistic(active, path["forecast_te"].to_numpy(), None if vr_scale is None else vr_scale.loc[path.index].to_numpy()),
           "active return (gross)": gross, "turnover (one-way)": turnover, "benchmark turnover": float(path["benchmark_turnover"].mean()),
           "relaxed months": int(path["relaxed"].sum()), "relaxed share": float(path["relaxed"].mean()),
           "inaccurate months": int((path["status"] != "optimal").sum()),
           "effective number": float(path["effective_number"].mean()), "industries held": float(path["held"].mean())}
    for c in C.EXT_COST_LEVELS:
        bp = int(round(c * 1e4))
        cost = PERIODS_PER_YEAR * turnover * c
        out[f"cost at {bp} bp"] = cost
        out[f"net active return at {bp} bp"] = gross - cost
        out[f"information ratio at {bp} bp"] = (gross - cost) / te if te > C.OPT_TOL_TE else float("nan")   # no ratio for a portfolio that is the benchmark
    return out


def by_decade(path: pd.DataFrame, first_label: str, last_label: str) -> pd.Series:
    """Realised tracking error by decade of the evaluation month; the first and last partial decades carry the given labels."""
    def label(m):
        if m.year < 1990:
            return first_label
        if m.year >= 2020:
            return last_label
        return f"{(m.year // 10) * 10}s"
    groups = pd.Series([label(m) for m in path.index], index=path.index)
    return path.groupby(groups)["active_return"].apply(realised_tracking_error)


def calibrated_forecast(path: pd.DataFrame, window: int = C.EVAL_CALIBRATION_WINDOW, minimum: int = C.EVAL_CALIBRATION_MIN) -> pd.Series:
    """The forecast tracking error of month t multiplied by the ratio of realised to forecast tracking error over the
    previous `window` months of the same path (square root of the mean squared active return over the mean forecast
    variance), using only months before t; unchanged while fewer than `minimum` months are available."""
    f_var = (path["forecast_te"] / np.sqrt(PERIODS_PER_YEAR)) ** 2
    a2 = path["active_return"] ** 2
    num = a2.shift(1).rolling(window, min_periods=minimum).mean()
    den = f_var.shift(1).rolling(window, min_periods=minimum).mean()
    ratio = np.sqrt(num / den)
    ratio = ratio.where(den > 0).fillna(1.0)
    return path["forecast_te"] * ratio
