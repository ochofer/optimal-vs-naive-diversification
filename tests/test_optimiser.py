"""Tests of the optimiser on made-up markets whose answers are known by hand or by an independent solver."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest
from scipy.optimize import linprog, minimize

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from bp import optimiser as O  # noqa: E402

TOL = 1e-6


def _market(N=6, seed=0):
    rng = np.random.default_rng(seed)
    beta = rng.uniform(0.6, 1.4, N)
    own = rng.uniform(0.02, 0.06, N) ** 2
    Sigma = 0.04 ** 2 * np.outer(beta, beta) + np.diag(own)
    b = rng.uniform(0.5, 2.0, N)
    return Sigma, b / b.sum()


def test_drifted_weights_follow_the_returns_and_sum_to_one():
    w0 = np.array([0.5, 0.5])
    r = np.array([0.10, -0.10])          # 0.55 / (0.55 + 0.45) and 0.45 / 1.00
    d = O.drifted_weights(w0, r)
    assert np.allclose(d, [0.55, 0.45]) and abs(d.sum() - 1) < 1e-12


def test_benchmark_is_the_answer_when_it_is_feasible():
    Sigma, b = _market()
    for cons in [("long_only",), ("long_only", "active_weight_bound"), ("long_only", "active_weight_bound", "turnover_cap")]:
        s = O.solve(Sigma, b, cons, w_prev=b)
        assert np.allclose(s.weights, b, atol=1e-5)
        assert s.tracking_error < 1e-4 and s.status == "optimal" and not s.relaxed


def test_two_assets_tilt_moves_half_the_weight_to_the_other_asset():
    Sigma = np.array([[0.04, 0.01], [0.01, 0.02]])
    b = np.array([0.4, 0.6])
    tilt = np.array([True, False])
    s = O.solve(Sigma, b, ("long_only", "tilt"), tilt_mask=tilt, tilt_share=0.5)
    assert np.allclose(s.weights, [0.2, 0.8], atol=1e-6)
    a = np.array([-0.2, 0.2])
    assert abs(s.tracking_error - np.sqrt(12 * a @ Sigma @ a)) < 1e-6
    assert s.binding["tilt"] == 1


def test_three_assets_tilt_goes_where_the_covariance_says():
    # a1 is forced to -d; the split of +d between assets 2 and 3 minimising a' Sigma a is
    # x = d (s12 - s13 - s23 + s33) / (s22 - 2 s23 + s33) for asset 2 (first-order condition by hand)
    Sigma = np.array([[0.040, 0.020, 0.005],
                      [0.020, 0.030, 0.004],
                      [0.005, 0.004, 0.025]])
    b = np.array([0.30, 0.35, 0.35])
    d = 0.15
    x = d * (Sigma[0, 1] - Sigma[0, 2] - Sigma[1, 2] + Sigma[2, 2]) / (Sigma[1, 1] - 2 * Sigma[1, 2] + Sigma[2, 2])
    s = O.solve(Sigma, b, ("long_only", "tilt"), tilt_mask=np.array([True, False, False]), tilt_share=0.5)
    assert np.allclose(s.active, [-d, x, d - x], atol=1e-6)
    assert s.active[1] > s.active[2]       # asset 2 moves more with the tilted asset, so it takes more of the weight


def test_active_bound_is_hard_and_raises_when_it_cannot_absorb_the_tilt():
    Sigma, b = _market(N=4, seed=1)
    b = np.array([0.25, 0.25, 0.25, 0.25])
    tilt = np.array([True, False, False, False])
    # the tilt removes 0.125; three untilted assets at +0.02 each absorb 0.06: contradictory
    with pytest.raises(O.OptimiserError):
        O.solve(Sigma, b, ("long_only", "active_weight_bound", "tilt"), tilt_mask=tilt, active_bound=0.02)
    s = O.solve(Sigma, b, ("long_only", "active_weight_bound", "tilt"), tilt_mask=tilt, active_bound=0.05)
    assert (s.active[1:] <= 0.05 + TOL).all() and abs(s.active[1:].sum() - 0.125) < 1e-6


def test_turnover_cap_binds_from_far_away_and_is_relaxed_when_the_tilt_demands_more():
    Sigma, b = _market()
    N = len(b)
    start = np.ones(N) / N
    s_cap = O.solve(Sigma, b, ("long_only", "turnover_cap"), w_prev=start, turnover_cap=0.02)
    assert abs(s_cap.turnover - 0.02) < 1e-5 and s_cap.binding["turnover_cap"] == 1 and not s_cap.relaxed
    s_free = O.solve(Sigma, b, ("long_only",), w_prev=start)
    assert s_cap.tracking_error > s_free.tracking_error + 1e-6
    # with the active bound on as well, 1/N is more than 0.02 of one-way turnover away from the box around b,
    # so the cap is relaxed to the smallest feasible turnover, which is the distance to that box
    s_box = O.solve(Sigma, b, ("long_only", "active_weight_bound", "turnover_cap"), w_prev=start, turnover_cap=0.02, active_bound=0.02)
    # the smallest feasible turnover, by an independent linear program: w = start + p - n, p, n >= 0, minimise sum(p + n) / 2
    lower, upper = O.bounds(b, ("long_only", "active_weight_bound"), np.zeros(N, bool), np.zeros(N, bool), 0.02, 0.5)
    c = np.concatenate([np.zeros(N), 0.5 * np.ones(2 * N)])
    A_eq = np.block([[np.eye(N), -np.eye(N), np.eye(N)], [np.ones((1, N)), np.zeros((1, 2 * N))]])
    lp = linprog(c, A_eq=A_eq, b_eq=np.concatenate([start, [1.0]]), bounds=list(zip(lower, upper)) + [(0, None)] * (2 * N), method="highs")
    assert lp.success
    assert s_box.relaxed and abs(s_box.turnover - lp.fun) < 1e-5
    # from the benchmark itself, a tilt that removes 0.5 * b_0 needs one-way turnover of exactly that amount
    tilt = np.zeros(N, bool); tilt[0] = True
    s_tilt = O.solve(Sigma, b, ("long_only", "active_weight_bound", "turnover_cap", "tilt"), w_prev=b, tilt_mask=tilt,
                     turnover_cap=0.001, active_bound=0.5)
    assert s_tilt.relaxed and abs(s_tilt.turnover - 0.5 * b[0]) < 1e-5
    assert s_tilt.turnover_cap_used >= 0.5 * b[0] - 1e-6


def test_exclusion_sets_the_weight_to_zero():
    Sigma, b = _market()
    excl = np.zeros(len(b), bool); excl[2] = True
    s = O.solve(Sigma, b, ("long_only", "exclusion"), exclude_mask=excl)
    assert s.weights[2] == 0.0 and abs(s.weights.sum() - 1) < TOL and s.tracking_error > 0


def test_against_an_independent_solver_on_a_box_bounded_problem():
    Sigma, b = _market(N=8, seed=3)
    tilt = np.zeros(8, bool); tilt[[0, 5]] = True
    s = O.solve(Sigma, b, ("long_only", "active_weight_bound", "tilt"), tilt_mask=tilt, active_bound=0.03, tilt_share=0.5)
    lower, upper = O.bounds(b, ("long_only", "active_weight_bound", "tilt"), tilt, np.zeros(8, bool), 0.03, 0.5)
    res = minimize(lambda w: (w - b) @ Sigma @ (w - b), x0=b, jac=lambda w: 2 * Sigma @ (w - b),
                   bounds=list(zip(lower, upper)), constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(8)}],
                   method="SLSQP", options={"ftol": 1e-14, "maxiter": 500})
    assert res.success
    assert np.allclose(s.weights, res.x, atol=1e-5)
    assert abs(s.tracking_error - np.sqrt(12 * res.fun)) < 1e-6


def test_effective_number_and_one_way_turnover():
    assert abs(O.effective_number(np.ones(49) / 49) - 49) < 1e-9
    assert abs(O.effective_number(np.array([1.0, 0.0])) - 1) < 1e-12
    assert abs(O.one_way_turnover(np.array([0.5, 0.5]), np.array([0.6, 0.4])) - 0.1) < 1e-12


def test_masks_name_the_industries_and_reject_unknown_names():
    cols = ["Agric", "Coal ", "Oil  ", "Util ", "Banks"]
    t, e = O.masks(cols, tilt=("Coal", "Oil", "Util"), exclude=("Banks",))
    assert t.tolist() == [False, True, True, True, False] and e.tolist() == [False, False, False, False, True]
    with pytest.raises(KeyError):
        O.masks(cols, tilt=("Gold",))


def test_beta_neutral_constraint_and_the_variance_decomposition():
    Sigma, b = _market(N=8, seed=7)
    tilt = np.zeros(8, bool); tilt[0] = True
    s = O.solve(Sigma, b, ("long_only", "tilt", "beta_neutral"), tilt_mask=tilt, tilt_share=0.5)
    beta = O.benchmark_betas(Sigma, b)
    assert abs(beta @ b - 1.0) < 1e-12                       # the benchmark's own beta is one
    assert abs(beta @ s.active) < 1e-6                       # the portfolio's beta equals the benchmark's
    market, rest = O.active_variance_parts(s.active, Sigma, b)
    assert market < 1e-12 and abs(market + rest - s.active @ Sigma @ s.active) < 1e-15
    s_free = O.solve(Sigma, b, ("long_only", "tilt"), tilt_mask=tilt, tilt_share=0.5)
    assert s.tracking_error >= s_free.tracking_error - 1e-9  # a constraint cannot lower the minimum
    m2, r2 = O.active_variance_parts(s_free.active, Sigma, b)
    assert abs(m2 + r2 - s_free.active @ Sigma @ s_free.active) < 1e-15 and m2 >= 0


def test_robust_portfolio_is_the_minimax_and_reduces_to_the_single_problem():
    Sigma_a, b = _market(N=8, seed=11)
    Sigma_b, _ = _market(N=8, seed=12)
    tilt = np.zeros(8, bool); tilt[0] = True
    cons = ("long_only", "tilt", "beta_neutral")
    same = O.solve_robust([Sigma_a, Sigma_a], b, cons, tilt_mask=tilt)
    single = O.solve(Sigma_a, b, cons, tilt_mask=tilt)
    assert np.allclose(same.weights, single.weights, atol=1e-5) and abs(same.tracking_error - single.tracking_error) < 1e-6
    # the minimax property, on a feasible set the single problems share (no beta constraint, which would differ by covariance)
    plain = ("long_only", "tilt")
    rob = O.solve_robust([Sigma_a, Sigma_b], b, plain, tilt_mask=tilt)
    s_a, s_b = O.solve(Sigma_a, b, plain, tilt_mask=tilt), O.solve(Sigma_b, b, plain, tilt_mask=tilt)
    worst = lambda w: max(O.forecast_tracking_error(w, b, S) for S in (Sigma_a, Sigma_b))
    assert rob.status == "optimal"
    assert rob.tracking_error <= worst(s_a.weights) + 1e-7 and rob.tracking_error <= worst(s_b.weights) + 1e-7
    assert abs(rob.tracking_error - worst(rob.weights)) < 1e-9
    # each covariance's own portfolio is at least as good under that covariance as the robust one
    assert O.forecast_tracking_error(rob.weights, b, Sigma_a) >= s_a.tracking_error - 1e-9
    assert O.forecast_tracking_error(rob.weights, b, Sigma_b) >= s_b.tracking_error - 1e-9
    # with beta neutrality the robust portfolio is neutral under the average of the covariances' betas
    rob_bn = O.solve_robust([Sigma_a, Sigma_b], b, cons, tilt_mask=tilt)
    beta_mean = 0.5 * (O.benchmark_betas(Sigma_a, b) + O.benchmark_betas(Sigma_b, b))
    assert abs(beta_mean @ rob_bn.active) < 1e-6
    assert rob_bn.tracking_error >= rob.tracking_error - 1e-9
