"""The benchmark of the extension: the cap-weighted combination of French's 49 industry portfolios.

Each industry portfolio's value-weighted return for a month is the return of the
firms in the industry, each counted in proportion to its market equity at the
start of the month. Weighting the 49 industry returns by each industry's total
market equity at the same time (firm count times average firm size, two blocks of
the same French file) gives the value-weighted return of all the firms in the 49
portfolios, which should be close to French's market return. Notebook 08 measures
how close, against the level fixed in constants.CAPW_TE_MAX_ANNUAL, and decides
whether these weights are the benchmark of notebooks 09 to 13.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C
from . import french_loader as fl

PERIODS_PER_YEAR = 12


def load_inputs(cache_dir: str = "data/french") -> dict[str, pd.DataFrame | pd.Series]:
    """The three monthly blocks of the 49-industry file and the market series.

    returns: value-weighted industry returns (decimal); firms: number of firms;
    size: average firm size in millions of dollars; market: Mkt-RF plus RF from
    the factors file (decimal). Missing codes are NaN in all of them.
    """
    returns = fl.load_monthly("ind49", r"Value Weighted Returns -- Monthly", cache_dir)
    firms = fl.load_counts("ind49", r"Number of Firms", cache_dir)
    size = fl.load_counts("ind49", r"Average Firm Size", cache_dir)
    f3 = fl.load_monthly("factors3", 0, cache_dir)
    excess, rf = C.CAPW_MARKET_SERIES
    market = (f3[excess] + f3[rf]).rename("market")
    return {"returns": returns, "firms": firms, "size": size, "market": market}


def market_equity(firms: pd.DataFrame, size: pd.DataFrame) -> pd.DataFrame:
    """Total market equity of each industry, in the units of the size block (millions of dollars)."""
    if not firms.index.equals(size.index) or not firms.columns.equals(size.columns):
        raise ValueError("firm counts and average sizes must share months and industries")
    return firms * size


def cap_weights(firms: pd.DataFrame, size: pd.DataFrame, timing: str = C.CAPW_WEIGHT_TIMING) -> pd.DataFrame:
    """Each industry's share of total market equity, per month; the rows sum to one.

    timing "same_month": the count and size of month t weight the returns of
    month t (French measures both at the start of the month). "previous_month":
    the count and size of month t-1 weight the returns of month t; the first
    month has no weights. Any month in which an industry's count or size is
    missing has no weights at all, so that a partial sum never passes as a
    whole-market weight.
    """
    me = market_equity(firms, size)
    if timing == "previous_month":
        me = me.shift(1)
    elif timing != "same_month":
        raise ValueError(f"unknown timing {timing!r}")
    total = me.sum(axis=1, min_count=me.shape[1])
    return me.div(total, axis=0)


def combination_return(returns: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    """Sum over industries of weight times return, per month; NaN where any of the 49 is missing."""
    if not returns.columns.equals(weights.columns):
        raise ValueError("returns and weights must have the same industries in the same order")
    aligned = weights.reindex(returns.index)
    return (aligned * returns).sum(axis=1, min_count=returns.shape[1]).rename("combination")


def tracking_error(a: pd.Series, b: pd.Series, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    """Annualised standard deviation of the per-period difference a - b, over the periods both have."""
    d = (a - b).dropna()
    if len(d) < 2:
        return float("nan")
    return float(d.std(ddof=1) * np.sqrt(periods_per_year))


def compare(a: pd.Series, b: pd.Series, periods_per_year: int = PERIODS_PER_YEAR) -> dict[str, float]:
    """Tracking error, annualised mean difference, correlation, largest absolute monthly difference and month count of a against b."""
    both = pd.concat([a, b], axis=1).dropna()
    d = both.iloc[:, 0] - both.iloc[:, 1]
    return {
        "months": int(len(d)),
        "tracking_error_annual": float(d.std(ddof=1) * np.sqrt(periods_per_year)),
        "mean_difference_annual": float(d.mean() * periods_per_year),
        "correlation": float(both.iloc[:, 0].corr(both.iloc[:, 1])) if both.std(ddof=1).gt(0).all() else float("nan"),
        "max_abs_monthly_difference": float(d.abs().max()),
        "month_of_max": str(d.abs().idxmax()),
    }


def weight_extremes(weights: pd.DataFrame, month: str | pd.Period) -> dict[str, object]:
    """The largest and smallest weights in one month, with their industries."""
    row = weights.loc[pd.Period(month, "M")].dropna()
    return {
        "month": str(pd.Period(month, "M")),
        "largest": row.idxmax(), "largest_weight": float(row.max()),
        "smallest": row.idxmin(), "smallest_weight": float(row.min()),
        "industries": int(len(row)),
    }
