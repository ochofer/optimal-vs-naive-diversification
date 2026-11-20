"""The daily construction of a path's returns: on a made-up month the compounded daily return of a drifting
portfolio equals the weights times the compounded industry returns, the drifted weights sum to one every
day, the series re-anchors at each month's weights, the reconciliation of gate D1 reads as expected, the
GARCH pair of the size check has the variance and correlation it is given, the first k pairs of a longer run are
the run of k pairs, the reading of a RiskMetrics row comes by code for every reading, and the constants of section 9."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import constants as C  # noqa: E402
from bp import daily as D  # noqa: E402
from bp import paired as P  # noqa: E402


def _month(rng, days=21, n=5):
    return rng.normal(0.0, 0.01, size=(days, n))


def test_the_compounded_daily_return_equals_the_weights_times_the_compounded_industry_returns():
    rng = np.random.default_rng(1)
    r = _month(rng)
    w0 = np.array([0.4, 0.3, 0.2, 0.05, 0.05])
    port, starts = D.drift_daily(w0, r)
    compounded = float(np.prod(1.0 + port) - 1.0)
    expected = float(w0 @ (np.prod(1.0 + r, axis=0) - 1.0))
    assert compounded == pytest.approx(expected, abs=1e-14)
    assert np.allclose(starts.sum(axis=1), 1.0, atol=1e-12) and np.array_equal(starts[0], w0)
    # the second day's weights are the first day's grown by the first day's returns
    grown = w0 * (1.0 + r[0])
    assert np.allclose(starts[1], grown / grown.sum())
    # a flat month leaves the weights and gives a zero return
    port0, starts0 = D.drift_daily(w0, np.zeros((21, 5)))
    assert np.all(port0 == 0) and np.all(starts0 == w0)


def test_the_series_re_anchors_at_each_months_weights_and_rejects_a_missing_day():
    rng = np.random.default_rng(2)
    days = pd.period_range("2001-01-01", "2001-02-28", freq="D")
    days = days[days.dayofweek < 5]
    returns_d = pd.DataFrame(rng.normal(0.0, 0.01, size=(len(days), 3)), index=days, columns=["a", "b", "c"])
    months = pd.period_range("2001-01", "2001-02", freq="M")
    weights = pd.DataFrame([[0.5, 0.3, 0.2], [0.2, 0.3, 0.5]], index=months, columns=["a", "b", "c"])
    series = D.daily_returns_of_path(weights, returns_d)
    assert series.index.equals(returns_d.index)
    by_month = D.compounded_by_month(series)
    for month in months:
        r = returns_d[returns_d.index.asfreq("M") == month].to_numpy()
        assert by_month[month] == pytest.approx(float(weights.loc[month].to_numpy() @ (np.prod(1.0 + r, axis=0) - 1.0)), abs=1e-14)
    with_gap = returns_d.copy()
    with_gap.iloc[3, 1] = np.nan
    with pytest.raises(ValueError):
        D.daily_returns_of_path(weights, with_gap)
    with pytest.raises(ValueError):
        D.daily_returns_of_path(weights[["b", "a", "c"]], returns_d)


def test_the_reconciliation_reads_a_perfect_match_and_a_known_gap():
    rng = np.random.default_rng(3)
    days = pd.period_range("2001-01-01", "2001-12-31", freq="D")
    days = days[days.dayofweek < 5]
    returns_d = pd.DataFrame(rng.normal(0.0, 0.01, size=(len(days), 2)), index=days, columns=["a", "b"])
    months = pd.period_range("2001-01", "2001-12", freq="M")
    port_w = pd.DataFrame(np.tile([0.6, 0.4], (12, 1)), index=months, columns=["a", "b"])
    bench_w = pd.DataFrame(np.tile([0.5, 0.5], (12, 1)), index=months, columns=["a", "b"])
    port = D.daily_returns_of_path(port_w, returns_d)
    bench = D.daily_returns_of_path(bench_w, returns_d)
    committed = D.compounded_by_month(port) - D.compounded_by_month(bench)
    out = D.reconcile(port, bench, committed)
    assert out["months"] == 12 and out["correlation"] == pytest.approx(1.0) and abs(out["te_gap"]) < 1e-15 and out["largest_monthly_gap"] < 1e-15
    shifted = committed + 0.0001
    out2 = D.reconcile(port, bench, shifted)
    assert out2["largest_monthly_gap"] == pytest.approx(0.0001) and out2["correlation"] == pytest.approx(1.0) and abs(out2["te_gap"]) < 1e-12
    # a committed series equal to the compounded one times 1.1: the correlation stays 1, the compounded
    # tracking error is a tenth below the committed one, and the largest gap is a tenth of the largest
    # compounded month, in that month (added 20 November 2026)
    scaled = committed * 1.1
    out3 = D.reconcile(port, bench, scaled)
    assert out3["correlation"] == pytest.approx(1.0)
    assert out3["te_gap"] == pytest.approx(-0.1 * out3["te_compounded"]) and out3["te_committed"] == pytest.approx(1.1 * out3["te_compounded"])
    assert out3["largest_monthly_gap"] == pytest.approx(0.1 * committed.abs().max())
    assert out3["month_of_largest_gap"] == str(committed.abs().idxmax())
    # a portfolio's own return against its monthly return, family C's form: no benchmark
    own = D.reconcile(port, None, D.compounded_by_month(port) * 1.1)
    assert own["correlation"] == pytest.approx(1.0) and own["te_gap"] == pytest.approx(-0.1 * own["te_compounded"])


def test_the_garch_pair_has_the_variance_and_correlation_it_is_given():
    rng = np.random.default_rng(4)
    sd = C.DAILY_SIZE_SD_ANNUAL / np.sqrt(C.DAILY_PERIODS)
    r1, r2 = P.simulate_garch_pair(200_000, sd, C.DAILY_SIZE_CORRELATION, C.DAILY_SIZE_T_DOF, C.DAILY_SIZE_GARCH, rng)
    assert np.std(r1) * np.sqrt(C.DAILY_PERIODS) == pytest.approx(C.DAILY_SIZE_SD_ANNUAL, rel=0.05)
    assert np.std(r2) * np.sqrt(C.DAILY_PERIODS) == pytest.approx(C.DAILY_SIZE_SD_ANNUAL, rel=0.05)
    assert np.corrcoef(r1, r2)[0, 1] == pytest.approx(C.DAILY_SIZE_CORRELATION, abs=0.003)
    # the variance clusters: squared returns are positively autocorrelated at one day
    sq = r1 ** 2
    assert np.corrcoef(sq[:-1], sq[1:])[0, 1] > 0.05
    omega, alpha, beta = C.DAILY_SIZE_GARCH
    assert omega / (1 - alpha - beta) == pytest.approx(1.0)


def test_the_daily_size_check_runs_and_reports_its_counts():
    out = P.size_check_daily(pairs=4, days=600, sd=0.0005, rho=0.99, dof=5, garch=C.DAILY_SIZE_GARCH, seed=11,
                             block=252, draws=99, periods=252, chunk=40)
    assert out["pairs"] == 4 and len(out["p_values"]) == 4 and len(out["standard_errors"]) == 4
    assert len(out["critical_values"]) == 4 and (out["critical_values"] > 0).all()   # the per-pair critical values, for the size table's median (19 November 2026)
    assert out["rejected"] == int((out["p_values"] < 0.05).sum())
    assert out["rejected_interval"] == int(out["excludes_interval"].sum()) and len(out["excludes_interval"]) == out["pairs"]   # per-pair flags, for the first-pairs row of P3


def test_the_first_k_pairs_of_a_longer_run_are_the_run_of_k_pairs_and_workers_change_nothing():
    # the property the size table's first row rests on: the pairs are drawn in sequence from one generator
    # and each bootstrap seed is spawned in sequence (added 20 November 2026)
    kw = dict(days=400, sd=0.0005, rho=0.99, dof=5, garch=C.DAILY_SIZE_GARCH, seed=11, block=252, draws=99, periods=252, chunk=40)
    short = P.size_check_daily(pairs=3, **kw)
    longer = P.size_check_daily(pairs=7, **kw)
    for key in ("p_values", "excludes_interval", "differences", "standard_errors", "critical_values"):
        assert np.array_equal(short[key], longer[key][:3]), key
    parallel = P.size_check_daily(pairs=7, workers=2, batch=3, **kw)
    for key in ("p_values", "excludes_interval", "differences", "standard_errors", "critical_values"):
        assert np.array_equal(parallel[key], longer[key]), key
    assert parallel["rejected"] == longer["rejected"] and parallel["rejected_interval"] == longer["rejected_interval"]


def test_read_interval_gives_every_reading_on_made_up_intervals():
    # the setting of 20 November 2026: what each reading is read against, by code and never by hand
    kw = dict(readings=C.DAILY_READINGS, readings_unconstrained=C.DAILY_READINGS_UNCONSTRAINED, window_clause=C.DAILY_WINDOW_CLAUSE,
              paper_window_years=C.DAILY_PAPER_WINDOW_YEARS)
    cap = C.PAIRED_PAPER_FIGURES[C.DAILY_READING_VERSION]["with the cap"]           # 13.00 against 13.36: a published gain of 2.69 per cent
    assert cap == (13.00, 13.36)
    ref = 84.65
    gain = (13.36 - 13.00) / 13.36 * ref                                              # 2.28 basis points on this level
    below = D.read_interval(-3.0, -5.0, -1.0, ref, cap, 5, **kw)
    assert below["key"] == "below" and below["sentence"] == C.DAILY_READINGS["below"] and below["published_gain_here"] == pytest.approx(gain)
    excludes = D.read_interval(-0.4, -1.5, 0.7, ref, cap, 5, **kw)                   # includes zero, lower end above -2.28
    assert excludes["key"] == "excludes_gain" and excludes["sentence"] == C.DAILY_READINGS["excludes_gain"]
    includes = D.read_interval(-0.4, -2.3, 1.5, ref, cap, 5, **kw)                   # includes zero and a gain of the published size
    assert includes["key"] == "includes_gain" and includes["sentence"] == C.DAILY_READINGS["includes_gain"]
    above = D.read_interval(2.0, 0.5, 3.5, ref, cap, 5, **kw)
    assert above["key"] == "above" and above["sentence"] == C.DAILY_READINGS["above"]
    # a row whose sample covariance is on three years names the window as a difference from the paper
    three = D.read_interval(-0.4, -2.3, 1.5, ref, cap, 3, **kw)
    assert three["key"] == "includes_gain" and three["sentence"] == C.DAILY_READINGS["includes_gain"] + "; " + C.DAILY_WINDOW_CLAUSE
    # the unconstrained pair has RiskMetrics above the sample covariance: no published gain, three readings
    unc = C.PAIRED_PAPER_FIGURES[C.DAILY_READING_VERSION]["unconstrained"]
    assert unc == (11.36, 10.91)
    u_below = D.read_interval(-0.3, -0.8, -0.1, 11.9, unc, 5, **kw)
    assert u_below["key"] == "below" and u_below["sentence"] == C.DAILY_READINGS_UNCONSTRAINED["below"] and u_below["published_share"] is None
    u_zero = D.read_interval(-0.3, -0.8, 0.3, 11.9, unc, 5, **kw)
    assert u_zero["key"] == "includes_zero" and u_zero["sentence"] == C.DAILY_READINGS_UNCONSTRAINED["includes_zero"]
    u_above = D.read_interval(0.3, 0.1, 0.5, 11.9, unc, 3, **kw)
    assert u_above["key"] == "above" and u_above["sentence"] == C.DAILY_READINGS["above"] + "; " + C.DAILY_WINDOW_CLAUSE
    # the long-only pair: 11.31 against 12.24, 7.6 per cent of the level
    lo = C.PAIRED_PAPER_FIGURES[C.DAILY_READING_VERSION]["long-only"]
    assert D.read_interval(-0.1, -0.5, 0.3, 12.06, lo, 5, **kw)["published_share"] == pytest.approx((12.24 - 11.31) / 12.24)


def test_the_pilot_of_18_november_printed_the_two_shares_the_text_quotes():
    # checks/daily_pilot_2026-11-18.py, written and run on 18 November 2026 before the block was fixed, entered the
    # repository on 20 November with its two printed lines; the text quotes 2.8 and 3.7 per cent
    root = pathlib.Path(__file__).resolve().parents[1]
    script = root / "checks" / "daily_pilot_2026-11-18.py"
    lines = (root / "checks" / "daily_pilot_2026-11-18.txt").read_text().splitlines()
    assert script.exists() and len(script.read_text().splitlines()) == 48
    rows = {int(l.split()[1]): l for l in lines if l.startswith("block ")}
    assert set(rows) == {252, 63}
    assert "rejected 0.028 " in rows[252] and "rejected 0.037 " in rows[63]
    assert "pairs 400 draws 999" in rows[252] and "pairs 400 draws 999" in rows[63]
    assert "mean se 0.155 bp | sd of differences 0.153 bp" in rows[252] and "mean se 0.155 bp | sd of differences 0.153 bp" in rows[63]
    # on 400 pairs a share of 0.028 has a standard error of 0.008, so the two shares are not told apart
    assert np.sqrt(0.028 * 0.972 / 400) == pytest.approx(0.0082, abs=0.0002) and abs(0.037 - 0.028) < 2 * 0.0082


def test_the_settings_of_20_november():
    assert C.DAILY_SETTINGS_DATE == "2026-11-20" and C.DAILY_READING_VERSION == "published version, Table 3 Panel B"
    assert C.DAILY_PAPER_WINDOW_YEARS == 5 and len(C.DAILY_READING_ROWS) == 7
    assert [r[4] for r in C.DAILY_READING_ROWS] == ["with the cap", "with the cap", "with the cap", "unconstrained", "long-only", "unconstrained", "long-only"]
    assert [r[5] for r in C.DAILY_READING_ROWS] == [3, 5, 5, 5, 5, 3, 3]
    assert set(C.DAILY_READINGS_UNCONSTRAINED) == {"below", "includes_zero", "above"} and C.DAILY_READINGS_UNCONSTRAINED["above"] == C.DAILY_READINGS["above"]
    assert C.DAILY_SIZE_FURTHER_CORRELATIONS == (0.93, 0.81) and C.DAILY_C_RECONCILIATION_DATE == "2026-11-20"


def test_the_constants_of_the_daily_measurement():
    assert C.DAILY_TEST_DATE == "2026-11-18" and C.DAILY_PERIODS == 252 and C.DAILY_BLOCK == 252
    assert C.DAILY_PATH_SETS == ("C3", "C3 tilt only") and len(C.DAILY_C_VARIANTS) == 3 and C.DAILY_C_SIDES == ("unconstrained", "long-only")
    assert C.DAILY_D1_CORRELATION_MIN == 0.995 and C.DAILY_D1_TE_GAP_MAX == 0.0001
    assert C.DAILY_SIZE_PAIRS == 3000 and C.DAILY_SIZE_PAIRS_FIRST == 500 and C.DAILY_SIZE_PAIRS_RAISED == "2026-11-19"   # raised 19 November 2026, before the larger run
    assert C.DAILY_SIZE_SEED == 20261119 and C.DAILY_SIZE_GARCH == (0.02, 0.06, 0.92)
    assert C.DAILY_SIZE_RATE_MAX == 0.065 and C.DAILY_SIZE_RATE_LOW == 0.035 and C.DAILY_ED2_SE_RATIO_MAX == 0.5
    assert set(C.DAILY_READINGS) == {"below", "excludes_gain", "includes_gain", "above"}
    for version, figures in C.PAIRED_PAPER_FIGURES.items():
        assert set(figures) == {"unconstrained", "long-only", "with the cap"}
        assert figures["with the cap"] == C.PAIRED_PAPER_GAIN_WITH_CAP[f"{version}, with the cap"]
    assert C.PAIRED_PAPER_FIGURES["published version, Table 3 Panel B"]["unconstrained"] == (11.36, 10.91)


def test_window_weight_statistics_flat_and_exponential():
    flat = D.window_weight_statistics(756)
    assert flat["mean age"] == pytest.approx(378.5) and flat["effective number"] == pytest.approx(756.0) and flat["share in recent days"] == pytest.approx(1.0)
    flat5 = D.window_weight_statistics(1260)
    assert flat5["mean age"] == pytest.approx(630.5) and flat5["effective number"] == pytest.approx(1260.0) and flat5["share in recent days"] == pytest.approx(756 / 1260)
    rm = D.window_weight_statistics(1260, halflife=252)
    assert rm["mean age"] < flat["mean age"] < flat5["mean age"]
    assert rm["effective number"] < flat["effective number"] and 0.85 < rm["share in recent days"] < 0.95
    # the weights are those of covariance.ewma_cov: the weight halves every half-life
    w = 0.5 ** (np.arange(1260) / 252.0)
    w = w / w.sum()
    assert rm["effective number"] == pytest.approx(1.0 / (w ** 2).sum())
    with pytest.raises(ValueError):
        D.window_weight_statistics(0)


def test_family_d_constants():
    assert C.DAILY_D_DATE == "2026-11-18" and C.DAILY_D_VARIANT == ("sample", "daily_5y") and C.DAILY_D_SET == "C3"
    assert len(C.DAILY_COMPARISONS_D) == 2 and C.DAILY_COMPARISONS_D[0] == (("RiskMetrics", "daily 5y"), ("sample", "daily 5y"))
    assert C.DAILY_COMPARISONS_D[1] == (("sample", "daily 5y"), ("sample", "daily 3y"))
    assert C.DAILY_D_FREQUENCIES == ("monthly", "daily") and C.DAILY_RECENT_DAYS == 756
    assert [w[0] for w in C.DAILY_WINDOWS_DESCRIBED] == ["RiskMetrics, daily 5y", "flat, daily 3y", "flat, daily 5y"]
    assert C.DAILY_WINDOWS_DESCRIBED[0][2] == C.EXT_COV_EWMA_HALFLIFE_DAYS and C.DAILY_WINDOWS_DESCRIBED[1][2] is None
