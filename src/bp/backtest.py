"""
Rolling out-of-sample evaluation and the three performance measures of
DeMiguel, Garlappi and Uppal (2009), section 2.

The rolling sample: with T months of data and an estimation window of M
months, the rule is estimated on months t-M+1 to t and its weights are held
through month t+1, for t = M, ..., T-1. That gives T - M out-of-sample
monthly returns per rule (DGU p. 1928).

Measures, all monthly:
  Sharpe ratio        mean of out-of-sample excess returns over their standard
                      deviation, equation (12); the p-value of the difference
                      from 1/N is the Jobson-Korkie (1981) statistic with the
                      Memmel (2003) correction, footnote 16.
  CEQ return          mean minus gamma/2 times variance, equation (14), with
                      the delta-method p-value of footnote 18.
  turnover            average over months of the sum of absolute trades needed
                      to move from the drifted weights to the new target,
                      equation (15).
  net-of-cost return  equation (16), with a proportional cost c per unit of
                      one-way turnover.
  return-loss         equation (17): the extra mean return a rule needs for its
                      net Sharpe ratio to equal 1/N's.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from . import constants as C


@dataclass
class Backtest:
    name: str
    oos: pd.Series            # out-of-sample excess return, indexed by the month it was earned
    weights: pd.DataFrame     # target weights, indexed by the month they were formed for
    turnover: pd.Series       # one-way trade at each rebalance, equation (15) summand
    drifted: pd.DataFrame     # weights before each rebalance


def drift(w: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Weights after one month of excess returns r, before rebalancing (DGU p. 1929, w_{t+}).

    Position j grows to w_j (1 + r_j) and wealth to 1 + w'r, the residual
    1 - sum(w) sitting in the riskless asset at zero excess return. Dividing by
    wealth rather than by the sum of the risky positions keeps the sign of a
    net-short portfolio, which DGU's normalisation preserves on purpose.
    """
    return w * (1.0 + r) / (1.0 + w @ r)


def rolling(returns: pd.DataFrame, rule, window: int = C.DGU_ESTIMATION_WINDOW, name: str | None = None) -> Backtest:
    R = returns.to_numpy(dtype=float)
    T, N = R.shape
    if T <= window:
        raise ValueError(f"{T} months is not more than the {window}-month window")
    idx = returns.index
    n_oos = T - window
    oos = np.empty(n_oos)
    weights = np.empty((n_oos, N))
    drifted = np.full((n_oos, N), np.nan)
    turnover = np.full(n_oos, np.nan)
    prev = None
    for k in range(n_oos):
        t = window + k                       # the month whose return is earned out of sample
        w = np.asarray(rule(R[t - window:t]), dtype=float)
        weights[k] = w
        if prev is not None:
            drifted[k] = prev
            turnover[k] = np.abs(w - prev).sum()
        oos[k] = w @ R[t]
        prev = drift(w, R[t])
    months = idx[window:]
    cols = list(returns.columns)
    return Backtest(
        name=name or getattr(rule, "__name__", "rule"),
        oos=pd.Series(oos, index=months, name=name),
        weights=pd.DataFrame(weights, index=months, columns=cols),
        turnover=pd.Series(turnover, index=months, name="turnover"),
        drifted=pd.DataFrame(drifted, index=months, columns=cols),
    )


# ---------------------------------------------------------------------------
# Measures
# ---------------------------------------------------------------------------

def sharpe(x: pd.Series) -> float:
    return float(x.mean() / x.std(ddof=1))


def ceq(x: pd.Series, gamma: float = C.DGU_RISK_AVERSION) -> float:
    return float(x.mean() - 0.5 * gamma * x.var(ddof=1))


def mean_turnover(bt: Backtest) -> float:
    """Equation (15): the average one-way trade per rebalance, over the rebalances that exist."""
    return float(bt.turnover.dropna().mean())


def net_of_cost(bt: Backtest, cost: float = C.DGU_TCOST) -> pd.Series:
    """Equation (16): (1 + r)(1 - c * turnover) - 1, with no trade charged in the first month."""
    to = bt.turnover.fillna(0.0)
    return (1.0 + bt.oos) * (1.0 - cost * to) - 1.0


def return_loss(bt: Backtest, benchmark: Backtest, cost: float = C.DGU_TCOST) -> float:
    """Equation (17), on net-of-cost returns."""
    k = net_of_cost(bt, cost)
    b = net_of_cost(benchmark, cost)
    return float(b.mean() / b.std(ddof=1) * k.std(ddof=1) - k.mean())


def sharpe_pvalue(x: pd.Series, y: pd.Series) -> float:
    """Jobson-Korkie (1981) test of equal Sharpe ratios with the Memmel (2003) correction, DGU footnote 16."""
    T = len(x)
    mi, mn = x.mean(), y.mean()
    si, sn = x.std(ddof=1), y.std(ddof=1)
    s_in = np.cov(x, y, ddof=1)[0, 1]
    theta = (2 * si**2 * sn**2 - 2 * si * sn * s_in
             + 0.5 * mi**2 * sn**2 + 0.5 * mn**2 * si**2
             - (mi * mn / (si * sn)) * s_in**2) / T
    z = (sn * mi - si * mn) / np.sqrt(theta)
    return float(2 * (1 - stats.norm.cdf(abs(z))))


def ceq_pvalue(x: pd.Series, y: pd.Series, gamma: float = C.DGU_RISK_AVERSION) -> float:
    """Delta-method test of equal CEQ returns, DGU footnote 18."""
    T = len(x)
    mi, mn = x.mean(), y.mean()
    vi, vn = x.var(ddof=1), y.var(ddof=1)
    v_in = np.cov(x, y, ddof=1)[0, 1]
    grad = np.array([1.0, -1.0, -0.5 * gamma, 0.5 * gamma])
    Theta = np.array([
        [vi, v_in, 0.0, 0.0],
        [v_in, vn, 0.0, 0.0],
        [0.0, 0.0, 2 * vi**2, 2 * v_in**2],
        [0.0, 0.0, 2 * v_in**2, 2 * vn**2],
    ])
    diff = (mi - 0.5 * gamma * vi) - (mn - 0.5 * gamma * vn)
    var = grad @ Theta @ grad / T
    z = diff / np.sqrt(var)
    return float(2 * (1 - stats.norm.cdf(abs(z))))


def evaluate(bts: dict[str, Backtest], benchmark: str = "ew", cost: float = C.DGU_TCOST) -> pd.DataFrame:
    """One row per rule: Sharpe, its p-value against the benchmark, CEQ, its p-value, turnover, relative turnover, return-loss."""
    b = bts[benchmark]
    rows = []
    for name, bt in bts.items():
        rows.append({
            "rule": name,
            "sharpe": sharpe(bt.oos),
            "sharpe_p": np.nan if name == benchmark else sharpe_pvalue(bt.oos, b.oos),
            "ceq": ceq(bt.oos),
            "ceq_p": np.nan if name == benchmark else ceq_pvalue(bt.oos, b.oos),
            "turnover": mean_turnover(bt),
            "turnover_rel": mean_turnover(bt) / mean_turnover(b),
            "return_loss": np.nan if name == benchmark else return_loss(bt, b, cost),
        })
    return pd.DataFrame(rows).set_index("rule")
