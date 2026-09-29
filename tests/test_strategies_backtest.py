"""Known-answer checks for the portfolio rules and the rolling evaluation, no network."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import backtest as B  # noqa: E402
from bp import strategies as S  # noqa: E402


def _simulated(n_assets=5, months=200_000, seed=1):
    rng = np.random.default_rng(seed)
    mu = np.array([0.004, 0.006, 0.005, 0.007, 0.003])[:n_assets]
    A = rng.normal(size=(n_assets, n_assets))
    Sigma = A @ A.T / 100 + np.eye(n_assets) * 0.001
    return mu, Sigma, rng.multivariate_normal(mu, Sigma, size=months)


def test_mv_recovers_true_tangency_weights():
    mu, Sigma, R = _simulated()
    w_true = np.linalg.solve(Sigma, mu)
    w_true /= abs(w_true.sum())
    assert np.abs(S.mv(R) - w_true).max() < 0.01


def test_min_variance_recovers_true_weights_and_sums_to_one():
    mu, Sigma, R = _simulated()
    w_true = np.linalg.solve(Sigma, np.ones(len(mu)))
    w_true /= w_true.sum()
    w = S.min_variance(R)
    assert abs(w.sum() - 1.0) < 1e-12
    assert np.abs(w - w_true).max() < 0.01


def test_normalise_keeps_direction_of_a_net_short_position():
    w = S.normalise(np.array([-0.6, -0.9, 0.5]))
    assert abs(w.sum() + 1.0) < 1e-12


def test_ew_and_vw():
    R = np.zeros((10, 4))
    assert np.allclose(S.ew(R), 0.25)
    assert list(S.vw(2)(R)) == [0.0, 0.0, 1.0, 0.0]


def test_in_sample_sharpe_equals_tangency_sharpe():
    mu, Sigma, R = _simulated()
    sr = S.in_sample_sharpe(R)
    mu_hat, Sigma_hat = S.sample_moments(R)
    assert abs(sr - np.sqrt(mu_hat @ np.linalg.solve(Sigma_hat, mu_hat))) < 1e-12


def test_rolling_counts_and_first_month_untraded():
    idx = pd.period_range("2000-01", periods=30, freq="M")
    R = pd.DataFrame(np.random.default_rng(0).normal(0.005, 0.04, size=(30, 3)), index=idx)
    bt = B.rolling(R, S.ew, window=12)
    assert len(bt.oos) == 18
    assert str(bt.oos.index[0]) == "2001-01"
    assert np.isnan(bt.turnover.iloc[0]) and not np.isnan(bt.turnover.iloc[1])
    # 1/N's turnover is the drift only: recompute one month by hand.
    w = np.full(3, 1 / 3)
    r = R.iloc[12].to_numpy()
    drifted = w * (1 + r) / (1 + w @ r)
    assert abs(bt.turnover.iloc[1] - np.abs(w - drifted).sum()) < 1e-12
    assert abs(bt.oos.iloc[0] - w @ r) < 1e-12


def test_drift_keeps_sign_of_net_short_portfolio():
    w = np.array([-0.5, -0.5])
    r = np.array([0.02, -0.01])
    d = B.drift(w, r)
    assert d.sum() < 0


def test_net_of_cost_charges_turnover_after_the_return():
    idx = pd.period_range("2000-01", periods=3, freq="M")
    bt = B.Backtest("x", pd.Series([0.01, 0.02, -0.01], index=idx), pd.DataFrame(), pd.Series([np.nan, 0.5, 0.2], index=idx), pd.DataFrame())
    net = B.net_of_cost(bt, cost=0.005)
    assert abs(net.iloc[0] - 0.01) < 1e-12
    assert abs(net.iloc[1] - ((1.02) * (1 - 0.005 * 0.5) - 1)) < 1e-12


def test_sharpe_pvalue_is_one_for_identical_series_and_small_for_different():
    x = pd.Series(np.random.default_rng(2).normal(0.01, 0.05, 400))
    assert abs(B.sharpe_pvalue(x, x) - 1.0) < 1e-9
    y = x - 0.02
    assert B.sharpe_pvalue(x, y) < 0.01


def test_ceq_pvalue_is_one_for_identical_series():
    x = pd.Series(np.random.default_rng(3).normal(0.01, 0.05, 400))
    assert abs(B.ceq_pvalue(x, x) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Bayes-Stein and the constrained rules (notebook 03)
# ---------------------------------------------------------------------------

from scipy.optimize import minimize  # noqa: E402


def _random_problem(rng, N):
    A = rng.normal(size=(N, N))
    Sigma = A @ A.T / N * 0.002 + 0.0005 * np.eye(N)
    mu = rng.normal(0.005, 0.004, N)
    return mu, Sigma


def test_nonneg_mean_variance_satisfies_kkt_and_matches_lbfgsb():
    rng = np.random.default_rng(10)
    for N in (3, 8, 24):
        mu, Sigma = _random_problem(rng, N)
        x = S.nonneg_mean_variance(mu, Sigma)
        g = Sigma @ x - mu
        assert np.all(x >= 0)
        assert np.all(np.abs(g[x > 1e-12]) < 1e-8)       # active assets: zero gradient
        assert np.all(g[x <= 1e-12] > -1e-8)             # excluded assets: gradient pushes them negative
        res = minimize(lambda z: 0.5 * z @ Sigma @ z - mu @ z, np.ones(N) / N, jac=lambda z: Sigma @ z - mu,
                       bounds=[(0, None)] * N, method="L-BFGS-B", options={"ftol": 1e-15, "gtol": 1e-12, "maxiter": 10000})
        assert np.abs(res.x - x).max() < 1e-5


def test_budget_mean_variance_matches_slsqp():
    rng = np.random.default_rng(11)
    for N in (3, 8, 24):
        mu, Sigma = _random_problem(rng, N)
        w = S.budget_mean_variance(mu, Sigma, gamma=1.0)
        assert abs(w.sum() - 1.0) < 1e-12 and w.min() >= -1e-15
        cons = [{"type": "eq", "fun": lambda z: z.sum() - 1.0, "jac": lambda z: np.ones(N)}]
        res = minimize(lambda z: 0.5 * z @ Sigma @ z - mu @ z, np.ones(N) / N, jac=lambda z: Sigma @ z - mu,
                       bounds=[(0, None)] * N, constraints=cons, method="SLSQP", options={"ftol": 1e-15, "maxiter": 10000})
        assert np.abs(res.x - w).max() < 1e-5


def test_constrained_min_variance_matches_slsqp_and_respects_floor():
    rng = np.random.default_rng(12)
    for N in (3, 8, 24):
        _, Sigma = _random_problem(rng, N)
        for lower in (0.0, 0.5 / N):
            w = S.constrained_min_variance(Sigma, lower)
            assert abs(w.sum() - 1.0) < 1e-12 and w.min() >= lower - 1e-10
            cons = [{"type": "eq", "fun": lambda z: z.sum() - 1.0, "jac": lambda z: np.ones(N)}]
            res = minimize(lambda z: z @ Sigma @ z, np.ones(N) / N, jac=lambda z: 2 * Sigma @ z,
                           bounds=[(lower, None)] * N, constraints=cons, method="SLSQP", options={"ftol": 1e-15, "maxiter": 10000})
            assert np.abs(res.x - w).max() < 1e-5


def test_min_c_equals_min_when_no_constraint_binds():
    rng = np.random.default_rng(13)
    Sigma = np.diag([0.001, 0.002, 0.003])       # uncorrelated: minimum-variance weights are all positive
    R = rng.multivariate_normal(np.zeros(3), Sigma, size=5000)
    assert np.abs(S.min_c(R) - S.min_variance(R)).max() < 1e-8


def test_bayes_stein_phi_form_and_limit():
    mu, Sigma, R = _simulated(months=120)
    mu_bs, Sigma_bs, phi = S.bayes_stein_moments(R)
    M, N = R.shape
    # phi must equal DGU equation (5)
    m = R.mean(axis=0)
    dev = R - m
    S_ = dev.T @ dev / (M - N - 2)
    w_min = np.linalg.solve(S_, np.ones(N)); w_min /= w_min.sum()
    d = m - m @ w_min
    phi_eq5 = (N + 2) / ((N + 2) + M * (d @ np.linalg.solve(S_, d)))
    assert abs(phi - phi_eq5) < 1e-12
    assert 0 < phi < 1
    # the shrunk mean lies between the sample mean and the minimum-variance mean
    assert np.allclose(mu_bs, (1 - phi) * m + phi * (m @ w_min))
    # phi = lambda / (M + lambda) falls as the window lengthens, and bs approaches mv
    _, _, R_long = _simulated(months=200_000, seed=5)
    _, _, phi_long = S.bayes_stein_moments(R_long)
    assert phi_long < phi and phi_long < 0.05
    assert np.abs(S.bs(R_long) - S.mv(R_long)).max() < 0.05
