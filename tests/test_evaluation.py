"""Tests of the rolling evaluation on a made-up market with a known covariance and a benchmark that drifts."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

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
