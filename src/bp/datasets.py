"""
The four DGU datasets built from Ken French's library.

DGU (Table 2, p. 1918; Appendix A, pp. 1948-1949) work in monthly excess
returns over the Treasury bill rate from French's site. Each dataset is a
set of risky assets plus one or more factor portfolios:

  Industry      ten industry portfolios plus the market factor, N = 11
  MKT/SMB/HML   the three Fama-French factors as the assets, N = 3
  FF-1-factor   twenty size-and-value portfolios plus the market, N = 21
  FF-4-factor   the same twenty plus MKT, SMB, HML and UMD, N = 24

The twenty are the 25 size-and-value portfolios less the five with the
largest firms (DGU footnote 24). SMB, HML and UMD are zero-cost portfolios,
so their return is already an excess return; the industry and size-and-value
portfolios are long-only, so RF is subtracted from them.
"""
from __future__ import annotations

import pandas as pd

from . import constants as C
from . import french_loader as fl


def _window(frame: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    lo = pd.Period(start, "M") if start else frame.index[0]
    hi = pd.Period(end, "M") if end else frame.index[-1]
    return frame.loc[lo:hi]


def load_inputs(cache_dir: str = "data/french") -> dict[str, pd.DataFrame]:
    """Every French block the datasets need, in decimal returns."""
    return {
        "factors3": fl.load_monthly("factors3", 0, cache_dir),
        "momentum": fl.load_monthly("momentum", 0, cache_dir),
        "ind10": fl.load_monthly("ind10", 0, cache_dir),
        "size_bm25": fl.load_monthly("size_bm25", 0, cache_dir),
    }


def twenty_of_25(p25: pd.DataFrame) -> pd.DataFrame:
    big = [c for c in p25.columns if c.startswith("BIG") or c.startswith("ME5")]
    if len(big) != 5:
        raise ValueError(f"expected five largest-size portfolios, found {big}")
    return p25.drop(columns=big)


def build(name: str, inputs: dict[str, pd.DataFrame] | None = None,
          start: str | None = C.DGU_SAMPLE_START, end: str | None = C.DGU_SAMPLE_END,
          cache_dir: str = "data/french") -> pd.DataFrame:
    """One DGU dataset as a DataFrame of monthly excess returns, assets in columns.

    The factor columns come last, in the order DGU list them, so that the
    market factor is the last column of the Industry and FF-1-factor sets.
    """
    if inputs is None:
        inputs = load_inputs(cache_dir)
    f3, mom, i10, p25 = inputs["factors3"], inputs["momentum"], inputs["ind10"], inputs["size_bm25"]
    rf = f3["RF"]
    if name == "Industry":
        risky = i10.sub(rf, axis=0)
        out = pd.concat([risky, f3[["Mkt-RF"]]], axis=1)
    elif name == "MKT/SMB/HML":
        out = f3[["Mkt-RF", "SMB", "HML"]].copy()
    elif name == "FF-1-factor":
        risky = twenty_of_25(p25).sub(rf, axis=0)
        out = pd.concat([risky, f3[["Mkt-RF"]]], axis=1)
    elif name == "FF-4-factor":
        risky = twenty_of_25(p25).sub(rf, axis=0)
        out = pd.concat([risky, f3[["Mkt-RF", "SMB", "HML"]], mom[["Mom"]]], axis=1)
    else:
        raise KeyError(f"unknown dataset {name!r}; known: {list(C.DGU_DATASETS)}")
    out = _window(out.dropna(how="any"), start, end)
    expected = C.DGU_DATASETS[name]["N"]
    if out.shape[1] != expected:
        raise ValueError(f"{name}: {out.shape[1]} columns, DGU Table 2 says N = {expected}")
    out.attrs["name"] = name
    out.attrs["market_column"] = "Mkt-RF"
    return out


def build_all(start: str | None = C.DGU_SAMPLE_START, end: str | None = C.DGU_SAMPLE_END,
              cache_dir: str = "data/french") -> dict[str, pd.DataFrame]:
    inputs = load_inputs(cache_dir)
    return {name: build(name, inputs, start, end) for name in C.DGU_DATASETS}
