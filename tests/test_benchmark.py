"""Hand-computed checks for the cap-weighted benchmark, no network."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import benchmark as BM  # noqa: E402

MONTHS = pd.period_range("2000-01", "2000-03", freq="M")


def _two_industries():
    firms = pd.DataFrame({"A": [2.0, 4.0, 1.0], "B": [3.0, 1.0, 1.0]}, index=MONTHS)
    size = pd.DataFrame({"A": [10.0, 5.0, 8.0], "B": [5.0, 15.0, 2.0]}, index=MONTHS)
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03], "B": [0.02, 0.00, -0.01]}, index=MONTHS)
    return firms, size, returns


def test_market_equity_is_count_times_size():
    firms, size, _ = _two_industries()
    me = BM.market_equity(firms, size)
    # 2 firms of 10 million each = 20 million; 3 firms of 5 million = 15 million
    assert me.loc[MONTHS[0]].tolist() == [20.0, 15.0]
    assert me.loc[MONTHS[1]].tolist() == [20.0, 15.0]


def test_same_month_weights_are_shares_of_total_market_equity():
    firms, size, _ = _two_industries()
    w = BM.cap_weights(firms, size, "same_month")
    assert np.allclose(w.loc[MONTHS[0]], [20 / 35, 15 / 35])
    assert np.allclose(w.loc[MONTHS[2]], [8 / 10, 2 / 10])
    assert np.allclose(w.sum(axis=1), 1.0)


def test_previous_month_weights_shift_by_one_month_and_leave_the_first_empty():
    firms, size, _ = _two_industries()
    w = BM.cap_weights(firms, size, "previous_month")
    assert w.loc[MONTHS[0]].isna().all()
    assert np.allclose(w.loc[MONTHS[1]], [20 / 35, 15 / 35])
    assert np.allclose(w.loc[MONTHS[2]], [20 / 35, 15 / 35])


def test_a_missing_count_removes_the_whole_month_of_weights():
    firms, size, _ = _two_industries()
    firms.loc[MONTHS[1], "B"] = np.nan
    w = BM.cap_weights(firms, size)
    assert w.loc[MONTHS[1]].isna().all()
    assert np.allclose(w.loc[MONTHS[0]], [20 / 35, 15 / 35])


def test_unknown_timing_is_refused():
    firms, size, _ = _two_industries()
    with pytest.raises(ValueError):
        BM.cap_weights(firms, size, "end_of_month")


def test_combination_return_is_the_weighted_sum():
    firms, size, returns = _two_industries()
    w = BM.cap_weights(firms, size)
    r = BM.combination_return(returns, w)
    # month 1: 20/35 * 0.01 + 15/35 * 0.02 = 0.0142857...
    assert abs(r.loc[MONTHS[0]] - (20 / 35 * 0.01 + 15 / 35 * 0.02)) < 1e-12
    # month 3: 0.8 * 0.03 + 0.2 * (-0.01) = 0.022
    assert abs(r.loc[MONTHS[2]] - 0.022) < 1e-12


def test_combination_return_is_missing_where_a_weight_is_missing():
    firms, size, returns = _two_industries()
    w = BM.cap_weights(firms, size, "previous_month")
    r = BM.combination_return(returns, w)
    assert np.isnan(r.loc[MONTHS[0]])
    assert not r.loc[MONTHS[1]:].isna().any()


def test_identical_industry_returns_give_the_common_return_whatever_the_weights():
    firms, size, _ = _two_industries()
    common = pd.Series([0.01, -0.02, 0.03], index=MONTHS)
    returns = pd.DataFrame({"A": common, "B": common})
    r = BM.combination_return(returns, BM.cap_weights(firms, size))
    assert np.allclose(r, common)
    assert BM.tracking_error(r, common) == 0.0


def test_tracking_error_is_annualised_standard_deviation_of_the_difference():
    a = pd.Series([0.02, 0.00, 0.01, 0.03], index=pd.period_range("2000-01", periods=4, freq="M"))
    b = pd.Series([0.01, 0.01, 0.01, 0.01], index=a.index)
    # differences 0.01, -0.01, 0.00, 0.02: mean 0.005, sample variance (0.000025+0.000225+0.000025+0.000225)/3
    d = np.array([0.01, -0.01, 0.00, 0.02])
    expected = d.std(ddof=1) * np.sqrt(12)
    assert abs(BM.tracking_error(a, b) - expected) < 1e-12
    out = BM.compare(a, b)
    assert out["months"] == 4
    assert np.isnan(out["correlation"])  # b does not vary, so no correlation exists
    assert abs(out["mean_difference_annual"] - 0.005 * 12) < 1e-12
    assert abs(out["max_abs_monthly_difference"] - 0.02) < 1e-12
    assert out["month_of_max"] == "2000-04"


def test_weight_extremes_name_the_industries():
    firms, size, _ = _two_industries()
    w = BM.cap_weights(firms, size)
    ex = BM.weight_extremes(w, "2000-03")
    assert ex["largest"] == "A" and abs(ex["largest_weight"] - 0.8) < 1e-12
    assert ex["smallest"] == "B" and abs(ex["smallest_weight"] - 0.2) < 1e-12
    assert ex["industries"] == 2
