"""The optimiser of the extension: the portfolio that tracks the benchmark most closely under a set of constraints (notebook 11).

For a month with benchmark weights b and a monthly covariance matrix Sigma, the
optimiser finds the weights w that minimise the forecast tracking error, the
square root of 12 (w - b)' Sigma (w - b), subject to the constraints of a named
set: the weights sum to one; no short positions (long_only); each untilted
industry within ACTIVE_WEIGHT_BOUND of its benchmark weight (active_weight_bound);
one-way turnover from the drifted previous portfolio at most
TURNOVER_CAP_MONTHLY_ONE_WAY (turnover_cap); the tilted industries at no more than
TILT_MAX_SHARE_OF_BENCHMARK of their benchmark weight (tilt); named industries
at zero (exclusion); the portfolio's beta to the benchmark equal to the benchmark's
(beta_neutral). The objective is quadratic and every constraint is linear,
so the problem is a convex quadratic program with one global minimum, solved by
cvxpy with the solver named in constants.OPT_SOLVER. Two safeguards (notebook 11,
check D5): when the turnover cap is among the constraints, the smallest feasible
one-way turnover is found first, by a linear program, so that the solver is never
handed a capped problem that has no solution (a cap below that turnover is raised
to it and the month is marked relaxed); and every solution is checked against its
constraints within constants.OPT_TOL before it is returned, whatever status the
solver reports.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import cvxpy as cp
import numpy as np

from . import constants as C

PERIODS_PER_YEAR = 12


class OptimiserError(RuntimeError):
    """The solver did not return an optimal solution, or the solution failed a check."""


@dataclass
class Solution:
    weights: np.ndarray
    active: np.ndarray                 # weights minus benchmark weights
    tracking_error: float              # forecast, per year: sqrt(12 a' Sigma a)
    turnover: float                    # one-way, against the previous portfolio (nan when there is none)
    turnover_cap_used: float | None    # the cap applied, after any relaxation
    relaxed: bool                      # True when the cap had to be raised to make the month feasible
    status: str
    binding: dict = field(default_factory=dict)   # constraint name -> count of bounds within OPT_TOL of their limit


def cholesky_factor(Sigma: np.ndarray) -> np.ndarray:
    """L with Sigma = L L', after symmetrising; a jitter of 1e-10 on the diagonal is added only if Sigma is not positive definite."""
    S = 0.5 * (Sigma + Sigma.T)
    try:
        return np.linalg.cholesky(S)
    except np.linalg.LinAlgError:
        return np.linalg.cholesky(S + 1e-10 * np.eye(S.shape[0]))


def drifted_weights(w_prev: np.ndarray, returns_prev: np.ndarray) -> np.ndarray:
    """The previous portfolio after the month's returns: w_i (1 + r_i) divided by the portfolio's own gross return."""
    grown = np.asarray(w_prev, dtype=float) * (1.0 + np.asarray(returns_prev, dtype=float))
    return grown / grown.sum()


def forecast_tracking_error(w: np.ndarray, b: np.ndarray, Sigma: np.ndarray) -> float:
    """sqrt(12 a' Sigma a) with a = w - b, in return units per year."""
    a = np.asarray(w, dtype=float) - np.asarray(b, dtype=float)
    return float(np.sqrt(max(PERIODS_PER_YEAR * a @ Sigma @ a, 0.0)))


def effective_number(w: np.ndarray) -> float:
    """1 / sum of squared weights: 49 for 1/N over 49 industries, smaller for a concentrated portfolio."""
    w = np.asarray(w, dtype=float)
    return float(1.0 / (w @ w))


def one_way_turnover(w: np.ndarray, w0: np.ndarray) -> float:
    """Half the sum of absolute weight changes: the fraction of the portfolio sold (and bought) at the rebalance."""
    return float(0.5 * np.abs(np.asarray(w, dtype=float) - np.asarray(w0, dtype=float)).sum())


def benchmark_betas(Sigma: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Each asset's beta to the benchmark under Sigma: Sigma b divided by b' Sigma b; the benchmark's own beta is one."""
    Sb = np.asarray(Sigma, dtype=float) @ np.asarray(b, dtype=float)
    return Sb / float(np.asarray(b, dtype=float) @ Sb)


def active_variance_parts(a: np.ndarray, Sigma: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Split a' Sigma a into the market part, (a' beta)^2 times the benchmark's variance, and the rest.

    With beta = Sigma b / (b' Sigma b) the two parts add up to a' Sigma a exactly: the market part is the
    variance of the active return's projection on the benchmark, the rest is the variance of what the
    benchmark leaves unexplained."""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float); Sigma = np.asarray(Sigma, dtype=float)
    beta = benchmark_betas(Sigma, b)
    var_b = float(b @ Sigma @ b)
    market = float((a @ beta) ** 2 * var_b)
    total = float(a @ Sigma @ a)
    return market, total - market


def bounds(b: np.ndarray, constraints: tuple, tilt_mask: np.ndarray, exclude_mask: np.ndarray,
           active_bound: float = C.ACTIVE_WEIGHT_BOUND, tilt_share: float = C.TILT_MAX_SHARE_OF_BENCHMARK) -> tuple[np.ndarray, np.ndarray]:
    """The lower and upper bound on each weight that the named constraints imply."""
    N = len(b)
    lower = np.full(N, -np.inf)
    upper = np.full(N, np.inf)
    if "long_only" in constraints:
        lower = np.maximum(lower, 0.0)
    if "active_weight_bound" in constraints:
        untilted = ~tilt_mask if "tilt" in constraints else np.ones(N, bool)
        lower = np.where(untilted, np.maximum(lower, b - active_bound), lower)
        upper = np.where(untilted, np.minimum(upper, b + active_bound), upper)
    if "tilt" in constraints:
        lower = np.where(tilt_mask, np.maximum(lower, 0.0), lower)
        upper = np.where(tilt_mask, np.minimum(upper, tilt_share * b), upper)
    if "exclusion" in constraints:
        lower = np.where(exclude_mask, 0.0, lower)
        upper = np.where(exclude_mask, 0.0, upper)
    return lower, upper


def _build(Ls: list, b: np.ndarray, lower: np.ndarray, upper: np.ndarray, w0: np.ndarray | None, cap: float | None,
           objective: str = "tracking_error", betas: list | None = None):
    """The cvxpy problem. `Ls` holds one Cholesky factor for the single-covariance problem and one per covariance for the robust
    one, whose objective is the largest of the forecast active variances; `betas` holds the beta vectors the
    beta-neutral constraint applies to, one per covariance."""
    N = len(b)
    w = cp.Variable(N)
    cons = [cp.sum(w) == 1]
    finite_lo = np.isfinite(lower)
    finite_up = np.isfinite(upper)
    if finite_lo.any():
        cons.append(w[finite_lo] >= lower[finite_lo])
    if finite_up.any():
        cons.append(w[finite_up] <= upper[finite_up])
    for beta in betas or []:
        cons.append(beta @ (w - b) == 0)
    turnover_expr = None
    if w0 is not None:
        # one-way turnover through explicit purchases p and sales n, w - w0 = p - n: the same quantity as half the sum of
        # absolute changes, in the form in which trades are written as buys and sells. The solver's status is not relied on
        # in either form (notebook 11, check D5: on a month with no feasible portfolio the solver reported "optimal" with
        # weights that fail the budget); check() tests every returned portfolio, and _solve poses a capped problem only
        # after the smallest feasible turnover is known.
        p = cp.Variable(N, nonneg=True)
        n = cp.Variable(N, nonneg=True)
        cons.append(w - w0 == p - n)
        turnover_expr = 0.5 * cp.sum(p + n)
        if cap is not None:
            cons.append(turnover_expr <= cap)
    if objective == "tracking_error" and len(Ls) == 1:
        obj = cp.Minimize(cp.sum_squares(Ls[0].T @ (w - b)))
    elif objective == "tracking_error":                     # robust: the largest active standard deviation across the covariances
        t = cp.Variable()                                   # written with norms (second-order cones) and in percent, which the solver handles more accurately than squares
        cons += [cp.norm(100.0 * (L.T @ (w - b)), 2) <= t for L in Ls]
        obj = cp.Minimize(t)
    else:                                                   # the smallest feasible one-way turnover
        obj = cp.Minimize(turnover_expr)
    return w, cp.Problem(obj, cons)


def solve(Sigma: np.ndarray, b: np.ndarray, constraints: tuple, w_prev: np.ndarray | None = None,
          tilt_mask: np.ndarray | None = None, exclude_mask: np.ndarray | None = None,
          turnover_cap: float = C.TURNOVER_CAP_MONTHLY_ONE_WAY, active_bound: float = C.ACTIVE_WEIGHT_BOUND,
          tilt_share: float = C.TILT_MAX_SHARE_OF_BENCHMARK, solver: str = C.OPT_SOLVER, tol: float = C.OPT_TOL) -> Solution:
    """The constrained tracking-error minimiser for one month.

    `constraints` is a tuple of names from constants.CONSTRAINT_SETS. `w_prev` is the previous portfolio after
    drift; it is required when "turnover_cap" is among the constraints. If the cap makes the month infeasible,
    the cap is raised to the smallest feasible one-way turnover and the solution says so.
    """
    return _solve([np.asarray(Sigma, dtype=float)], b, constraints, w_prev, tilt_mask, exclude_mask, turnover_cap, active_bound, tilt_share, solver, tol)


def solve_robust(Sigmas: list, b: np.ndarray, constraints: tuple, w_prev: np.ndarray | None = None,
                 tilt_mask: np.ndarray | None = None, exclude_mask: np.ndarray | None = None,
                 turnover_cap: float = C.TURNOVER_CAP_MONTHLY_ONE_WAY, active_bound: float = C.ACTIVE_WEIGHT_BOUND,
                 tilt_share: float = C.TILT_MAX_SHARE_OF_BENCHMARK, solver: str = C.OPT_SOLVER, tol: float = C.OPT_TOL) -> Solution:
    """The robust minimiser: the weights whose largest forecast active variance across the covariances in `Sigmas`
    is smallest, under the same constraints; beta neutrality, when asked, holds under the average of the covariances'
    beta vectors. The tracking error reported is the worst case across the covariances."""
    return _solve([np.asarray(S, dtype=float) for S in Sigmas], b, constraints, w_prev, tilt_mask, exclude_mask, turnover_cap, active_bound, tilt_share, solver, tol)


def _solve(Sigmas: list, b, constraints, w_prev, tilt_mask, exclude_mask, turnover_cap, active_bound, tilt_share, solver, tol) -> Solution:
    b = np.asarray(b, dtype=float)
    N = len(b)
    tilt_mask = np.zeros(N, bool) if tilt_mask is None else np.asarray(tilt_mask, bool)
    exclude_mask = np.zeros(N, bool) if exclude_mask is None else np.asarray(exclude_mask, bool)
    if "turnover_cap" in constraints and w_prev is None:
        raise OptimiserError("the turnover cap needs the previous portfolio")
    if "exclusion" in constraints and (exclude_mask is None or not np.asarray(exclude_mask, bool).any()):
        raise OptimiserError("the exclusion constraint needs a mask naming at least one industry")
    lower, upper = bounds(b, constraints, tilt_mask, exclude_mask, active_bound, tilt_share)
    if (lower > upper + tol).any():
        raise OptimiserError("a weight's lower bound exceeds its upper bound; the constraint set is contradictory for this month")
    Ls = [cholesky_factor(S) for S in Sigmas]
    w0 = None if w_prev is None else np.asarray(w_prev, dtype=float)
    cap = turnover_cap if "turnover_cap" in constraints else None
    # beta neutrality: one equality. With one covariance, its own betas; with more than one (the robust problem), the average
    # of their beta vectors, because one equality per covariance made the 1979-07 problem infeasible under the mandate's
    # bounds, and the minimax objective already penalises the market exposure that remains under each covariance.
    betas = [np.mean([benchmark_betas(S, b) for S in Sigmas], axis=0)] if "beta_neutral" in constraints else None
    relaxed = False

    options = C.OPT_SOLVER_OPTIONS if len(Ls) == 1 else C.OPT_SOLVER_OPTIONS_ROBUST
    accepted = ("optimal",) if len(Ls) == 1 else ("optimal", "optimal_inaccurate")
    if cap is not None:
        # feasibility first: the smallest one-way turnover the other constraints allow, from a linear program. A cap below
        # it would hand the solver a problem with no solution, and on such a problem the solver's status is not reliable
        # (notebook 11, check D5); so the cap is raised to that turnover, with a margin of one part in a million plus tol,
        # and the month is marked relaxed, before the capped problem is posed.
        w_t, prob_t = _build(Ls, b, lower, upper, w0, None, objective="turnover", betas=betas)
        _run(prob_t, solver, options)
        if prob_t.status not in ("optimal", "optimal_inaccurate"):
            raise OptimiserError(f"infeasible without the turnover cap: {prob_t.status}")
        check(_clean(w_t.value), b, lower, upper, w0, None, tol)      # the program's own weights pass the checks too
        if float(prob_t.value) > cap + 10 * tol:
            cap = float(prob_t.value) * (1.0 + 1e-6) + tol
            relaxed = True
    w, prob = _build(Ls, b, lower, upper, w0, cap, betas=betas)
    _run(prob, solver, options)
    x = _clean(w.value)
    if prob.status not in accepted:
        raise OptimiserError(f"solver status {prob.status} on a problem known to be feasible")
    check(x, b, lower, upper, w0, cap, tol)
    a = x - b
    binding = {}
    if "long_only" in constraints:
        binding["long_only"] = int(((x <= tol) & ~exclude_mask).sum())
    if "active_weight_bound" in constraints:
        untilted = ~tilt_mask if "tilt" in constraints else np.ones(N, bool)
        binding["active_weight_bound"] = int((untilted & (np.abs(np.abs(a) - active_bound) <= tol)).sum())
    if "tilt" in constraints:
        binding["tilt"] = int((tilt_mask & (np.abs(x - tilt_share * b) <= tol)).sum())
    to = one_way_turnover(x, w0) if w0 is not None else float("nan")
    if "turnover_cap" in constraints:
        binding["turnover_cap"] = int(abs(to - cap) <= 10 * tol)
    for beta in betas or []:
        if abs(beta @ a) > 10 * tol:
            raise OptimiserError(f"the portfolio's beta differs from the benchmark's by {beta @ a:.2e}")
    te = max(forecast_tracking_error(x, b, S) for S in Sigmas)      # the worst case across the covariances; one covariance, its own
    return Solution(weights=x, active=a, tracking_error=te, turnover=to,
                    turnover_cap_used=cap, relaxed=relaxed, status=prob.status, binding=binding)


def _run(prob, solver: str, options: dict) -> None:
    """Solve with the tight stopping rule; if the solver reports the result as inaccurate at that rule, solve again at
    its default rule (about 1e-8). A single-covariance problem is accepted only when reported optimal; the robust
    problem, written with second-order cones, is accepted as inaccurate too once the feasibility checks pass, and
    the status is recorded so that the evaluation can count such months."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Solution may be inaccurate")   # that case is solved again below at the default rule
        prob.solve(solver=solver, **options)
        if prob.status == "optimal_inaccurate":
            prob.solve(solver=solver)


def _clean(value) -> np.ndarray:
    if value is None:
        return np.full(0, np.nan)
    x = np.asarray(value, dtype=float).ravel()
    return np.where(np.abs(x) < 1e-12, 0.0, x)


def feasible(w: np.ndarray, b: np.ndarray, lower: np.ndarray, upper: np.ndarray, w0: np.ndarray | None, cap: float | None, tol: float) -> bool:
    """True when the weights sum to one, lie inside their bounds and respect the turnover cap, all within tol."""
    if len(w) != len(b) or not np.isfinite(w).all() or abs(w.sum() - 1.0) > tol:
        return False
    if (w < lower - tol).any() or (w > upper + tol).any():
        return False
    if cap is not None and w0 is not None and one_way_turnover(w, w0) > cap + 10 * tol:
        return False
    return True


def check(w: np.ndarray, b: np.ndarray, lower: np.ndarray, upper: np.ndarray, w0: np.ndarray | None, cap: float | None, tol: float) -> None:
    """Raise unless the weights sum to one, lie inside their bounds and respect the turnover cap, all within tol."""
    if len(w) != len(b) or not np.isfinite(w).all():
        raise OptimiserError("the solver returned no weights")
    if abs(w.sum() - 1.0) > tol:
        raise OptimiserError(f"weights sum to {w.sum():.8f}")
    if (w < lower - tol).any() or (w > upper + tol).any():
        raise OptimiserError("a weight lies outside its bounds")
    if cap is not None and w0 is not None and one_way_turnover(w, w0) > cap + 10 * tol:
        raise OptimiserError(f"turnover {one_way_turnover(w, w0):.6f} exceeds the cap {cap:.6f}")


def masks(columns, tilt=C.TILT_INDUSTRIES, exclude=()) -> tuple[np.ndarray, np.ndarray]:
    """Boolean masks over `columns` for the tilted and the excluded industries; a name that is not a column raises."""
    cols = [str(c).strip() for c in columns]
    for name in tuple(tilt) + tuple(exclude):
        if name not in cols:
            raise KeyError(f"{name} is not one of the {len(cols)} industries")
    return np.array([c in tilt for c in cols]), np.array([c in exclude for c in cols])
