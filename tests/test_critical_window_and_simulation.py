"""Known answers for DGU's Proposition 1 and for the simulated market of section 5.1."""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import constants as C  # noqa: E402
from bp import critical_window as CW  # noqa: E402
from bp import simulate as SIM  # noqa: E402


def test_every_figure_1_value_the_paper_states_is_reproduced():
    table = CW.figure_1_table()
    assert (table["verdict"] == "pass").all(), table[table["verdict"] != "pass"]
    # the two numbers the abstract quotes
    assert CW.critical_window(25, 0.15, 0.12) > 3000
    assert CW.critical_window(50, 0.15, 0.12) > 6000


def test_critical_window_orders_the_three_cases_as_the_paper_says():
    # p. 1939: most of the cost is the mean; case 2 (mean known) needs far fewer months than case 1 or 3
    m1 = CW.critical_window(25, 0.15, 0.12, case=1)
    m2 = CW.critical_window(25, 0.15, 0.12, case=2)
    m3 = CW.critical_window(25, 0.15, 0.12, case=3)
    assert m2 < m1 < m3
    # more assets, longer window, and k < 1, h > 0
    assert CW.critical_window(50, 0.15, 0.12) > CW.critical_window(25, 0.15, 0.12)
    assert CW.k_factor(1000, 25) < 1 and CW.h_factor(1000, 25) > 0


def test_simulated_market_moments_and_shared_factor_path():
    m10, m25 = SIM.build_market(10), SIM.build_market(25)
    # the factor is the first asset and its returns are shared across N
    assert np.allclose(m10.returns[:, 0], m25.returns[:, 0])
    # true tangency Sharpe equals the factor's: 0.08/0.16 a year, /sqrt(12) a month
    w = m25.true_tangency_weights
    sr = m25.mu @ w / np.sqrt(w @ m25.Sigma @ w)
    assert abs(sr - 0.08 / 0.16 / np.sqrt(12)) < 1e-12
    # sample moments of a 24,000-month simulated history sit close to the population ones
    assert np.abs(m25.returns.mean(axis=0) - m25.mu).max() < 0.002
    assert np.abs(np.cov(m25.returns, rowvar=False) - m25.Sigma).max() < 0.0003
    # betas evenly spread, idiosyncratic vol inside the stated range
    assert m25.betas[1] == 0.5 and m25.betas[-1] == 1.5
    ann = np.sqrt(m25.idio_var[1:] * 12)
    assert ann.min() >= 0.10 and ann.max() <= 0.30
    assert m25.returns.shape == (C.SIM_T, 25)


def test_normal_market_unchanged_by_the_fat_tail_option():
    # values recorded from the simulator before the dof option was added (seed 20260910, N = 10)
    m = SIM.build_market(10)
    assert m.dof is None
    np.testing.assert_allclose(m.returns[0, :3], [0.00838968, 0.07585716, -0.00336966], atol=1e-8)
    assert abs(m.returns.sum() - 1514.049004083914) < 1e-6
    assert abs(m.idio_var[1] - 0.0026518219576037055) < 1e-15


def test_fat_tailed_market_keeps_the_moments_and_fattens_the_tails():
    normal = SIM.build_market(10)
    for dof in C.SIM_T_DOF:
        t = SIM.build_market(10, dof=dof)
        # same true moments, same betas, same idiosyncratic volatilities
        np.testing.assert_array_equal(t.mu, normal.mu)
        np.testing.assert_array_equal(t.Sigma, normal.Sigma)
        # sample covariance stays close to the population one: the scaling does not change the variance
        S = np.cov(t.returns, rowvar=False)
        assert np.allclose(np.diag(S), np.diag(t.Sigma), rtol=0.06)
        assert np.allclose(t.returns.mean(axis=0), t.mu, atol=0.002)
        # paired with the normal market: every shock keeps its sign, only its size changes
        shock_n = normal.returns[:, 0] - normal.mu[0]
        shock_t = t.returns[:, 0] - t.mu[0]
        assert np.all(np.sign(shock_n) == np.sign(shock_t))
        # fatter tails than the normal market
        assert SIM.excess_kurtosis(t.returns[:, 0]) > SIM.excess_kurtosis(normal.returns[:, 0]) + 0.3
    # the fatter of the two is fatter
    k10 = SIM.excess_kurtosis(SIM.build_market(10, dof=10).returns[:, 0])
    k5 = SIM.excess_kurtosis(SIM.build_market(10, dof=5).returns[:, 0])
    assert k5 > k10
    # kurtosis of a t with 10 degrees of freedom is 1 in excess, of 5 it is 6; the sample values are noisy but of that order
    assert 0.5 < k10 < 2.0
    assert 3.0 < k5 < 12.0


def test_garch_market_keeps_the_moments_and_clusters_the_volatility():
    normal = SIM.build_market(10)
    g = SIM.build_market(10, garch=True)
    assert g.garch and g.dof is None and g.scales.shape == g.returns.shape
    np.testing.assert_array_equal(g.mu, normal.mu)
    np.testing.assert_array_equal(g.Sigma, normal.Sigma)
    # unconditional variance unchanged: the scales average one in the square
    assert abs(np.mean(g.scales**2) - 1.0) < 0.03
    S = np.cov(g.returns, rowvar=False)
    assert np.allclose(np.diag(S), np.diag(g.Sigma), rtol=0.08)
    assert np.allclose(g.returns.mean(axis=0), g.mu, atol=0.002)
    # paired with the normal market: every shock keeps its sign
    assert np.all(np.sign(g.returns[:, 0] - g.mu[0]) == np.sign(normal.returns[:, 0] - normal.mu[0]))
    # clustering: squared factor returns are autocorrelated under GARCH and uncorrelated in the normal market
    a_g = SIM.autocorrelation((g.returns[:, 0] - g.mu[0]) ** 2)
    a_n = SIM.autocorrelation((normal.returns[:, 0] - normal.mu[0]) ** 2)
    assert a_g > 0.10 and abs(a_n) < 0.03
    # the clustering produces some excess kurtosis, less than the t with 5 degrees of freedom
    assert 0.2 < SIM.excess_kurtosis(g.returns[:, 0]) < 3.0
    # the factor's scale and an asset's own scale are different processes
    assert np.corrcoef(g.scales[:, 0], g.scales[:, 5])[0, 1] < 0.2
    # one relaxation at a time
    try:
        SIM.build_market(10, dof=5, garch=True)
        raise AssertionError("dof and garch together should be refused")
    except ValueError:
        pass


def test_garch_scales_formula():
    # with alpha = beta = 0 the scales are all one; with the project's parameters the recursion matches a hand computation
    z = np.array([[1.0], [2.0], [0.5], [0.0]])
    assert np.allclose(SIM.garch_scales(z, 0.0, 0.0), 1.0)
    s = SIM.garch_scales(z, 0.1, 0.85)
    h1 = 0.05 + 0.1 * 1.0 * 1.0**2 + 0.85 * 1.0
    h2 = 0.05 + 0.1 * h1 * 2.0**2 + 0.85 * h1
    assert abs(s[1, 0] - np.sqrt(h1)) < 1e-12 and abs(s[2, 0] - np.sqrt(h2)) < 1e-12


def test_per_asset_scale_keeps_the_covariance_and_changes_the_shape_of_months():
    normal = SIM.build_market(10)
    common = SIM.build_market(10, dof=5)
    per_asset = SIM.build_market(10, dof=5, common_scale=False)
    # same true moments; the sample covariance stays close to Sigma because every scale has mean square one
    np.testing.assert_array_equal(per_asset.Sigma, normal.Sigma)
    S = np.cov(per_asset.returns, rowvar=False)
    assert np.allclose(np.diag(S), np.diag(per_asset.Sigma), rtol=0.06)
    assert np.allclose(S[0, 1:], per_asset.Sigma[0, 1:], rtol=0.08)      # the factor row: covariances with every asset
    assert np.allclose(per_asset.returns.mean(axis=0), per_asset.mu, atol=0.002)
    # the scales differ across assets within a month under per-asset scaling and are equal under the common scale
    assert np.allclose(common.scales[:, 0], common.scales[:, 5])
    assert not np.allclose(per_asset.scales[:, 0], per_asset.scales[:, 5])
    assert per_asset.scales.shape == (C.SIM_T, 10)
    # the factor's shocks keep their sign, paired with the normal market (an asset's return adds two shocks with
    # different scales, so its sign can flip; the factor asset has only one)
    assert np.all(np.sign(per_asset.returns[:, 0] - per_asset.mu[0]) == np.sign(normal.returns[:, 0] - normal.mu[0]))
    # fatter tails than the normal market in the assets' own returns too
    assert SIM.excess_kurtosis(per_asset.returns[:, 3]) > SIM.excess_kurtosis(normal.returns[:, 3]) + 0.3
