"""Ledoit and Wolf's variance test: the same seed gives the same answer, the differences agree with the
tables' conventions, the standard errors agree with the textbook formulas on simulated returns, the test
rejects a true null at about its nominal rate, a large true difference is found, Holm's adjustment by hand,
and the module loads on its own."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import constants as C  # noqa: E402
from bp import paired as P  # noqa: E402


def _pair(months, seed, rho=0.99, scale2=1.0):
    rng = np.random.default_rng(seed)
    r1, r2 = P.simulate_null_pair(months, 0.0025, rho, 5, rng)
    return r1, r2 * scale2


def test_the_module_loads_without_the_package():
    path = ROOT / "src" / "bp" / "paired.py"
    text = path.read_text()
    assert "from ." not in text and "import bp" not in text and "from bp" not in text
    spec = importlib.util.spec_from_file_location("lw_variance_alone", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r1, r2 = _pair(240, 1)
    assert mod.test(r1, r2, draws=199, seed=5) == P.test(r1, r2, draws=199, seed=5)


def test_same_seed_same_result_and_another_seed_another_interval():
    r1, r2 = _pair(480, 2)
    a, b = P.test(r1, r2, draws=499, seed=9), P.test(r1, r2, draws=499, seed=9)
    c = P.test(r1, r2, draws=499, seed=10)
    assert a == b
    assert c["difference"] == a["difference"] and c["se"] == a["se"] and c["critical"] != a["critical"]


def test_the_differences_follow_the_tables_conventions():
    r1, r2 = _pair(300, 3, scale2=1.1)
    te = lambda r: float(np.std(r, ddof=1) * np.sqrt(12))   # the tables' realised tracking error  # noqa: E731
    assert P.sd_difference(r1, r2) == pytest.approx(te(r1) - te(r2))
    assert P.log_variance_difference(r1, r2) == pytest.approx(np.log(np.var(r1) / np.var(r2)))
    out = P.test(r1, r2, draws=199, seed=1)
    assert out["sd1"] == pytest.approx(te(r1)) and out["sd2"] == pytest.approx(te(r2))
    assert out["difference"] == pytest.approx(te(r1) - te(r2)) and out["correlation"] == pytest.approx(np.corrcoef(r1, r2)[0, 1])
    assert out["lower"] < out["difference"] < out["upper"] and out["upper"] - out["difference"] == pytest.approx(out["half_width"])


def test_standard_errors_agree_with_the_normal_formulas_on_simulated_returns():
    rng = np.random.default_rng(7)
    t, rho, s = 40000, 0.6, 0.05
    x = rng.standard_normal((2, t))
    a, b = s * x[0], s * (rho * x[0] + np.sqrt(1 - rho ** 2) * x[1])
    se = P.standard_errors(a, b)
    # independent normal months: var(log s1^2 - log s2^2) = 4 (1 - rho^2) / T
    assert se["se_log"] == pytest.approx(2 * np.sqrt(1 - rho ** 2) / np.sqrt(t), rel=0.05)
    # var(s1 - s2) = (sigma_1^2 + sigma_2^2 - 2 rho^2 sigma_1 sigma_2) / (2 T), times 12 for the annualisation
    sd1, sd2 = a.std(), b.std()
    var_sd = 12 * (sd1 ** 2 + sd2 ** 2 - 2 * rho ** 2 * sd1 * sd2) / (2 * t)
    assert se["se_sd"] == pytest.approx(np.sqrt(var_sd), rel=0.05)


def test_parzen_kernel_values():
    assert P._parzen(0) == 1 and P._parzen(0.5) == pytest.approx(0.25) and P._parzen(1) == 0 and P._parzen(1.5) == 0


def test_circular_blocks_wrap_past_the_last_month():
    rng = np.random.default_rng(0)
    idx = P.circular_block_indices(10, 4, 500, rng)
    assert idx.shape == (500, 8) and idx.min() == 0 and idx.max() == 9
    blocks = idx.reshape(500, 2, 4)
    assert np.all((np.diff(blocks, axis=2) % 10) == 1)          # consecutive months, 9 followed by 0


def test_rejects_a_true_null_at_about_the_nominal_rate():
    out = P.size_check(pairs=200, months=240, sd=0.0025, rho=0.99, dof=5, seed=3, draws=299)
    # 200 pairs: two standard errors of a proportion of 0.05 is 0.031
    assert 0.01 <= out["rate"] <= 0.05 + 0.031 + 0.02
    assert out["rejected"] == int((out["p_values"] < 0.05).sum()) and len(out["differences"]) == 200


def test_a_large_true_difference_is_found_and_the_interval_narrows_with_more_months():
    r1, r2 = _pair(960, 6, scale2=1.08)         # the second series 8 per cent more volatile
    out = P.test(r1, r2, draws=499, seed=2)
    assert out["excludes_zero"] and out["upper"] < 0 and out["p_value"] < 0.01
    short = P.test(*_pair(240, 4), draws=499, seed=1)
    long = P.test(*_pair(960, 4), draws=499, seed=1)
    assert long["half_width"] < 0.7 * short["half_width"]


def test_holm_by_hand():
    adjusted = P.holm([0.01, 0.04, 0.03, 0.20])
    # sorted: 0.01 x 4 = 0.04, 0.03 x 3 = 0.09, 0.04 x 2 = 0.09 (held at 0.09), 0.20 x 1 = 0.20
    assert np.allclose(adjusted, [0.04, 0.09, 0.09, 0.20])
    assert np.allclose(P.holm([0.5, 0.9]), [1.0, 1.0])


def test_chunked_bootstrap_equals_unchunked_at_the_chunks_used_and_within_1e_12_at_one_draw():
    # the daily test uses chunks of 200 draws and the monthly test is not chunked; a draw computed alone
    # need not give the bits it gives among many, so a chunk of one is held to 1e-12
    r1, r2 = _pair(600, 8)
    whole = P.test(r1, r2, draws=301, seed=4)
    for chunk in (7, 100, 200, 301, 1000):
        assert P.test(r1, r2, draws=301, seed=4, chunk=chunk) == whole
    one = P.test(r1, r2, draws=301, seed=4, chunk=1)
    for key, value in whole.items():
        if isinstance(value, float):
            assert abs(one[key] - value) <= 1e-12, key
        else:
            assert one[key] == value, key


def test_the_detectable_difference_and_the_chance_follow_the_normal_formulas():
    assert P.normal_cdf(0) == 0.5 and P.normal_cdf(1.959963985) == pytest.approx(0.975, abs=1e-6)
    assert P.normal_quantile(0.8) == pytest.approx(0.8416212, abs=1e-6) and P.normal_quantile(0.975) == pytest.approx(1.959964, abs=1e-6)
    assert P.detectable_difference(1.0, 2.0, 0.8) == pytest.approx(2.8416212, abs=1e-6)
    assert P.chance_to_exclude_zero(0.0, 1.0, 2.0) == pytest.approx(P.normal_cdf(-2.0))
    assert P.chance_to_exclude_zero(2.8416212, 1.0, 2.0) == pytest.approx(0.8, abs=1e-6)     # at the detectable difference the chance is the power
    assert P.chance_to_exclude_zero(-3.0, 1.5, 2.0) == P.chance_to_exclude_zero(3.0, 1.5, 2.0)
    with pytest.raises(ValueError):
        P.normal_quantile(1.0)


def test_the_constants_name_the_comparisons_and_the_settings():
    assert C.PAIRED_TEST_DATE == "2026-11-18"
    assert C.PAIRED_REFERENCE == ("sample", "daily 3y") and len(C.PAIRED_COMPARISONS_A) == 6
    assert C.PAIRED_REFERENCE not in C.PAIRED_COMPARISONS_A
    assert len(C.PAIRED_COMPARISONS_B) == 7 and C.PAIRED_COMPARISON_B_SETS == ("C3", "C3 tilt only")
    assert len(C.PAIRED_COMPARISONS_C) == 4
    assert C.PAIRED_SIZE_PAIRS == 1000 and C.PAIRED_SIZE_MONTHS == 566 and C.PAIRED_SIZE_CORRELATION == 0.99
    assert C.PAIRED_SIZE_RANGE == (0.035, 0.065)
    assert C.PAIRED_DETECTABLE_POWER == 0.80 and len(C.PAIRED_PAPER_GAIN_WITH_CAP) == 2
    assert all(rm < sample for rm, sample in C.PAIRED_PAPER_GAIN_WITH_CAP.values())
    assert C.EVAL_BOOTSTRAP_BLOCK_MONTHS == 12 and C.EVAL_BOOTSTRAP_DRAWS == 2000 and C.EVAL_BOOTSTRAP_LEVEL == 0.95
    # E, added on 18 November 2026 after every recorded run: the three pairs among the four daily estimators that A does not test
    assert C.PAIRED_E_DATE == "2026-11-18" and len(C.PAIRED_COMPARISONS_E) == 3
    daily = {("ledoit_wolf", "daily 3y"), ("factor", "daily 3y"), ("pca", "daily 3y")}
    assert all(a in daily and b in daily and a != b for a, b in C.PAIRED_COMPARISONS_E)
    assert len({frozenset(pair) for pair in C.PAIRED_COMPARISONS_E}) == 3
    assert C.PAIRED_REFERENCE not in {v for pair in C.PAIRED_COMPARISONS_E for v in pair}
    assert C.REPLICATION_VS_1N_DATE == "2026-11-18"
    # the additions of 19 November 2026, after the study's results were known: block lengths, Holm for B and across A with E,
    # the further size checks, the bias statistic before 2000 and from 2000
    assert C.PAIRED_ADDITIONS_DATE == "2026-11-19"
    assert C.PAIRED_BLOCK_LENGTHS_FURTHER == (3, 6, 24) and C.EVAL_BOOTSTRAP_BLOCK_MONTHS not in C.PAIRED_BLOCK_LENGTHS_FURTHER
    assert C.PAIRED_BLOCK_FAMILIES_FURTHER == ("A", "B", "E")
    assert C.PAIRED_HOLM_FAMILIES_FURTHER == ("B",) and C.PAIRED_HOLM_JOINT_FAMILIES == ("A", "E")
    assert len(C.PAIRED_SIZE_FURTHER_SEEDS) == 3 and C.PAIRED_SIZE_SEED not in C.PAIRED_SIZE_FURTHER_SEEDS
    assert len(set(C.PAIRED_SIZE_FURTHER_SEEDS)) == 3
    assert C.PAIRED_SIZE_FURTHER_CORRELATIONS == (0.93, 0.81) and all(0 < r < C.PAIRED_SIZE_CORRELATION for r in C.PAIRED_SIZE_FURTHER_CORRELATIONS)
    assert C.EVAL_BIAS_SPLIT_MONTH == "2000-01" and C.EVAL_BIAS_SPLIT_SET == "C3"


# Batch means, added on 24 November 2026 after the results of notebooks 17 and 18 were known.

def test_student_t_matches_tabulated_values():
    # values from a reference implementation of Student's t, to the digits shown
    assert P.student_t_cdf(2.0, 10) == pytest.approx(0.9633059826146299, abs=1e-13)
    assert P.student_t_cdf(-1.3, 46) == pytest.approx(0.10003875066734813, abs=1e-13)
    assert P.student_t_cdf(0.0, 5) == 0.5
    assert P.student_t_quantile(0.975, 46) == pytest.approx(2.012895598919429, abs=1e-9)
    assert P.student_t_quantile(0.975, 22) == pytest.approx(2.0738730679040254, abs=1e-9)
    # with many degrees of freedom the t is close to the normal
    assert P.student_t_quantile(0.975, 100000) == pytest.approx(P.normal_quantile(0.975), abs=1e-4)


def test_batch_means_with_blocks_of_one_is_the_standard_error_of_independent_periods():
    r1, r2 = _pair(600, 11, scale2=1.05)
    psi = P.influence_series(r1, r2)
    assert abs(psi["sd"].mean()) < 1e-15 and abs(psi["log"].mean()) < 1e-15
    out = P.batch_means(r1, r2, block=1)
    assert out["blocks"] == 600 and out["left_out"] == 0
    assert out["se"] == pytest.approx(psi["sd"].std(ddof=1) / np.sqrt(600))
    assert out["se_log"] == pytest.approx(psi["log"].std(ddof=1) / np.sqrt(600))
    assert out["difference"] == pytest.approx(P.sd_difference(r1, r2))
    assert out["log_difference"] == pytest.approx(P.log_variance_difference(r1, r2))


def test_batch_means_by_hand():
    r1, r2 = _pair(250, 12)
    out = P.batch_means(r1, r2, block=24, level=0.95)
    assert out["blocks"] == 10 and out["left_out"] == 10
    psi = P.influence_series(r1, r2)
    means = psi["sd"][:240].reshape(10, 24).mean(axis=1)
    se = means.std(ddof=1) / np.sqrt(10)
    assert out["se"] == pytest.approx(se)
    crit = P.student_t_quantile(0.975, 9)
    assert out["critical"] == pytest.approx(crit)
    assert out["lower"] == pytest.approx(out["difference"] - crit * se) and out["upper"] == pytest.approx(out["difference"] + crit * se)
    t = out["log_difference"] / out["se_log"]
    assert out["t"] == pytest.approx(t)
    assert out["p_value"] == pytest.approx(2 * (1 - P.student_t_cdf(abs(t), 9)), abs=1e-12)
    with pytest.raises(ValueError):
        P.batch_means(r1, r2, block=200)


def test_the_batch_means_constants():
    assert C.BATCH_MEANS_BLOCK_DAYS == C.DAILY_BLOCK == 252
    assert set(C.BATCH_MEANS_MONTHS_OF) == {C.BATCH_MEANS_BLOCK_DAYS, *C.BATCH_MEANS_BLOCK_DAYS_FURTHER}
    assert all(C.BATCH_MEANS_MONTHS_OF[d] * 21 == d for d in C.BATCH_MEANS_MONTHS_OF)
    assert C.BATCH_MEANS_HOLM_FAMILIES == ("A", "B")
