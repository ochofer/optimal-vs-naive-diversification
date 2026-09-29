"""The verdict rules of the comparison tables, checked on made-up results."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import compare as CMP  # noqa: E402
from bp import constants as C  # noqa: E402
from bp import dgu_published as P  # noqa: E402


def _frame(**sharpe):
    return pd.DataFrame({"sharpe": pd.Series(sharpe), "ceq": 0.0, "turnover": 0.02, "turnover_rel": 1.0, "return_loss": 0.0})


def test_gating_follows_published_relative_turnover():
    assert CMP.sharpe_is_gated("ew", "Industry")
    assert CMP.sharpe_is_gated("vw", "Industry")
    assert CMP.sharpe_is_gated("mv", "MKT/SMB/HML")        # published relative turnover 2.83
    assert not CMP.sharpe_is_gated("mv", "Industry")        # 606,594
    assert not CMP.sharpe_is_gated("mv", "FF-4-factor")     # 3,553
    assert not CMP.sharpe_is_gated("mv (in sample)", "Industry")
    assert CMP.sharpe_is_gated("min-c", "FF-1-factor")      # 3.93


def test_sharpe_verdicts():
    pub_ew = P.SHARPE["ew"][0][0]
    pub_mv = P.SHARPE["mv"][0][0]
    results = {"Industry": _frame(ew=pub_ew + 0.02, mv=pub_mv + 0.5)}
    t = CMP.sharpe_table(results, in_sample={"Industry": 0.0})
    assert t.loc[("ew", "Industry"), "verdict"] == "pass"
    assert t.loc[("mv", "Industry"), "verdict"] == "report"
    assert t.loc[("mv (in sample)", "Industry"), "verdict"] == "report"
    results = {"Industry": _frame(ew=pub_ew + 0.04)}
    assert CMP.sharpe_table(results).loc[("ew", "Industry"), "verdict"] == "MISS"


def test_turnover_verdicts():
    results = {"Industry": pd.DataFrame({
        "sharpe": [0.1, 0.1, 0.1], "ceq": 0.0,
        "turnover": [P.TURNOVER_1N[0] * 1.1, 1.0, 1.0],
        "turnover_rel": [1.0, 2.58 * 1.3, 1.0],
        "return_loss": 0.0}, index=["ew", "min-c", "mv"])}
    t = CMP.turnover_table(results)
    assert t.loc[("ew", "Industry"), "verdict"] == "pass"        # within 25%
    assert t.loc[("min-c", "Industry"), "verdict"] == "MISS"     # 30% off a gated row
    assert t.loc[("mv", "Industry"), "verdict"] == "report"      # published 606,594


def test_top3_ranks_only_gated_rules():
    rules = ["ew", "mv", "min", "mv-c", "min-c", "g-min-c"]
    pub = {r: P.SHARPE[r][0][0] for r in rules}
    results = {"Industry": _frame(**pub)}
    t = CMP.top3_preserved(results, rules)
    assert "mv" not in t.loc["Industry", "rules_ranked"]
    assert t.loc["Industry", "verdict"] == "pass"
