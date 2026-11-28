"""The two naive portfolios under the index mandate, and the measures that set them beside the optimised paths (notebooks 08 and 09).

A naive portfolio takes its weights from the benchmark weights alone, or from the benchmark weights and one score per
industry, with no covariance estimate:

- naive_tilt: Coal, Oil and Util held at half their benchmark weight, and the weight this removes spread over the
  other 46 industries in proportion to their benchmark weights (notebook 08).
- tilted_index: the same tilt with tobacco and weapons excluded, the removed weight spread over the other 44, and each
  of the 44 then scaled by one plus a common multiple k of its centred factor score, k as large as the bound on each
  active weight and the floor at zero allow (notebook 09).

run_path holds a naive portfolio month by month as evaluation.run_path holds an optimised one: the path starts as the
benchmark, rebalances to the month's weights every month, and measures its one-way turnover against its previous weights
drifted by the previous month's returns. The remaining functions compute the measures the two notebooks report.

The exposure that factor_objective measures is the forecast one: the active weights times each industry's betas from the
three years of daily returns before the month. realised_exposure measures it after the fact, from the portfolio's own
monthly active returns regressed on the six factors' monthly returns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C
from .source import attribution as A
from .source import evaluation as E
from .source import optimiser as O


def naive_tilt(b: np.ndarray, tilt: np.ndarray) -> tuple[np.ndarray, dict]:
    """The naive tilt's weights for one month, from the benchmark weights b; tilt marks Coal, Oil and Util."""
    w = b.copy()
    removed = (1.0 - C.TILT_MAX_SHARE_OF_BENCHMARK) * b[tilt].sum()
    w[tilt] = C.TILT_MAX_SHARE_OF_BENCHMARK * b[tilt]
    rest = ~tilt
    w[rest] = b[rest] * (1.0 + removed / b[rest].sum())
    return w, {"removed weight": removed}


def tilted_index(b: np.ndarray, tilt: np.ndarray, excluded: np.ndarray, score: np.ndarray,
                 names: list[str]) -> tuple[np.ndarray, dict]:
    """The tilted index's weights for one month.

    b: the benchmark weights; tilt and excluded: the masks of the tilted and the excluded industries; score: each
    industry's score, the sum of its betas to the four targeted factors; names: the industries' names, in b's order.
    Returns the weights and k, the constraint that set it ("bound" or "floor") and the industry at which it binds.
    """
    rest = ~(tilt | excluded)
    w0 = b.copy()
    w0[tilt] = C.TILT_MAX_SHARE_OF_BENCHMARK * b[tilt]
    w0[excluded] = 0.0
    removed = (1.0 - C.TILT_MAX_SHARE_OF_BENCHMARK) * b[tilt].sum() + b[excluded].sum()
    w0[rest] = b[rest] * (1.0 + removed / b[rest].sum())
    s, w_rest, b_rest = score[rest], w0[rest], b[rest]
    z = s - (w_rest @ s) / w_rest.sum()           # the score centred on its w0-weighted mean over the 44
    a = w_rest - b_rest                            # the active weight of w0, zero or more for each of the 44
    c = w_rest * z                                 # the change in active weight per unit of k
    rest_names = [n for n, keep in zip(names, rest) if keep]
    limits = []
    for i in range(len(z)):
        if c[i] > 0:
            limits.append(((C.ACTIVE_WEIGHT_BOUND - a[i]) / c[i], "bound", rest_names[i]))
        elif c[i] < 0:
            limits.append(((a[i] + C.ACTIVE_WEIGHT_BOUND) / -c[i], "bound", rest_names[i]))
            limits.append((1.0 / -z[i], "floor", rest_names[i]))
    k, source, name = min(limits, key=lambda x: x[0])
    w = w0.copy()
    w[rest] = w_rest * (1.0 + k * z)
    return w, {"removed weight": removed, "k": k, "k set by": source, "k set at": name,
               "largest active weight of w0": float(np.abs(w0 - b)[rest].max())}


def run_path(weights_of, months: pd.PeriodIndex, weights: pd.DataFrame, returns_m: pd.DataFrame, betas: dict,
             factors: list[str], sign: np.ndarray) -> pd.DataFrame:
    """One naive path: weights_of(month, b) gives the month's weights and a dict of descriptions.

    Each month records the active return, the one-way turnover of the path and of the benchmark, the largest active
    weight, the effective number and the industries held, the six active exposures with that month's betas, and the
    objective, the exposures summed with the signs in sign. The weights go into the column "weights".
    """
    recs = []
    w_prev, prev = None, None
    for m in months:
        b = weights.loc[m].to_numpy()
        r = returns_m.loc[m].to_numpy()
        w, info = weights_of(m, b)
        if w_prev is None:
            w0, b_drift = b.copy(), b.copy()
        else:
            w0 = O.drifted_weights(w_prev, returns_m.loc[prev].to_numpy())
            b_drift = O.drifted_weights(weights.loc[prev].to_numpy(), returns_m.loc[prev].to_numpy())
        x = A.active_exposures(betas[m], w, b)
        recs.append({"month": m, "active_return": float(w @ r - b @ r), "turnover": O.one_way_turnover(w, w0),
                     "benchmark_turnover": O.one_way_turnover(b, b_drift), "largest active weight": float(np.abs(w - b).max()),
                     "effective_number": O.effective_number(w), "held": int((w > 1e-6).sum()), "objective": float(sign @ x),
                     **{f"exposure {f}": float(v) for f, v in zip(factors, x)}, **info, "weights": w})
        w_prev, prev = w, m
    return pd.DataFrame(recs).set_index("month")


def realised_beta(active, bench_ex) -> float:
    """The slope of the portfolio's monthly excess return (the benchmark's plus the active return) on the benchmark's."""
    bench_ex = np.asarray(bench_ex, dtype=float)
    port_ex = bench_ex + np.asarray(active, dtype=float)
    return float(np.cov(port_ex, bench_ex, ddof=1)[0, 1] / np.var(bench_ex, ddof=1))


def measures(active, turnover, bench_ex, objective=None, exposures=None) -> dict:
    """Realised tracking error, gross active return, turnover, cost and net active return at each cost level, the
    information ratios, the realised beta, and, given the monthly objective and the monthly exposures (a table with a
    column "exposure F" for each factor F), the exposure per basis point and the mean exposure to each factor."""
    active = np.asarray(active, dtype=float)
    te = E.realised_tracking_error(active)
    gross = 12.0 * float(active.mean())
    out = {"realised TE": te, "active return (gross)": gross, "turnover (one-way)": float(np.mean(turnover)),
           "information ratio (gross)": gross / te, "realised beta": realised_beta(active, bench_ex)}
    for c in C.EXT_COST_LEVELS:
        bp = int(round(c * 1e4))
        cost = 12.0 * float(np.mean(turnover)) * c
        out[f"cost at {bp} bp"] = cost
        out[f"net active return at {bp} bp"] = gross - cost
        out[f"information ratio at {bp} bp"] = (gross - cost) / te
    if objective is not None:
        out["mean objective"] = float(np.mean(objective))
        out["exposure per bp of realised TE"] = float(np.mean(objective)) / (1e4 * te)
    if exposures is not None:
        for f in C.ATTRIBUTION_FACTORS:
            out[f"mean exposure {f}"] = float(np.mean(exposures[f"exposure {f}"]))
    return out


def resample_indices(n: int) -> np.ndarray:
    """The circular block resamples of evaluation.block_bootstrap_band: ceil(n / block) block starts per resample, each block
    running past the last month into the first, the generator seeded with EVAL_BOOTSTRAP_SEED."""
    block, draws = C.EVAL_BOOTSTRAP_BLOCK_MONTHS, C.EVAL_BOOTSTRAP_DRAWS
    rng = np.random.default_rng(C.EVAL_BOOTSTRAP_SEED)
    k = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(draws, k))
    return ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(draws, k * block)[:, :n]


def exposure_per_bp(objective: np.ndarray, active: np.ndarray) -> np.ndarray:
    """The mean objective over 10,000 times the realised tracking error, along the last axis."""
    return objective.mean(axis=-1) / (1e4 * active.std(axis=-1, ddof=1) * np.sqrt(12.0))


def bootstrap_difference(d_star: np.ndarray) -> tuple[float, float, float]:
    """The 95% percentile interval of the resampled differences and the two-sided p-value: twice the smaller of the shares
    at or below zero and at or above zero, each counted as (count + 1) / (draws + 1), at most 1."""
    tail = 100.0 * (1.0 - C.EVAL_BOOTSTRAP_LEVEL) / 2.0
    lo, hi = np.percentile(d_star, [tail, 100.0 - tail])
    draws = len(d_star)
    p = min(1.0, 2.0 * min((int((d_star <= 0).sum()) + 1) / (draws + 1), (int((d_star >= 0).sum()) + 1) / (draws + 1)))
    return float(lo), float(hi), p


def information_ratios(active, costs: dict, idx: np.ndarray) -> dict:
    """The information ratio gross and net of each cost, each with the standard deviation of the ratio over the resamples
    idx; the cost is held at the full-sample figure, 12 times the mean one-way turnover times the cost level."""
    a = np.asarray(active, dtype=float)
    a_star = a[idx]
    te_star = a_star.std(axis=1, ddof=1) * np.sqrt(12.0)
    g_star = 12.0 * a_star.mean(axis=1)
    te = E.realised_tracking_error(a)
    row = {"information ratio (gross)": 12.0 * a.mean() / te, "standard error (gross)": float((g_star / te_star).std(ddof=1))}
    for c, cost in costs.items():
        row[f"information ratio at {c} bp"] = (12.0 * a.mean() - cost) / te
        row[f"standard error at {c} bp"] = float(((g_star - cost) / te_star).std(ddof=1))
    return row


def information_ratio_star(active, cost: float, idx: np.ndarray) -> np.ndarray:
    """The information ratio on each resample idx, net of the cost per year held at its full-sample figure: the resampled
    ratios whose standard deviation information_ratios reports."""
    a_star = np.asarray(active, dtype=float)[idx]
    return (12.0 * a_star.mean(axis=1) - cost) / (a_star.std(axis=1, ddof=1) * np.sqrt(12.0))


def factor_design(factors) -> np.ndarray:
    """The design of the regression of a monthly active return on the factors: a column of ones, then each factor's
    monthly return in the order given."""
    f = np.asarray(factors, dtype=float)
    return np.column_stack([np.ones(len(f)), f])


def realised_exposure(active, design: np.ndarray, targeted) -> float:
    """The realised exposure to the targeted factors: the sum of their slopes in the least-squares regression of the
    monthly active return on the design. targeted holds the design's column numbers of the targeted factors."""
    b = np.linalg.lstsq(design, np.asarray(active, dtype=float), rcond=None)[0]
    return float(b[list(targeted)].sum())


def realised_exposure_per_bp(active, design: np.ndarray, targeted, idx: np.ndarray | None = None):
    """The realised exposure over 10,000 times the realised tracking error, on the months as they are or, given idx, on each
    resample of them, with the regression run again on the resampled months."""
    a = np.asarray(active, dtype=float)
    if idx is None:
        return realised_exposure(a, design, targeted) / (1e4 * a.std(ddof=1) * np.sqrt(12.0))
    out = np.empty(len(idx))
    for d, j in enumerate(idx):
        out[d] = realised_exposure(a[j], design[j], targeted) / (1e4 * a[j].std(ddof=1) * np.sqrt(12.0))
    return out
