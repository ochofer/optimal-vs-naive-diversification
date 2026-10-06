"""Principal components on a made-up one-factor market, no network."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import pca as P  # noqa: E402
from bp import simulate as SIM  # noqa: E402


def _panel(N=10, T=6000, seed=7):
    mkt = SIM.build_market(N, T, seed)
    idx = pd.period_range("1900-01", periods=T, freq="M")
    cols = [f"A{k}" for k in range(N)]
    return pd.DataFrame(mkt.returns, index=idx, columns=cols), mkt


def test_eigenvalues_sum_to_the_total_variance_and_shares_to_one():
    X, _ = _panel()
    p = P.fit(X)
    assert np.isclose(p.eigenvalues.sum(), np.trace(P.covariance(X)))
    assert np.isclose(p.shares.sum(), 1.0)
    assert np.all(np.diff(p.eigenvalues) <= 1e-12)        # descending
    assert p.months == len(X) and p.assets == list(X.columns)


def test_first_component_recovers_the_factor_in_a_one_factor_market():
    X, mkt = _panel()
    p = P.fit(X)
    # the estimated first component matches the first eigenvector of the true covariance
    true_vals, true_vecs = np.linalg.eigh(mkt.Sigma)
    true_first = true_vecs[:, np.argmax(true_vals)]
    assert P.loading_similarity(p.loadings[:, 0], true_first) > 0.99
    # and that eigenvector leans the same way as the betas (the factor exposures), though it is not equal to them,
    # because assets with more of their own noise get a larger loading than their beta alone would give
    assert P.loading_similarity(true_first, mkt.betas) > 0.9
    # its score (monthly return) moves with the factor (asset 0 is the factor itself); with ten assets the component also
    # carries some of the assets' own noise, so the correlation is high and below one
    s = P.scores(X, p, 1)["PC1"]
    assert 0.9 < np.corrcoef(s, X["A0"])[0, 1] < 1.0
    # the first component explains most of the variance; the second far less
    assert p.shares[0] > 0.5 and p.shares[1] < 0.2


def test_sign_rule_makes_the_loading_on_the_reference_positive():
    X, _ = _panel()
    ref = np.ones(X.shape[1]) / X.shape[1]
    p = P.fit(X, ref)
    assert all(p.loadings[:, k] @ ref >= 0 for k in range(X.shape[1]))
    flipped = P.fit(X, -ref)
    assert np.allclose(np.abs(flipped.loadings), np.abs(p.loadings))


def test_explained_in_window_is_largest_for_the_window_own_components():
    X, _ = _panel()
    first, second = X.iloc[:3000], X.iloc[3000:]
    own = P.fit(second)
    other = P.fit(first)
    share_own = P.explained_in_window(second, own.loadings, 3)
    share_other = P.explained_in_window(second, other.loadings, 3)
    assert np.isclose(share_own, own.shares[:3].sum())
    assert share_other <= share_own + 1e-12
    assert share_other > 0.9 * share_own        # the same market, so the structure is nearly the same


def test_parallel_analysis_finds_one_component_in_a_one_factor_market_and_none_in_noise():
    X, _ = _panel(N=10, T=2000)
    pa = P.parallel_analysis(X, draws=50, seed=1)
    assert pa.attrs["n_above_noise"] == 1
    rng = np.random.default_rng(2)
    noise = pd.DataFrame(rng.standard_normal((2000, 10)) * 0.05, index=X.index, columns=X.columns)
    pn = P.parallel_analysis(noise, draws=50, seed=1)
    assert pn.attrs["n_above_noise"] <= 1          # at the 95th percentile a false positive in the first slot happens one time in twenty


def test_rolling_first_component_covers_every_full_window():
    X, _ = _panel(N=5, T=400)
    bench = X.mean(axis=1)
    out = P.rolling_first_component(X, bench, window=120)
    assert len(out) == 400 - 120 + 1
    assert out.index[0] == X.index[119] and out.index[-1] == X.index[-1]
    assert (out["pc1_share"] > 0.5).all() and (out["pc1_corr_benchmark"] > 0.95).all()
