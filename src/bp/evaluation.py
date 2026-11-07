"""The rolling evaluation of the extension (notebook 12): one portfolio path per specification, month by month.

A path is one variant (a covariance estimator, or the robust portfolio built from all of them) under one
constraint set. It starts as the index. In every evaluation month the covariance is estimated on the data before
the month, the optimiser solves for the weights with the drifted previous weights as the turnover reference, the
portfolio and the benchmark earn the month's returns, and the active return, the forecast tracking error, the
turnover and the state of the cap are recorded. The measures of a path are computed from its records: realised
tracking error, forecast tracking error and its calibration, active return gross and net of trading costs,
turnover and relaxed-cap months, holdings.

Added 18 October 2026 (constants.EVAL_ADDITIONS_DATE): two descriptive figures of a path, the worst cumulative fall
of the active return and the share of positive months, and a block-bootstrap band on the bias statistic. Version 2,
module A (notebook 15): the factor path, which each month maximises the targeted exposure under the mandate and a
budget on the forecast tracking error, and its measures.
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


# ---------------------------------------------------------------------------
# Added 18 October 2026: two descriptive figures and the block-bootstrap band
# ---------------------------------------------------------------------------

def worst_cumulative_fall(active: pd.Series) -> dict:
    """The largest fall of the cumulative active return (the running sum of the monthly active returns, starting
    at zero before the first month) from an earlier high: its size in return units, the month of the high, the
    month of the low and the months between them. A descriptive figure, in no claim."""
    a = pd.Series(np.asarray(active, dtype=float), index=active.index if isinstance(active, pd.Series) else None)
    c = a.cumsum()
    high = np.maximum.accumulate(np.concatenate([[0.0], c.to_numpy()]))[1:]
    fall = pd.Series(high - c.to_numpy(), index=c.index)
    if fall.max() <= 0:
        return {"fall": 0.0, "peak": None, "trough": None, "months": 0}
    trough = fall.idxmax()
    before = c.loc[:trough]
    peak = before.idxmax() if before.max() > 0 else before.index[0]       # a fall from the start has no earlier high; the first month stands for it
    months = int(c.index.get_loc(trough) - c.index.get_loc(peak)) + (0 if before.max() > 0 else 1)
    return {"fall": float(fall.max()), "peak": peak if before.max() > 0 else "start", "trough": trough, "months": months}


def rolling_tracking_error(active: pd.DataFrame, window: int = C.EVAL_ROLLING_TE_MONTHS) -> pd.DataFrame:
    """The rolling realised tracking error of every column: the standard deviation (n minus 1) of the monthly
    active return over the `window` months ending in and including each month, times the square root of 12,
    from the first month with a full window. Added 6 November 2026 (constants.EVAL_ROLLING_ADDITIONS_DATE)."""
    if window < 2 or window > len(active):
        raise ValueError(f"the window must be between 2 and the number of months, {len(active)}; got {window}")
    return active.rolling(window).std(ddof=1).iloc[window - 1:] * np.sqrt(PERIODS_PER_YEAR)


def share_positive(active: pd.Series | np.ndarray) -> float:
    """The share of months in which the active return is above zero."""
    a = np.asarray(active, dtype=float)
    return float(np.mean(a > 0))


def block_bootstrap_band(active: np.ndarray, forecast_te: np.ndarray, block: int = C.EVAL_BOOTSTRAP_BLOCK_MONTHS,
                         draws: int = C.EVAL_BOOTSTRAP_DRAWS, seed: int = C.EVAL_BOOTSTRAP_SEED, level: float = C.EVAL_BOOTSTRAP_LEVEL) -> tuple[float, float]:
    """A band on the bias statistic from a circular block bootstrap: each resample draws ceil(n / block) starting
    months at random and takes `block` consecutive months from each (running past the last month into the first),
    keeping the month's pair (active return, forecast) together; the band is the central `level` share of the
    resampled statistics. Deterministic for a given seed."""
    a = np.asarray(active, dtype=float)
    f = np.asarray(forecast_te, dtype=float) / np.sqrt(PERIODS_PER_YEAR)
    n = len(a)
    if n != len(f) or n < 2 or block < 1 or draws < 1:
        raise ValueError("the band needs at least two months, a block of one month or more and one draw or more")
    if (np.asarray(forecast_te, dtype=float) <= C.OPT_TOL_TE).any():
        return (float("nan"), float("nan"))
    ratio = a / f
    rng = np.random.default_rng(seed)
    k = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(draws, k))
    idx = ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(draws, k * block)[:, :n]
    stats = np.std(ratio[idx], axis=1, ddof=1)
    tail = 100.0 * (1.0 - level) / 2.0
    lo, hi = np.percentile(stats, [tail, 100.0 - tail])
    return (float(lo), float(hi))


# ---------------------------------------------------------------------------
# Version 2, module A: the factor path (notebook 15)
# ---------------------------------------------------------------------------

def run_factor_path(months, Sigmas, betas: dict, weights: pd.DataFrame, returns: pd.DataFrame, constraints: tuple, s: np.ndarray,
                    budget_annual: float, tilt_mask: np.ndarray, exclude_mask: np.ndarray | None, keep_weights: bool = False) -> pd.DataFrame:
    """One path of the factor objective, run as `run_path` runs a path of version 1: in every month the optimiser
    maximises s' B' (w - b) under the constraints and the budget, with the drifted previous weights as the turnover
    reference, `Sigmas[month]` the month's covariance (a list for the robust variant) and `betas[month]` its N by K
    betas, both estimated before the month. The month in which the budget cannot be met takes the
    tracking-error-minimising portfolio and is marked (`budget_met` False), as constants.FO_INFEASIBLE_RULE says.

    Returns one record per month: the forecast tracking error, the active return, the turnover and the cap, whether
    the budget was met and whether it binds, the objective and the active exposure to each factor, the gap
    s' (B_t - B_{t+1})' a_t once the next month's betas are known (nan in the last month), and the holdings.
    """
    names = list(C.ATTRIBUTION_FACTORS)
    records = []
    w_prev = None
    prev_month = None
    prev = None                                  # (active weights, betas) of the previous month, for its gap
    for month in months:
        b = weights.loc[month].to_numpy()
        r = returns.loc[month].to_numpy()
        B = np.asarray(betas[month], dtype=float)
        if w_prev is None:
            w0 = b.copy()
            b_drift = b.copy()
        else:
            w0 = O.drifted_weights(w_prev, returns.loc[prev_month].to_numpy())
            b_drift = O.drifted_weights(weights.loc[prev_month].to_numpy(), returns.loc[prev_month].to_numpy())
        sol = O.solve_factor_objective(Sigmas[month], b, B, s, budget_annual, constraints, w_prev=w0, tilt_mask=tilt_mask, exclude_mask=exclude_mask)
        if prev is not None:
            a_prev, B_prev = prev
            records[-1]["gap"] = float(np.asarray(s, dtype=float) @ (B_prev - B).T @ a_prev)
        rec = {"month": month, "forecast_te": sol.tracking_error, "active_return": float(sol.weights @ r - b @ r),
               "turnover": sol.turnover, "cap_used": sol.turnover_cap_used if "turnover_cap" in constraints else np.nan,
               "relaxed": bool(sol.relaxed), "cap_binds": bool(sol.binding.get("turnover_cap", 0)),
               "budget_met": bool(sol.budget_met), "budget_binds": bool(sol.binding["budget"]), "objective": sol.objective,
               **{f"exposure {f}": float(x) for f, x in zip(names, sol.exposures)},
               "gap": np.nan, "effective_number": O.effective_number(sol.weights), "held": int((sol.weights > 1e-6).sum()),
               "status": sol.status, "benchmark_turnover": O.one_way_turnover(b, b_drift)}
        if keep_weights:
            rec["weights"] = sol.weights
        records.append(rec)
        prev = (sol.active, B)
        w_prev, prev_month = sol.weights, month
    return pd.DataFrame(records).set_index("month")


def summarise_factor(path: pd.DataFrame, budget_annual: float, targeted: tuple = C.FO_TARGET_FACTORS) -> dict:
    """The measures of one factor path: version 1's measures (realised and forecast tracking error, the bias
    statistic, active return gross and net of costs, turnover, the cap) and module A's (realised over budget, the
    months the budget was not met and the months it binds, the mean active exposure to each targeted factor and
    their sum, the exposure bought per basis point of realised tracking error, the mean absolute gap)."""
    out = summarise(path)
    te = out["realised TE"]
    years = len(path) / PERIODS_PER_YEAR
    out["budget"] = float(budget_annual)
    out["realised over budget"] = te / budget_annual
    out["budget not met months"] = int((~path["budget_met"]).sum())
    out["budget binds months"] = int(path["budget_binds"].sum())
    out["cap binds months"] = int(path["cap_binds"].sum())
    for f in targeted:
        out[f"mean exposure {f}"] = float(path[f"exposure {f}"].mean())
    out["mean objective"] = float(path["objective"].mean())
    out["mean objective per targeted factor"] = float(path["objective"].mean()) / len(targeted)
    out["exposure per bp of realised TE"] = float(path["objective"].mean()) / (1e4 * te) if te > C.OPT_TOL_TE else float("nan")
    out["mean absolute gap"] = float(path["gap"].abs().mean())
    out["standard error of the gross active return"] = te / np.sqrt(years)
    return out

