"""Tests of the factor objective under the mandate (version 2, module A) on made-up markets whose answers are
known by hand or by an independent solver: feasibility, the budget binding within one basis point, the exposure rising
with the budget in a fixed month, and the attribution identity on a path the objective built."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import linprog, minimize

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from bp import attribution as A  # noqa: E402
from bp import constants as C  # noqa: E402
from bp import optimiser as O  # noqa: E402

TOL = 1e-6
S = np.array([C.FO_TARGET_SIGN[f] for f in C.ATTRIBUTION_FACTORS])


def _market(N=20, seed=1):
    """A one-factor market with idiosyncratic risk, a benchmark, and betas to six factors whose first is the market's."""
    rng = np.random.default_rng(seed)
    beta = rng.uniform(0.6, 1.4, N)
    own = rng.uniform(0.03, 0.08, N) ** 2
    Sigma = (0.045 ** 2 * np.outer(beta, beta) + np.diag(own)) / 12      # monthly
    b = rng.uniform(0.5, 2.0, N)
    b = b / b.sum()
    B = rng.normal(0.0, 0.3, (N, len(C.ATTRIBUTION_FACTORS)))
    B[:, 0] = beta
    return Sigma, b, B


def _mandate_masks(N):
    tilt = np.zeros(N, bool)
    tilt[0] = True
    excl = np.zeros(N, bool)
    excl[1] = True
    return tilt, excl


def test_feasibility_every_constraint_and_the_budget_hold_on_the_returned_weights():
    Sigma, b, B = _market()
    tilt, excl = _mandate_masks(len(b))
    cons = C.CONSTRAINT_SETS["C3"]
    base = O.solve(Sigma, b, cons, w_prev=b, tilt_mask=tilt, exclude_mask=excl)      # a first month, as the evaluation starts
    sol = O.solve_factor_objective(Sigma, b, B, S, 0.0075, cons, w_prev=base.weights, tilt_mask=tilt, exclude_mask=excl)
    lower, upper = O.bounds(b, cons, tilt, excl)
    assert sol.budget_met and sol.status == "optimal"
    assert abs(sol.weights.sum() - 1) < TOL and (sol.weights >= lower - TOL).all() and (sol.weights <= upper + TOL).all()
    assert sol.weights[1] <= TOL and sol.weights[0] <= 0.5 * b[0] + TOL
    assert O.one_way_turnover(sol.weights, base.weights) <= C.TURNOVER_CAP_MONTHLY_ONE_WAY + 10 * TOL
    assert sol.tracking_error <= 0.0075 * (1 + 1e-6) + 10 * TOL
    beta_b = O.benchmark_betas(Sigma, b)
    assert abs(beta_b @ sol.active) < 10 * TOL
    assert np.allclose(sol.exposures, A.active_exposures(B, sol.weights, b))
    assert abs(sol.objective - S @ sol.exposures) < 1e-12
    assert sol.objective >= O.targeted_exposure(B, S, base.weights, b) - 1e-9     # at least what the minimiser's portfolio carries


def test_budget_binds_within_one_basis_point_and_agrees_with_an_independent_solver():
    # bounds only, no turnover cap: maximise g' (w - b) with (w - b)' Sigma (w - b) <= tau^2 / 12, checked against SLSQP
    Sigma, b, B = _market(N=8, seed=3)
    cons = ("long_only", "active_weight_bound")
    tau = 0.0040
    sol = O.solve_factor_objective(Sigma, b, B, S, tau, cons, active_bound=0.05)
    assert sol.budget_met and sol.binding["budget"] == 1
    assert abs(sol.tracking_error - tau) <= C.FO_E1_BIND_TOL_ANNUAL
    g = B @ S
    lower, upper = O.bounds(b, cons, np.zeros(8, bool), np.zeros(8, bool), active_bound=0.05)
    res = minimize(lambda w: -g @ (w - b), b, method="SLSQP", bounds=list(zip(lower, upper)),
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1},
                                {"type": "ineq", "fun": lambda w: tau ** 2 / 12 - (w - b) @ Sigma @ (w - b)}],
                   options={"ftol": 1e-14, "maxiter": 2000})
    assert res.success
    assert abs(-res.fun - sol.objective) < 1e-6
    assert np.allclose(res.x, sol.weights, atol=1e-4)


def test_a_loose_budget_leaves_the_bounds_as_the_only_limit_and_matches_the_linear_program():
    Sigma, b, B = _market(N=8, seed=3)
    cons = ("long_only", "active_weight_bound")
    sol = O.solve_factor_objective(Sigma, b, B, S, 1.0, cons, active_bound=0.05)
    assert sol.budget_met and sol.binding["budget"] == 0
    g = B @ S
    lower, upper = O.bounds(b, cons, np.zeros(8, bool), np.zeros(8, bool), active_bound=0.05)
    lp = linprog(-g, A_eq=np.ones((1, 8)), b_eq=[1.0], bounds=list(zip(lower, upper)), method="highs")
    assert lp.success
    assert abs(-lp.fun - g @ b - sol.objective) < 1e-8
    assert np.allclose(lp.x, sol.weights, atol=1e-6)


def test_exposure_rises_with_the_budget_in_a_fixed_month():
    Sigma, b, B = _market()
    tilt, excl = _mandate_masks(len(b))
    cons = ("long_only", "active_weight_bound", "tilt", "beta_neutral", "exclusion")     # no turnover cap, and a wide active bound: the budget is the limit on the move
    objs = []
    for tau in C.FO_BUDGETS_ANNUAL:
        sol = O.solve_factor_objective(Sigma, b, B, S, tau, cons, tilt_mask=tilt, exclude_mask=excl, active_bound=0.10)
        assert sol.budget_met and sol.binding["budget"] == 1
        objs.append(sol.objective)
    assert objs[0] < objs[1] < objs[2]
    assert all(np.isfinite(objs))


def test_an_infeasible_budget_takes_the_minimiser_and_says_so():
    Sigma, b, B = _market()
    tilt, excl = _mandate_masks(len(b))
    cons = C.CONSTRAINT_SETS["C3"]
    base = O.solve(Sigma, b, cons, w_prev=b, tilt_mask=tilt, exclude_mask=excl)
    assert base.tracking_error > 0.0010
    sol = O.solve_factor_objective(Sigma, b, B, S, 0.0010, cons, w_prev=b, tilt_mask=tilt, exclude_mask=excl)
    assert not sol.budget_met and sol.binding["budget"] == 0
    assert np.allclose(sol.weights, base.weights, atol=1e-8)
    assert abs(sol.tracking_error - base.tracking_error) < 1e-9
    assert sol.relaxed == base.relaxed and sol.turnover_cap_used == base.turnover_cap_used


def test_single_factor_target_moves_only_that_exposure_up():
    Sigma, b, B = _market(N=12, seed=5)
    cons = ("long_only", "active_weight_bound")
    s_val = np.zeros(len(S)); s_val[C.ATTRIBUTION_FACTORS.index("HML")] = 1.0
    sol = O.solve_factor_objective(Sigma, b, B, s_val, 0.0050, cons, active_bound=0.03)
    assert sol.budget_met
    assert sol.exposures[C.ATTRIBUTION_FACTORS.index("HML")] > 0
    assert abs(sol.objective - sol.exposures[C.ATTRIBUTION_FACTORS.index("HML")]) < 1e-12


def test_attribution_identity_on_a_path_the_objective_built():
    Sigma, b, B = _market()
    tilt, excl = _mandate_masks(len(b))
    cons = C.CONSTRAINT_SETS["C3"]
    rng = np.random.default_rng(7)
    months = pd.period_range("2020-01", periods=4, freq="M")
    factors = pd.DataFrame(rng.normal(0, 0.02, (4, len(C.ATTRIBUTION_FACTORS))), index=months, columns=C.ATTRIBUTION_FACTORS)
    own = rng.normal(0, 0.01, (4, len(b)))
    returns = pd.DataFrame(factors.to_numpy() @ B.T + own, index=months, columns=[f"i{k}" for k in range(len(b))])
    bench = pd.DataFrame(np.tile(b, (4, 1)), index=months, columns=returns.columns)
    w_prev, W, active = b.copy(), [], []
    for m in months:
        sol = O.solve_factor_objective(Sigma, b, B, S, 0.0075, cons, w_prev=w_prev, tilt_mask=tilt, exclude_mask=excl)
        W.append(sol.weights)
        active.append(float(sol.weights @ returns.loc[m] - b @ returns.loc[m]))
        w_prev = sol.weights
    W = pd.DataFrame(W, index=months, columns=returns.columns)
    att = A.attribute(W, bench, {m: B for m in months}, factors, pd.Series(active, index=months))
    assert att["identity error"].abs().max() <= C.ATTRIBUTION_IDENTITY_MAX_ABS_ERROR
    # the targeted exposure the solver reported is the attribution's, month by month
    for m, sol_w in zip(months, W.to_numpy()):
        x = A.active_exposures(B, sol_w, b)
        assert abs(S @ x - O.targeted_exposure(B, S, sol_w, b)) < 1e-12


def test_bad_inputs_raise():
    Sigma, b, B = _market(N=6)
    with pytest.raises(O.OptimiserError):
        O.solve_factor_objective(Sigma, b, B[:, :3], S, 0.01, ("long_only",))
    with pytest.raises(O.OptimiserError):
        O.solve_factor_objective(Sigma, b, B, S, 0.0, ("long_only",))
    with pytest.raises(O.OptimiserError):
        O.solve_factor_objective(Sigma, b, B, S, 0.01, ("long_only", "turnover_cap"))
