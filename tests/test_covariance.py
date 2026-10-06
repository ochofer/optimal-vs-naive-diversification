"""The covariance estimators and their tests on made-up markets with a known covariance, no network."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import constants as C  # noqa: E402
from bp import covariance as CV  # noqa: E402
from bp import simulate as SIM  # noqa: E402


def _market(N=25, T=120, seed=3):
    mkt = SIM.build_market(N, T, seed)
    return mkt.returns, mkt


def _frob(A, B):
    return float(np.sqrt(((A - B) ** 2).sum()))


def test_sample_cov_matches_numpy_and_is_symmetric():
    X, _ = _market()
    S = CV.sample_cov(X)
    assert np.allclose(S, np.cov(X, rowvar=False, ddof=1)) and np.allclose(S, S.T)


def test_ewma_with_a_huge_half_life_is_the_sample_covariance():
    X, _ = _market(T=300)
    S = CV.sample_cov(X)
    E = CV.ewma_cov(X, halflife=1e9)
    assert np.allclose(E, S, rtol=1e-6, atol=1e-10)
    # a short half-life leans on the last observations: the estimate moves with them
    X2 = X.copy(); X2[-1] *= 5
    assert _frob(CV.ewma_cov(X2, 10), CV.ewma_cov(X, 10)) > _frob(CV.ewma_cov(X2, 1e9), CV.ewma_cov(X, 1e9))


def test_lw_scaled_identity_intensity_in_unit_interval_and_closer_to_truth_with_few_observations():
    X, mkt = _market(N=25, T=60)
    est, k = CV.lw_scaled_identity(X)
    assert 0.0 < k < 1.0
    assert np.allclose(est, est.T)
    assert _frob(est, mkt.Sigma) < _frob(CV.sample_cov(X), mkt.Sigma)
    # with many observations the intensity goes to zero
    X_long, _ = _market(N=25, T=20000)
    _, k_long = CV.lw_scaled_identity(X_long)
    assert k_long < 0.01


def test_lw_constant_correlation_intensity_in_unit_interval_and_helps_when_correlations_are_equal():
    rng = np.random.default_rng(5)
    N, T = 20, 60
    sd = np.linspace(0.03, 0.09, N)
    R = np.full((N, N), 0.4); np.fill_diagonal(R, 1.0)
    Sigma = np.outer(sd, sd) * R
    X = rng.multivariate_normal(np.zeros(N), Sigma, size=T)
    est, k = CV.lw_constant_correlation(X)
    assert 0.0 < k <= 1.0
    assert np.allclose(est, est.T)
    assert _frob(est, Sigma) < _frob(CV.sample_cov(X), Sigma)


def test_factor_model_recovers_a_covariance_generated_by_factors():
    rng = np.random.default_rng(7)
    T, N, K = 5000, 15, 3
    F = rng.normal(0, 0.04, size=(T, K))
    B = rng.normal(0.8, 0.4, size=(N, K))
    own = rng.uniform(0.02, 0.05, size=N)
    X = F @ B.T + rng.normal(0, 1, size=(T, N)) * own
    Sigma_true = B @ np.cov(F, rowvar=False, ddof=1) @ B.T + np.diag(own ** 2)
    est, B_hat = CV.factor_cov(X, F)
    assert B_hat.shape == (N, K)
    assert np.abs(B_hat - B).max() < 0.05
    assert _frob(est, Sigma_true) / _frob(Sigma_true, 0 * Sigma_true) < 0.03


def test_pca_model_with_all_components_is_the_sample_covariance_and_with_market_first_recovers_a_one_factor_market():
    X, mkt = _market(N=10, T=3000)
    full, k = CV.pca_cov(X, n_components=10)
    assert k == 10 and np.allclose(full, CV.sample_cov(X), atol=1e-10)
    market = X[:, 0]                                   # asset 0 is the factor itself
    est1, k1 = CV.pca_cov(X, n_components=1, market=market)   # the market alone plus each asset's own variance
    assert k1 == 0
    assert _frob(est1, mkt.Sigma) / _frob(mkt.Sigma, 0 * mkt.Sigma) < 0.05
    est2, k2 = CV.pca_cov(X, n_components=2, market=market)   # one residual component on top, which here fits noise
    assert k2 == 1
    assert _frob(est2, mkt.Sigma) / _frob(mkt.Sigma, 0 * mkt.Sigma) < 0.10
    assert np.all(np.linalg.eigvalsh(est2) > 0)       # positive definite


def test_scaling_and_windows():
    S = np.eye(3) * 2.0
    assert np.allclose(CV.scale_daily_to_monthly(S, 21), S * 21)
    months = pd.period_range("2000-01", "2003-12", freq="M")
    em = pd.DataFrame(np.arange(len(months) * 2).reshape(-1, 2), index=months, columns=["a", "b"])
    w = CV.monthly_window(em, pd.Period("2003-12", "M"), 12)
    assert str(w.index[0]) == "2002-12" and str(w.index[-1]) == "2003-11" and len(w) == 12
    days = pd.period_range("2000-01-03", "2003-12-31", freq="D")
    ed = pd.DataFrame(np.ones((len(days), 2)), index=days, columns=["a", "b"])
    ed.iloc[0, 0] = np.nan                                                          # 2000-01-03 has a missing value
    d = CV.daily_window(ed, pd.Period("2003-01", "M"), 3)
    assert str(d.index[0]) == "2000-01-04" and str(d.index[-1]) == "2002-12-31"     # the missing day is left out


def test_daily_benchmark_uses_the_month_weights_for_every_day_of_the_month():
    days = pd.PeriodIndex(["2000-01-03", "2000-01-04", "2000-02-01"], freq="D")
    returns = pd.DataFrame([[0.01, 0.03], [0.02, 0.00], [0.01, 0.01]], index=days, columns=["a", "b"])
    rf = pd.Series([0.0, 0.0, 0.001], index=days)
    weights = pd.DataFrame([[0.5, 0.5], [0.25, 0.75]], index=pd.PeriodIndex(["2000-01", "2000-02"], freq="M"), columns=["a", "b"])
    b = CV.daily_benchmark_excess(returns, rf, weights)
    assert np.allclose(b.to_numpy(), [0.02, 0.01, 0.01 - 0.001])


def test_bias_statistic_is_one_for_calibrated_forecasts_and_above_one_when_risk_is_under_forecast():
    rng = np.random.default_rng(11)
    r = rng.normal(0, 0.05, size=20000)
    assert abs(CV.bias_statistic(r, np.full(20000, 0.05 ** 2)) - 1.0) < 0.02
    assert CV.bias_statistic(r, np.full(20000, 0.025 ** 2)) > 1.9


def test_active_weights_sum_to_zero_with_the_bound_as_largest_weight():
    A = CV.random_active_weights(49, draws=50, bound=0.02, seed=1)
    assert A.shape == (50, 49)
    assert np.allclose(A.sum(axis=1), 0.0)
    assert np.allclose(np.abs(A).max(axis=1), 0.02)


def test_minimum_variance_portfolios_and_condition_number():
    X, mkt = _market(N=10, T=2000)
    S = CV.sample_cov(X)
    w = CV.min_variance_unconstrained(S)
    assert abs(w.sum() - 1.0) < 1e-12
    w_lo = CV.min_variance_long_only(S)
    assert abs(w_lo.sum() - 1.0) < 1e-9 and (w_lo >= -1e-12).all()
    assert w_lo @ S @ w_lo >= w @ S @ w - 1e-12          # the constraint cannot lower the variance
    assert CV.condition_number(np.diag([4.0, 1.0])) == 4.0


def test_variance_ratio_is_one_for_independent_values_and_follows_the_autocorrelation():
    rng = np.random.default_rng(3)
    e = rng.standard_normal(200_000)
    assert abs(CV.variance_ratio(e, 21) - 1.0) < 0.03
    # an AR(1) series with coefficient rho has variance ratio 1 + 2 * sum_{k=1}^{q-1} (1 - k/q) rho^k
    for rho in (0.2, -0.2):
        x = np.empty_like(e)
        x[0] = e[0]
        for t in range(1, len(e)):
            x[t] = rho * x[t - 1] + e[t]
        q = 21
        expected = 1.0 + 2.0 * sum((1.0 - k / q) * rho ** k for k in range(1, q))
        assert abs(CV.variance_ratio(x, q) - expected) < 0.04, (rho, CV.variance_ratio(x, q), expected)
    assert (CV.variance_ratio(x, 21) < 1.0) is True            # the last rho is negative
    assert np.isnan(CV.variance_ratio(e[:30], 21))              # fewer than two horizons of data: no estimate


def test_estimate_dispatch_matches_the_estimators_and_scales_daily_windows():
    class P:
        pass
    rng = np.random.default_rng(5)
    months = pd.period_range("2000-01", "2012-12", freq="M")
    P.excess_m = pd.DataFrame(rng.standard_normal((len(months), 4)) * 0.05, index=months)
    P.factors_m = pd.DataFrame(rng.standard_normal((len(months), 6)) * 0.03, index=months, columns=["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"])
    P.bench_m = pd.Series(rng.standard_normal(len(months)) * 0.04, index=months)
    days = pd.period_range("2000-01-01", "2012-12-31", freq="D")
    days = days[days.dayofweek < 5]
    P.excess_d = pd.DataFrame(rng.standard_normal((len(days), 4)) * 0.01, index=days)
    P.factors_d = pd.DataFrame(rng.standard_normal((len(days), 6)) * 0.006, index=days, columns=P.factors_m.columns)
    P.bench_d = pd.Series(rng.standard_normal(len(days)) * 0.008, index=days)
    month = pd.Period("2010-06", "M")
    S_m, k_m, n_m = CV.estimate("sample", "monthly_120", month, P)
    assert n_m == 120 and np.isnan(k_m) and np.allclose(S_m, CV.sample_cov(CV.monthly_window(P.excess_m, month).to_numpy()))
    S_d, _, n_d = CV.estimate("sample", "daily_3y", month, P)
    Xd = CV.daily_window(P.excess_d, month, 3)
    assert n_d == len(Xd) and np.allclose(S_d, 21 * CV.sample_cov(Xd.to_numpy()))
    S_lw, k, _ = CV.estimate("ledoit_wolf", "daily_3y", month, P)
    assert 0 <= k <= 1 and S_lw.shape == (4, 4)
    assert len(CV.EVALUATION_VARIANTS) == 5 and len(CV.ALL_VARIANTS) * 4 == 28 == C.EXT_SPEC_COUNT
