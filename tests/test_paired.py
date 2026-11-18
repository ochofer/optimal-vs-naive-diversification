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


def test_the_constants_name_the_comparisons_and_the_settings():
    assert C.PAIRED_TEST_DATE == "2026-11-18"
    assert C.PAIRED_REFERENCE == ("sample", "daily 3y") and len(C.PAIRED_COMPARISONS_A) == 6
    assert C.PAIRED_REFERENCE not in C.PAIRED_COMPARISONS_A
    assert len(C.PAIRED_COMPARISONS_B) == 7 and C.PAIRED_COMPARISON_B_SETS == ("C3", "C3 tilt only")
    assert len(C.PAIRED_COMPARISONS_C) == 4
    assert C.PAIRED_SIZE_PAIRS == 1000 and C.PAIRED_SIZE_MONTHS == 566 and C.PAIRED_SIZE_CORRELATION == 0.99
    assert C.PAIRED_SIZE_RANGE == (0.035, 0.065)
    assert C.EVAL_BOOTSTRAP_BLOCK_MONTHS == 12 and C.EVAL_BOOTSTRAP_DRAWS == 2000 and C.EVAL_BOOTSTRAP_LEVEL == 0.95
