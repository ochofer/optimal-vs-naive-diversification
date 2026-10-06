"""The direct test's functions on made-up firms, no network, no CRSP data."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import direct_test as DT  # noqa: E402

MONTH_ENDS = pd.date_range("2000-05-31", "2000-12-31", freq="ME")


def _made_up_market():
    """Three firms. A and B exist all year. C lists in September 2000: its first
    month-end price is 2000-09-30, so its first return in the market is October,
    and it is in no industry portfolio until July 2001. B loses its SIC code in
    the names file for the whole period (siccd 0), so it is in the market and in
    no industry either."""
    rows = []
    for d in MONTH_ENDS:
        rows.append({"permno": 1, "date": d, "prc": 10.0, "ret": 0.01, "shrout": 100.0})   # A: value 1,000
        rows.append({"permno": 2, "date": d, "prc": -5.0, "ret": 0.02, "shrout": 100.0})   # B: value 500, bid-ask price
    for d in MONTH_ENDS[MONTH_ENDS >= "2000-09-30"]:
        rows.append({"permno": 3, "date": d, "prc": 20.0, "ret": 0.10 if d.month != 9 else np.nan, "shrout": 25.0})  # C: value 500
    msf = pd.DataFrame(rows)
    names = pd.DataFrame([
        {"permno": 1, "namedt": "1990-01-01", "nameendt": "2030-12-31", "shrcd": 10, "exchcd": 1, "siccd": 2800},
        {"permno": 2, "namedt": "1990-01-01", "nameendt": "2030-12-31", "shrcd": 11, "exchcd": 3, "siccd": 0},
        {"permno": 3, "namedt": "2000-09-15", "nameendt": "2030-12-31", "shrcd": 10, "exchcd": 3, "siccd": 7370},
    ])
    return msf, names


def test_names_are_attached_by_date_range():
    msf, names = _made_up_market()
    named = DT.attach_names(msf, names)
    assert (named.loc[named.permno == 1, "siccd"] == 2800).all()
    assert (named.loc[named.permno == 3, "exchcd"] == 3).all()
    # a row dated before the names row starts gets no codes
    early = DT.attach_names(pd.DataFrame([{"permno": 3, "date": "2000-08-31", "prc": 1.0, "ret": 0.0, "shrout": 1.0}]), names)
    assert early["shrcd"].isna().all()


def test_market_universe_needs_start_of_month_equity_and_a_return():
    msf, names = _made_up_market()
    panel = DT.monthly_panel(DT.attach_names(msf, names))
    c = panel[panel.permno == 3].set_index("month")
    assert not c.loc[pd.Period("2000-09", "M"), "in_market"]      # no start-of-month equity yet
    assert c.loc[pd.Period("2000-10", "M"), "in_market"]           # equity at the end of September, return in October
    assert np.isclose(c.loc[pd.Period("2000-10", "M"), "me_start"], 500.0)
    b = panel[panel.permno == 2].set_index("month")
    assert np.isclose(b.loc[pd.Period("2000-06", "M"), "me"], 500.0)   # negative price counts by its absolute value
    assert not panel.loc[(panel.permno == 1) & (panel.month == pd.Period("2000-05", "M")), "in_market"].iloc[0]  # first month has no previous month


def test_june_formation_excludes_late_listings_and_firms_without_sic():
    msf, names = _made_up_market()
    panel = DT.flag_industry_members(DT.monthly_panel(DT.attach_names(msf, names)))
    oct_ = panel[panel.month == pd.Period("2000-10", "M")].set_index("permno")
    assert oct_.loc[1, "in_market"] and oct_.loc[1, "in_industry"]
    assert oct_.loc[2, "in_market"] and not oct_.loc[2, "in_industry"]   # no SIC code at June
    assert oct_.loc[3, "in_market"] and not oct_.loc[3, "in_industry"]   # listed after June
    assert DT.formation_year(pd.Period("2000-10", "M")) == 2000
    assert DT.formation_year(pd.Period("2001-03", "M")) == 2000


def test_the_gap_identity_holds_on_made_up_firms():
    msf, names = _made_up_market()
    panel = DT.flag_industry_members(DT.monthly_panel(DT.attach_names(msf, names)))
    out = DT.universe_returns(panel)
    oct_ = out.loc[pd.Period("2000-10", "M")]
    # market: A 1000 at 1%, B 500 at 2%, C 500 at 10% -> (10 + 10 + 50) / 2000 = 3.5%
    assert np.isclose(oct_["r_market"], 0.035)
    # industries: A alone -> 1%; omega = (500 + 500) / 2000
    assert np.isclose(oct_["r_industries"], 0.01)
    assert np.isclose(oct_["omega"], 0.5)
    assert oct_["n_market"] == 3 and oct_["n_industries"] == 1 and oct_["n_outside"] == 2
    # the gap equals omega times (return outside minus return inside): outside = (10 + 50) / 1000 = 6%
    assert np.isclose(oct_["predicted_gap"], 0.5 * (0.06 - 0.01))


def test_compare_gaps_recovers_slope_one_when_the_series_agree():
    idx = pd.period_range("2000-01", periods=48, freq="M")
    rng = np.random.default_rng(3)
    g_hat = pd.Series(rng.normal(0, 0.002, 48), index=idx)
    out = DT.compare_gaps(g_hat.copy(), g_hat)
    assert out["months"] == 48 and abs(out["slope"] - 1.0) < 1e-9 and abs(out["correlation"] - 1.0) < 1e-9
    assert out["te_residual_annual"] == 0.0 and abs(out["share_of_variance_explained"] - 1.0) < 1e-12
    noisy = DT.compare_gaps(g_hat + pd.Series(rng.normal(0, 0.001, 48), index=idx), g_hat)
    assert 0.5 < noisy["correlation"] < 1.0 and noisy["te_residual_annual"] > 0


def test_by_calendar_month_puts_july_first():
    idx = pd.period_range("2000-01", periods=36, freq="M")
    s = pd.Series(np.arange(36) % 12 / 1000.0, index=idx)   # differs by calendar month, equal within one
    te = DT.by_calendar_month(s, "te")
    assert list(te.index[:3]) == ["Jul", "Aug", "Sep"] and np.allclose(te.fillna(0), 0)
    mean = DT.by_calendar_month(s, "mean")
    assert np.isclose(mean["Jan"], 0.0) and np.isclose(mean["Dec"], 0.011)
