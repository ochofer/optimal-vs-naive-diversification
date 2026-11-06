"""Tests of the rolling evaluation on a made-up market with a known covariance and a benchmark that drifts; from
18 October 2026 also of the two descriptive figures, the block-bootstrap band and the factor path of module A."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from bp import constants as C  # noqa: E402
from bp import evaluation as E  # noqa: E402
from bp import optimiser as O  # noqa: E402


def _world(T=24, N=6, seed=2):
    rng = np.random.default_rng(seed)
    months = pd.period_range("2010-01", periods=T, freq="M")
    beta = rng.uniform(0.6, 1.4, N)
    own = rng.uniform(0.02, 0.05, N) ** 2
    Sigma = 0.04 ** 2 * np.outer(beta, beta) + np.diag(own)
    returns = pd.DataFrame(rng.multivariate_normal(np.zeros(N), Sigma, size=T) + 0.005, index=months)
    # cap weights that drift with the returns, as an index's do
    w = rng.uniform(0.5, 2.0, N); w[0] = 0.25; w = w / w.sum()     # the first asset, the one tilted in the tests, is small enough for the bound to absorb half of it
    rows = [w]
    for t in range(1, T):
        rows.append(O.drifted_weights(rows[-1], returns.iloc[t - 1].to_numpy()))
    weights = pd.DataFrame(rows, index=months)
    return months, Sigma, weights, returns


def test_the_benchmark_path_has_zero_active_return_and_the_index_turnover():
    months, Sigma, weights, returns = _world()
    Sigmas = {m: Sigma for m in months}
    tilt = np.zeros(6, bool)
    path = E.run_path(months, Sigmas, weights, returns, ("long_only",), tilt, None)
    assert len(path) == len(months)
    assert np.abs(path["active_return"]).max() < 1e-10
    assert path["forecast_te"].max() < 1e-6
    # the benchmark here drifts exactly with the returns, so following it needs no trade after the first month
    assert path["turnover"].iloc[1:].max() < 1e-9 and path["benchmark_turnover"].iloc[1:].max() < 1e-9
    assert np.isnan(E.bias_statistic(path["active_return"].to_numpy(), path["forecast_te"].to_numpy()))


def test_a_tilted_path_records_the_active_return_and_the_relaxed_first_month():
    months, Sigma, weights, returns = _world()
    Sigmas = {m: Sigma for m in months}
    tilt = np.zeros(6, bool); tilt[0] = True
    cons = ("long_only", "active_weight_bound", "turnover_cap", "tilt")
    path = E.run_path(months, Sigmas, weights, returns, cons, tilt, None, keep_weights=True)
    # the first month relaxes the cap (the tilt alone demands more than 2%), later months stay inside it
    assert bool(path["relaxed"].iloc[0]) and path["turnover"].iloc[0] > 0.02
    assert (path["turnover"].iloc[1:] <= path["cap_used"].iloc[1:] + 1e-6).all()
    # the recorded active return is w' r - b' r for the month's own weights
    m = months[5]
    w = path.loc[m, "weights"]
    assert abs(path.loc[m, "active_return"] - (w @ returns.loc[m].to_numpy() - weights.loc[m].to_numpy() @ returns.loc[m].to_numpy())) < 1e-12
    assert (w[0] <= 0.5 * weights.loc[m, 0] + 1e-6)
    s = E.summarise(path)
    assert abs(s["realised TE"] - np.std(path["active_return"], ddof=1) * np.sqrt(12)) < 1e-12
    assert s["relaxed months"] >= 1 and 0 < s["forecast TE (mean)"]
    assert abs(s["cost at 50 bp"] - 12 * path["turnover"].mean() * 0.005) < 1e-12


def test_bias_statistic_and_variance_ratio_scale():
    rng = np.random.default_rng(4)
    f = np.full(5000, 0.02 * np.sqrt(12))                      # forecast tracking error 2% a month, stated per year
    active = rng.standard_normal(5000) * 0.02
    assert abs(E.bias_statistic(active, f) - 1.0) < 0.05
    assert abs(E.bias_statistic(active, f, scale=np.full(5000, 4.0)) - 0.5) < 0.03   # a variance scale of 4 doubles the forecast sd
    assert abs(E.realised_tracking_error(active) - 0.02 * np.sqrt(12)) < 0.002


def test_by_decade_labels_the_partial_decades():
    months = pd.period_range("1985-01", "2021-12", freq="M")
    path = pd.DataFrame({"active_return": np.sin(np.arange(len(months)))}, index=months)
    d = E.by_decade(path, "1985 to 1989", "2020 to 2021")
    assert list(d.index) == ["1985 to 1989", "1990s", "2000s", "2010s", "2020 to 2021"]


def test_calibrated_forecast_uses_only_the_past_and_corrects_a_constant_bias():
    months = pd.period_range("2000-01", periods=200, freq="M")
    rng = np.random.default_rng(9)
    forecast = pd.Series(0.01 * np.sqrt(12), index=months)                 # 1% a month, stated per year
    active = pd.Series(rng.standard_normal(200) * 0.015, index=months)      # realised 1.5%: the forecast is 50% too low
    path = pd.DataFrame({"forecast_te": forecast, "active_return": active})
    cal = E.calibrated_forecast(path, window=60, minimum=24)
    assert (cal.iloc[:24] == forecast.iloc[:24]).all()                      # nothing to calibrate on yet
    assert 1.3 < (cal.iloc[100:] / forecast.iloc[100:]).mean() < 1.7        # the ratio found is about 1.5
    # changing a later month's active return does not change an earlier month's calibrated forecast
    path2 = path.copy(); path2.loc[months[150], "active_return"] = 0.5
    cal2 = E.calibrated_forecast(path2, window=60, minimum=24)
    assert (cal2.iloc[:151] == cal.iloc[:151]).all() and (cal2.iloc[151:] > cal.iloc[151:]).all()
    b = E.bias_statistic(active.to_numpy()[100:], cal.to_numpy()[100:])
    assert 0.85 < b < 1.15


# ---------------------------------------------------------------------------
# Added 18 October 2026: the descriptive figures, the band and the factor path
# ---------------------------------------------------------------------------

def test_worst_cumulative_fall_on_a_series_whose_answer_is_known_by_hand():
    months = pd.period_range("2000-01", periods=8, freq="M")
    a = pd.Series([0.01, -0.02, -0.01, 0.03, 0.02, -0.05, 0.01, 0.0], index=months)
    # cumulative: .01 -.01 -.02 .01 .03 -.02 -.01 -.01; the high of .03 in May, the low of -.02 in June: a fall of .05 over one month
    d = E.worst_cumulative_fall(a)
    assert abs(d["fall"] - 0.05) < 1e-12 and d["peak"] == months[4] and d["trough"] == months[5] and d["months"] == 1
    # a fall from the start, before any high: measured from zero
    d0 = E.worst_cumulative_fall(pd.Series([-0.01, -0.02, 0.05], index=months[:3]))
    assert abs(d0["fall"] - 0.03) < 1e-12 and d0["peak"] == "start" and d0["trough"] == months[1]
    # a series that never falls
    assert E.worst_cumulative_fall(pd.Series([0.01, 0.02, 0.0], index=months[:3]))["fall"] == 0.0
    assert abs(E.share_positive(a) - 0.5) < 1e-12 and E.share_positive(np.array([-1.0, 0.0, 2.0])) == 1 / 3


def test_block_bootstrap_band_is_deterministic_covers_a_calibrated_forecast_and_keeps_the_blocks_together():
    rng = np.random.default_rng(11)
    f = np.full(566, 0.02 * np.sqrt(12))                      # a forecast of 2% a month, stated per year
    active = rng.standard_normal(566) * 0.02                  # realised 2%: the forecast is calibrated, the statistic about 1
    lo, hi = E.block_bootstrap_band(active, f, block=12, draws=500, seed=3)
    point = E.bias_statistic(active, f)
    assert lo < point < hi and lo < 1.0 < hi and 0.02 < hi - lo < 0.2
    assert E.block_bootstrap_band(active, f, block=12, draws=500, seed=3) == (lo, hi)               # the same seed, the same band
    assert E.block_bootstrap_band(active, f, block=12, draws=500, seed=4) != (lo, hi)
    # a longer series gives a narrower band
    long = rng.standard_normal(5000) * 0.02
    lo2, hi2 = E.block_bootstrap_band(long, np.full(5000, 0.02 * np.sqrt(12)), block=12, draws=500, seed=3)
    assert hi2 - lo2 < hi - lo
    # blocks keep the months together: with the forecast equal to the realised size month by month, every resampled
    # ratio is plus or minus one and the statistic is the same in every draw
    exact = np.abs(active) * np.sqrt(12)
    lo3, hi3 = E.block_bootstrap_band(active, exact, block=12, draws=200, seed=3)
    assert abs(hi3 - lo3) < 0.05
    assert np.isnan(E.block_bootstrap_band(active, np.zeros(566))[0])                                # no forecast, no band
    with pytest.raises(ValueError):
        E.block_bootstrap_band(active[:1], f[:1])


def _factor_world(T=10, N=30, seed=5):
    months, Sigma, weights, returns = _world(T=T, N=N, seed=seed)
    rng = np.random.default_rng(seed + 100)
    base = rng.normal(0.0, 0.3, (N, len(C.ATTRIBUTION_FACTORS)))
    base[:, 0] = 1.0
    betas = {m: base + 0.01 * i * np.sign(base) for i, m in enumerate(months)}       # betas that move a little each month
    return months, Sigma, weights, returns, betas


def test_the_factor_path_records_what_the_objective_bought_and_the_gap():
    months, Sigma, weights, returns, betas = _factor_world()
    N = Sigma.shape[0]
    s = np.array([C.FO_TARGET_SIGN[f] for f in C.ATTRIBUTION_FACTORS])
    tilt = np.zeros(N, bool); tilt[0] = True
    excl = np.zeros(N, bool); excl[1] = True
    cons = C.CONSTRAINT_SETS["C3"]
    Sigmas = {m: Sigma for m in months}
    path = E.run_factor_path(months, Sigmas, betas, weights, returns, cons, s, 0.0075, tilt, excl, keep_weights=True)
    assert len(path) == len(months) and path["budget_met"].all()
    assert (path["forecast_te"] <= 0.0075 * (1 + 1e-6) + 1e-5).all()
    m = months[3]
    w, b, B = path.loc[m, "weights"], weights.loc[m].to_numpy(), betas[m]
    expo = B.T @ (w - b)
    assert np.allclose([path.loc[m, f"exposure {f}"] for f in C.ATTRIBUTION_FACTORS], expo)
    assert abs(path.loc[m, "objective"] - s @ expo) < 1e-12
    assert abs(path.loc[m, "active_return"] - (w @ returns.loc[m].to_numpy() - b @ returns.loc[m].to_numpy())) < 1e-12
    gap = s @ (betas[m] - betas[months[4]]).T @ (w - b)
    assert abs(path.loc[m, "gap"] - gap) < 1e-12 and np.isnan(path["gap"].iloc[-1])
    assert w[1] <= 1e-6 and w[0] <= 0.5 * b[0] + 1e-6
    out = E.summarise_factor(path, 0.0075)
    assert abs(out["realised over budget"] - out["realised TE"] / 0.0075) < 1e-12
    assert out["budget not met months"] == 0 and 0 <= out["budget binds months"] <= len(months)
    assert abs(out["mean objective"] - sum(out[f"mean exposure {f}"] for f in C.FO_TARGET_FACTORS)) < 1e-9
    assert abs(out["exposure per bp of realised TE"] - out["mean objective"] / (1e4 * out["realised TE"])) < 1e-12


def test_a_budget_no_month_can_meet_gives_the_minimiser_path_of_version_1():
    months, Sigma, weights, returns, betas = _factor_world()
    N = Sigma.shape[0]
    s = np.array([C.FO_TARGET_SIGN[f] for f in C.ATTRIBUTION_FACTORS])
    tilt = np.zeros(N, bool); tilt[0] = True
    excl = np.zeros(N, bool); excl[1] = True
    cons = C.CONSTRAINT_SETS["C3"]
    Sigmas = {m: Sigma for m in months}
    tiny = E.run_factor_path(months, Sigmas, betas, weights, returns, cons, s, 1e-6, tilt, excl)
    base = E.run_path(months, Sigmas, weights, returns, cons, tilt, excl)
    assert not tiny["budget_met"].any() and not tiny["budget_binds"].any()
    assert np.allclose(tiny["active_return"].to_numpy(), base["active_return"].to_numpy(), atol=1e-7)
    assert np.allclose(tiny["forecast_te"].to_numpy(), base["forecast_te"].to_numpy(), atol=1e-7)

