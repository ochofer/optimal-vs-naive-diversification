"""The direct test of notebook 08's explanation of the gap, on firm-level data.

The first part of notebook 08 finds that the cap-weighted combination of French's
49 industries differs from French's market return by 47 basis points a year of
tracking error, and explains the gap by French's formation rule: industries are
formed once a year at the end of June, so a firm that lists after June is in the
market return and in no industry until the next July. Testing that needs the list
of firms in each portfolio each month, which only firm-level data give. The
functions here build the two universes from a monthly stock file, compute their
value-weighted returns and compare the gap they predict with the gap observed.
They take data frames and return data frames or numbers, so that they run on
made-up firms in the tests; checks/crsp_direct_test.py feeds them the CRSP
monthly stock file, which never leaves the machine that holds it.

Columns expected (CRSP names): msf has permno, date, prc, ret, shrout; names has
permno, namedt, nameendt, shrcd, exchcd, siccd. Dates are month ends.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C

PERIODS_PER_YEAR = 12


def attach_names(msf: pd.DataFrame, names: pd.DataFrame) -> pd.DataFrame:
    """Give each monthly row the share code, exchange code and SIC code in force on its date.

    A names row covers namedt to nameendt inclusive. A month whose date falls
    in no names row gets missing codes and so belongs to no universe.
    """
    m = msf.copy()
    m["date"] = pd.to_datetime(m["date"])
    n = names[["permno", "namedt", "nameendt", "shrcd", "exchcd", "siccd"]].copy()
    n["namedt"] = pd.to_datetime(n["namedt"])
    n["nameendt"] = pd.to_datetime(n["nameendt"])
    m = m.sort_values(["date", "permno"]).reset_index(drop=True)
    n = n.sort_values(["namedt", "permno"]).reset_index(drop=True)
    out = pd.merge_asof(m, n, left_on="date", right_on="namedt", by="permno", direction="backward")
    expired = out["date"] > out["nameendt"]
    out.loc[expired, ["shrcd", "exchcd", "siccd"]] = np.nan
    return out.drop(columns=["namedt", "nameendt"])


def monthly_panel(named: pd.DataFrame) -> pd.DataFrame:
    """Start-of-month market equity and the market-universe flag for every firm and month.

    Market equity at the end of a month is the absolute price times shares
    outstanding (a negative price in CRSP is a bid-ask average; the units of
    shares cancel in every weight). The start-of-month value is the previous
    month's end value, and only if that month is the one immediately before.
    A firm is in the market universe M_t when its share code and exchange code
    are among those French uses, it has start-of-month market equity, and it
    has a return for the month.
    """
    df = named.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    df["mi"] = df["date"].dt.year * 12 + df["date"].dt.month
    df["ret"] = df["ret"].where(df["ret"] > -1.0)
    df["me"] = df["prc"].abs() * df["shrout"]
    df = df.sort_values(["permno", "mi"]).reset_index(drop=True)
    prev = df.groupby("permno")[["me", "mi"]].shift(1)
    consecutive = (df["mi"] - prev["mi"]) == 1
    df["me_start"] = prev["me"].where(consecutive)
    codes_ok = df["shrcd"].isin(C.DIRECT_TEST_SHARE_CODES) & df["exchcd"].isin(C.DIRECT_TEST_EXCHANGE_CODES)
    df["in_market"] = codes_ok & (df["me_start"] > 0) & df["ret"].notna()
    return df


def formation_year(month: pd.Period) -> int:
    """The June whose portfolios a month belongs to: June of the same year from July on, the year before until June."""
    return month.year if month.month > C.DIRECT_TEST_FORMATION_MONTH else month.year - 1


def june_members(panel: pd.DataFrame) -> pd.DataFrame:
    """The firms an industry portfolio could hold from each July: in the market codes at the end of June, with market equity then and a positive SIC code."""
    june = panel[(panel["month"].dt.month == C.DIRECT_TEST_FORMATION_MONTH)
                 & panel["shrcd"].isin(C.DIRECT_TEST_SHARE_CODES)
                 & panel["exchcd"].isin(C.DIRECT_TEST_EXCHANGE_CODES)
                 & (panel["me"] > 0) & (panel["siccd"] > 0)]
    out = june[["permno"]].copy()
    out["formation_year"] = june["month"].dt.year.to_numpy()
    out["in_june"] = True
    return out.drop_duplicates()


def flag_industry_members(panel: pd.DataFrame) -> pd.DataFrame:
    """Add in_industry: in the market universe this month and formed into an industry at the last June."""
    df = panel.copy()
    df["formation_year"] = np.where(df["month"].dt.month > C.DIRECT_TEST_FORMATION_MONTH, df["month"].dt.year, df["month"].dt.year - 1)
    members = june_members(df)
    df = df.merge(members, on=["permno", "formation_year"], how="left")
    df["in_industry"] = df["in_market"] & df["in_june"].eq(True)
    return df


def universe_returns(panel: pd.DataFrame) -> pd.DataFrame:
    """Per month: value-weighted returns of M_t and I_t, the share omega of market equity outside the industries, and the firm counts."""
    df = panel[panel["in_market"]].copy()
    df["w_ret"] = df["me_start"] * df["ret"]
    g = df.groupby("month")
    out = pd.DataFrame({
        "r_market": g["w_ret"].sum() / g["me_start"].sum(),
        "n_market": g.size(),
        "me_market": g["me_start"].sum(),
    })
    ind = df[df["in_industry"]]
    gi = ind.groupby("month")
    out["r_industries"] = gi["w_ret"].sum() / gi["me_start"].sum()
    out["n_industries"] = gi.size()
    out["me_industries"] = gi["me_start"].sum()
    out["omega"] = 1.0 - out["me_industries"] / out["me_market"]
    out["n_outside"] = out["n_market"] - out["n_industries"].fillna(0).astype(int)
    out["predicted_gap"] = out["r_market"] - out["r_industries"]
    return out


def tracking_error(d: pd.Series, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    d = d.dropna()
    return float(d.std(ddof=1) * np.sqrt(periods_per_year)) if len(d) > 1 else float("nan")


def compare_gaps(observed: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """How much of the observed gap the predicted one accounts for: correlation, the slope and intercept of observed on predicted, and three tracking errors (observed, predicted, what remains)."""
    both = pd.concat([observed.rename("g"), predicted.rename("g_hat")], axis=1).dropna()
    g, gh = both["g"].to_numpy(), both["g_hat"].to_numpy()
    slope, intercept = np.polyfit(gh, g, 1)
    resid = both["g"] - both["g_hat"]
    return {
        "months": int(len(both)),
        "correlation": float(np.corrcoef(g, gh)[0, 1]),
        "slope": float(slope),
        "intercept_monthly": float(intercept),
        "te_observed_annual": tracking_error(both["g"]),
        "te_predicted_annual": tracking_error(both["g_hat"]),
        "te_residual_annual": tracking_error(resid),
        "share_of_variance_explained": float(1.0 - resid.var(ddof=1) / both["g"].var(ddof=1)),
    }


def by_calendar_month(series: pd.Series, how: str = "te") -> pd.Series:
    """A series summarised by calendar month, July first: 'te' for annualised standard deviation, 'mean' for the average."""
    s = series.dropna()
    grouped = s.groupby(s.index.month)
    out = grouped.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR) if how == "te" else grouped.mean()
    out.index = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][: len(out)] if len(out) == 12 else out.index
    order = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    return out.reindex(order) if len(out) == 12 else out
