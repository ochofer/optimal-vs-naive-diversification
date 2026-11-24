"""The attribution module on made-up data where every answer is known by hand."""
import sys
import pathlib

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from bp import attribution as A        # noqa: E402
from bp import constants as C          # noqa: E402

NAMES = C.ATTRIBUTION_FACTORS
K = len(NAMES)


def _months(n):
    return pd.period_range("2000-01", periods=n, freq="M")


def test_active_exposures_by_hand():
    # three assets, two of six factors matter: asset betas 1, 2, 3 on the first factor, 0 on the rest
    B = np.zeros((3, K))
    B[:, 0] = [1.0, 2.0, 3.0]
    B[:, 1] = [0.5, 0.5, 0.5]
    w = np.array([0.5, 0.3, 0.2])
    b = np.array([0.2, 0.3, 0.5])
    x = A.active_exposures(B, w, b)
    # first factor: 1 * 0.3 + 2 * 0 + 3 * (-0.3) = -0.6; second: 0.5 times the active weights, which sum to zero
    assert np.isclose(x[0], -0.6)
    assert np.isclose(x[1], 0.0)
    assert np.allclose(x[2:], 0.0)


def test_identity_holds_and_residual_is_zero_in_an_exact_factor_world():
    rng = np.random.default_rng(3)
    T, N = 24, 5
    months = _months(T)
    B = rng.normal(size=(N, K))
    F = pd.DataFrame(rng.normal(scale=0.03, size=(T, K)), index=months, columns=NAMES)
    # industry returns are exactly B times the factors: no residual anywhere
    R = pd.DataFrame(F.to_numpy() @ B.T, index=months)
    w = pd.DataFrame(np.tile([0.4, 0.3, 0.1, 0.1, 0.1], (T, 1)), index=months)
    b = pd.DataFrame(np.tile([0.2, 0.2, 0.2, 0.2, 0.2], (T, 1)), index=months)
    active = pd.Series([(w.loc[m].to_numpy() - b.loc[m].to_numpy()) @ R.loc[m].to_numpy() for m in months], index=months)
    att = A.attribute(w, b, {m: B for m in months}, F, active)
    assert att["identity error"].abs().max() < C.ATTRIBUTION_IDENTITY_MAX_ABS_ERROR
    assert att["residual"].abs().max() < 1e-12
    s = A.summarise(att)
    assert np.isclose(s["factor share"], 1.0)
    assert np.isclose(s["active return (per year)"], 12 * active.mean())


def test_residual_carries_what_the_factors_do_not_explain():
    rng = np.random.default_rng(4)
    T, N = 36, 4
    months = _months(T)
    B = np.zeros((N, K))                      # no factor exposure at all
    F = pd.DataFrame(rng.normal(scale=0.03, size=(T, K)), index=months, columns=NAMES)
    R = pd.DataFrame(rng.normal(scale=0.05, size=(T, N)), index=months)
    w = pd.DataFrame(np.tile([0.5, 0.5, 0.0, 0.0], (T, 1)), index=months)
    b = pd.DataFrame(np.tile([0.25, 0.25, 0.25, 0.25], (T, 1)), index=months)
    active = pd.Series([(w.loc[m].to_numpy() - b.loc[m].to_numpy()) @ R.loc[m].to_numpy() for m in months], index=months)
    att = A.attribute(w, b, {m: B for m in months}, F, active)
    assert np.allclose(att["factor total"], 0.0)
    assert np.allclose(att["residual"], active)
    s = A.summarise(att)
    assert np.isclose(s["factor share"], 0.0)
    assert np.isclose(s["residual (standard error)"], 12 * active.std(ddof=1) / np.sqrt(T))


def test_by_period_averages_each_group():
    T = 24
    months = _months(T)
    B = np.zeros((2, K)); B[:, 0] = [1.0, 0.0]
    F = pd.DataFrame(0.0, index=months, columns=NAMES); F["Mkt-RF"] = 0.01
    w = pd.DataFrame(np.tile([1.0, 0.0], (T, 1)), index=months)
    b = pd.DataFrame(np.tile([0.5, 0.5], (T, 1)), index=months)
    active = pd.Series(0.02, index=months)          # exposure 0.5, contribution 0.005 a month, residual 0.015
    att = A.attribute(w, b, {m: B for m in months}, F, active)
    labels = pd.Series(["first year"] * 12 + ["second year"] * 12, index=months)
    table = A.by_period(att, labels)
    assert np.allclose(table["contribution Mkt-RF"], 12 * 0.005)
    assert np.allclose(table["residual"], 12 * 0.015)
    assert list(table.index) == ["first year", "second year"]


# The Newey-West standard error, added on 24 November 2026 after the results of notebooks 13 and 16 were known.

def test_newey_west_by_hand():
    x = np.array([0.01, -0.02, 0.03, 0.00, -0.01, 0.02, 0.01, -0.03])
    t = len(x)
    u = x - x.mean()
    g0, g1, g2 = u @ u / t, u[1:] @ u[:-1] / t, u[2:] @ u[:-2] / t
    assert A.newey_west_se(x, 0) == pytest.approx(np.sqrt(g0 / t))
    assert A.newey_west_se(x, 2) == pytest.approx(np.sqrt((g0 + 2 * (2 / 3) * g1 + 2 * (1 / 3) * g2) / t))


def test_newey_west_is_larger_for_positively_correlated_months():
    rng = np.random.default_rng(5)
    e = rng.normal(size=20000)
    ar = np.empty_like(e)
    ar[0] = e[0]
    for i in range(1, len(e)):
        ar[i] = 0.3 * ar[i - 1] + e[i]
    # for an AR(1) with coefficient 0.3 the long-run variance is 1 / (1 - 0.3)^2 times the innovations', against 1 / (1 - 0.09) for the variance
    ratio = A.newey_west_se(ar, 6) / (ar.std() / np.sqrt(len(ar)))
    assert 1.2 < ratio < np.sqrt((1 - 0.09) / (1 - 0.3) ** 2) + 0.05


def test_newey_west_table_columns():
    months = _months(60)
    rng = np.random.default_rng(8)
    att = pd.DataFrame({"factor total": rng.normal(size=60), "residual": rng.normal(size=60)}, index=months)
    out = A.newey_west(att, 6, ["factor total", "residual"])
    x = att["factor total"].to_numpy()
    assert out["factor total (per year)"] == pytest.approx(12 * x.mean())
    assert out["factor total (standard error)"] == pytest.approx(12 * x.std(ddof=1) / np.sqrt(60))
    assert out["factor total (Newey-West standard error)"] == pytest.approx(12 * A.newey_west_se(x, 6))
    assert out["factor total (t, Newey-West)"] == pytest.approx(out["factor total (per year)"] / out["factor total (Newey-West standard error)"])
    assert C.ATTRIBUTION_NEWEY_WEST_LAGS == int(0.75 * 566 ** (1 / 3)) == 6
