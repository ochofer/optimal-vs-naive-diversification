"""
The daily measurement of tracking error, planned on 18 November 2026 and
committed on 19: a path's daily returns from the weights the study set for each
month, drifting with the industries' daily returns within the month and traded
only at the month's turn, as the plan of 18 November 2026 fixes it
(constants.py, section 9).

Within a month a portfolio's weights are those the study set for the month,
in force from the month's first trading day; each day's portfolio return is
the sum of the weights at the start of the day times the day's industry
returns, and the weights then move with those returns (w_i (1 + r_i) divided
by the portfolio's gross return), so that no trade happens within the month.
The benchmark is treated the same way from its weights of the month. The
daily active return is the portfolio's daily return less the benchmark's.

Compounded over a month, the daily returns of such a portfolio equal the
weights times the industries' compounded returns, sum_i w_i (prod_d (1 + r_id)
minus 1), which is the check tests/test_daily.py runs on a made-up month. That
compounded monthly return is what gate D1 reconciles with the committed
monthly active return, which notebook 12 computed on French's monthly
industry returns: French's monthly returns need not equal his daily returns
compounded, and the gate measures the gap before any daily figure is read.

Family D, added on 18 November 2026 after every recorded run (constants.py,
section 9): window_weight_statistics describes a covariance estimator's
window by the weights it puts on the days, the mean age of an observation,
the effective number of observations and the share of the weight in the most
recent days, for a flat window and for the exponentially weighted one.

read_interval, a setting of 20 November 2026 made before part (c) ran, takes a
row's difference, RiskMetrics less the sample covariance, with its interval and
the reference figure, and the pair of the paper's figures the row is read
against, and returns the reading: the four readings of constants.DAILY_READINGS
where the paper reports a gain, the three of DAILY_READINGS_UNCONSTRAINED where
it reports none, and the window clause where the row's sample covariance is not
on the paper's window. Part (c) writes no reading by hand.

The module depends on numpy and pandas alone.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["drift_daily", "daily_returns_of_path", "compounded_by_month", "reconcile", "window_weight_statistics", "read_interval"]


def drift_daily(w0: np.ndarray, returns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """One month. `w0` the weights in force on the first day (they sum to one), `returns` the days' plain
    industry returns, shape (days, N). Returns the daily portfolio returns, shape (days,), and the
    weights at the start of each day, shape (days, N): the first row is w0, each later row the previous
    row grown by the previous day's returns and rescaled to sum to one."""
    w = np.asarray(w0, dtype=float)
    r = np.asarray(returns, dtype=float)
    if r.ndim != 2 or r.shape[1] != len(w):
        raise ValueError("returns must have one column per weight")
    if not np.isclose(w.sum(), 1.0, atol=1e-10):
        raise ValueError("the weights must sum to one")
    days = r.shape[0]
    starts = np.empty((days, len(w)))
    port = np.empty(days)
    for d in range(days):
        starts[d] = w
        port[d] = float(w @ r[d])
        grown = w * (1.0 + r[d])
        w = grown / grown.sum()
    return port, starts


def daily_returns_of_path(weights_by_month: pd.DataFrame, returns_d: pd.DataFrame) -> pd.Series:
    """The daily returns of a portfolio whose weights are reset to `weights_by_month.loc[month]` on the
    first trading day of each month in that frame's index and drift within the month. `returns_d` holds
    the industries' plain daily returns (decimals) with a daily PeriodIndex or DatetimeIndex and the same
    columns as the weights; the days of a month are the days whose month equals the period. Every month
    of the frame must have at least one trading day, and no day of those months may have a missing
    return. Returns a Series over the days of those months, in order."""
    if list(weights_by_month.columns) != list(returns_d.columns):
        raise ValueError("the weights and the daily returns must have the same columns in the same order")
    month_of_day = returns_d.index.asfreq("M") if isinstance(returns_d.index, pd.PeriodIndex) else returns_d.index.to_period("M")
    pieces = []
    for month in weights_by_month.index:
        days = returns_d.index[month_of_day == month]
        if len(days) == 0:
            raise ValueError(f"no trading day in {month}")
        r = returns_d.loc[days]
        if r.isna().any().any():
            raise ValueError(f"a missing daily return in {month}")
        port, _ = drift_daily(weights_by_month.loc[month].to_numpy(), r.to_numpy())
        pieces.append(pd.Series(port, index=days))
    return pd.concat(pieces)


def compounded_by_month(daily: pd.Series) -> pd.Series:
    """The return of each month compounded from its days: prod (1 + r) minus 1, indexed by month."""
    month_of_day = daily.index.asfreq("M") if isinstance(daily.index, pd.PeriodIndex) else daily.index.to_period("M")
    return (1.0 + daily).groupby(month_of_day).prod() - 1.0


def reconcile(daily_portfolio: pd.Series, daily_benchmark: pd.Series | None, committed_active: pd.Series, periods: int = 12) -> dict:
    """Gate D1 for one path: the month's active return compounded from the daily series (the portfolio's
    compounded return less the benchmark's) against the committed monthly active return over the same
    months. Returns the correlation of the two monthly series, the realised tracking error of each
    (per year, n minus 1), their gap, the largest absolute monthly gap and the month it falls in, and
    the number of months. With `daily_benchmark` None the series is a portfolio's own return against its
    monthly return, the form family C's six series take (added 20 November 2026)."""
    comp = compounded_by_month(daily_portfolio)
    if daily_benchmark is not None:
        comp = comp - compounded_by_month(daily_benchmark)
    committed = committed_active.copy()
    committed.index = pd.PeriodIndex(committed.index, freq="M")
    comp = comp.reindex(committed.index)
    if comp.isna().any():
        raise ValueError("a committed month has no compounded daily return")
    te_daily = float(np.std(comp.to_numpy(), ddof=1) * np.sqrt(periods))
    te_committed = float(np.std(committed.to_numpy(), ddof=1) * np.sqrt(periods))
    gaps = (comp - committed).abs()
    return {"months": int(len(comp)), "correlation": float(np.corrcoef(comp.to_numpy(), committed.to_numpy())[0, 1]),
            "te_compounded": te_daily, "te_committed": te_committed, "te_gap": te_daily - te_committed,
            "largest_monthly_gap": float(gaps.max()), "month_of_largest_gap": str(gaps.idxmax())}


def window_weight_statistics(days: int, halflife: float | None = None, recent_days: int = 756) -> dict:
    """The weights a covariance estimator puts on a window of `days` trading days, described by three
    numbers: the mean age of an observation in days (the most recent day has age 1), the effective number
    of observations (one over the sum of the squared weights, equal to `days` for a flat window) and the
    share of the weight in the last `recent_days` days. A flat window weighs every day 1 / days; with a
    `halflife` the weight halves every `halflife` days, as covariance.ewma_cov weighs them, normalised to
    sum to one."""
    days = int(days)
    if days < 1:
        raise ValueError("a window needs at least one day")
    age = np.arange(1, days + 1, dtype=float)                       # 1 the most recent day, `days` the oldest
    if halflife is None:
        w = np.full(days, 1.0 / days)
    else:
        w = 0.5 ** ((age - 1.0) / float(halflife))
        w = w / w.sum()
    return {"days": days, "halflife": halflife, "mean age": float(w @ age), "effective number": float(1.0 / (w ** 2).sum()),
            "share in recent days": float(w[age <= recent_days].sum()), "recent days": int(recent_days)}


def read_interval(difference: float, lower: float, upper: float, reference: float, paper_pair: tuple[float, float],
                  window_years: int, readings: dict, readings_unconstrained: dict, window_clause: str,
                  paper_window_years: int = 5) -> dict:
    """The reading of one RiskMetrics row, a setting of 20 November 2026 made before part (c) ran.

    `difference`, `lower` and `upper` are RiskMetrics less the sample covariance and its interval, in the
    row's units; `reference` is the sample covariance's figure in the same units; `paper_pair` is
    (RiskMetrics, sample covariance) in the paper's table for the portfolio the row is read against. The
    published gain is the pair's gap as a share of the paper's sample-covariance figure, and on this
    row's level it is that share times `reference`. Where the pair has RiskMetrics above the sample
    covariance there is no published gain, and the row has three readings. Where the row's sample
    covariance is not on the paper's window the window clause is added. Returns the reading's key, the
    sentence, the published share and the published gain on this level (None where the paper reports
    no gain)."""
    rm, sample = paper_pair
    share = (sample - rm) / sample if sample > rm else None
    gain_here = None if share is None else share * reference
    if upper < 0:
        key = "below"
    elif lower > 0:
        key = "above"
    elif share is None:
        key = "includes_zero"
    elif lower > -gain_here:
        key = "excludes_gain"      # a gain as large as the published one would be a difference of -gain_here, which lies below the interval
    else:
        key = "includes_gain"
    sentence = (readings_unconstrained if share is None else readings)[key]
    if window_years != paper_window_years:
        sentence = sentence + "; " + window_clause
    return {"key": key, "sentence": sentence, "published_share": share, "published_gain_here": gain_here}
