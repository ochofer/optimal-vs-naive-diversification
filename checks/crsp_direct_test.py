"""Run the direct test of notebook 08's explanation on the CRSP monthly stock file.

Notebook 08 explains the gap between French's market return and the cap-weighted
combination of his 49 industries by the formation rule: industries are formed
once a year at the end of June, so a firm that lists after June is in the market
and in no industry until the next July. This script tests that on firm-level
data: it builds the market universe and the June-formed universe from CRSP,
computes the gap their returns predict, and compares it with the gap observed.
The design and the expectations are in constants.py (DIRECT_TEST_*).

The CRSP data are licensed. They stay on the machine that holds them; this
script reads them in place, writes only aggregate results to
constants.DIRECT_TEST_RESULTS_FILE, and keeps its intermediate panel in a cache
folder outside the repository. The notebooks never run it.

Usage, from the repository root on that machine:
  python3 checks/crsp_direct_test.py --wrds-dir "<folder>/raw" --cache "<folder outside the repository>"
      --stage panel     build the two universes and save their monthly returns to the cache (the slow part)
      --stage compare   compare the predicted gap with the observed gap and write the results
  Without --stage both run in turn.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import benchmark as BM  # noqa: E402
from bp import constants as C  # noqa: E402
from bp import direct_test as DT  # noqa: E402
from bp import french_loader as fl  # noqa: E402

PANEL_FILE = "universe_returns.parquet"


def build_panel(wrds_dir: pathlib.Path, cache: pathlib.Path) -> pd.DataFrame:
    import pyarrow.parquet as pq
    t0 = time.time()
    msf = pq.read_table(wrds_dir / "crsp_msf" / "crsp_msf.parquet",
                        columns=["permno", "date", "prc", "ret", "shrout"]).to_pandas()
    names = pq.read_table(wrds_dir / "crsp_msenames" / "crsp_msenames.parquet",
                          columns=["permno", "namedt", "nameendt", "shrcd", "exchcd", "siccd"]).to_pandas()
    print(f"read {len(msf):,} monthly rows and {len(names):,} names rows in {time.time() - t0:.0f}s")
    panel = DT.flag_industry_members(DT.monthly_panel(DT.attach_names(msf, names)))
    print(f"panel built in {time.time() - t0:.0f}s: {int(panel['in_market'].sum()):,} firm-months in the market universe, "
          f"{int(panel['in_industry'].sum()):,} of them formed into an industry at the last June")
    out = DT.universe_returns(panel)
    cache.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache / PANEL_FILE)
    print(f"monthly universe returns saved: {len(out)} months, {out.index[0]} to {out.index[-1]}, {time.time() - t0:.0f}s")
    return out


def manifest_date(wrds_dir: pathlib.Path) -> str:
    try:
        m = json.loads((wrds_dir.parent / "manifest.json").read_text())
        for f in m["files"]:
            if f.get("key") == "crsp_msf":
                return f["fetched_utc"][:10]
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


def compare(wrds_dir: pathlib.Path, cache: pathlib.Path, french_cache: str) -> dict:
    uni = pd.read_parquet(cache / PANEL_FILE)
    uni.index = pd.PeriodIndex(uni.index, freq="M")
    inputs = BM.load_inputs(french_cache)
    start = pd.Period(C.EXT_SAMPLE_START, "M")
    weights = BM.cap_weights(inputs["firms"].loc[start:], inputs["size"].loc[start:], C.CAPW_WEIGHT_TIMING)
    combination = BM.combination_return(inputs["returns"].loc[start:], weights)
    market = inputs["market"].loc[start:]
    observed = (market - combination).rename("observed_gap")
    common = observed.index.intersection(uni.index)
    common = common[common >= start]
    uni, observed, market = uni.loc[common], observed.loc[common], market.loc[common]
    results: dict = {
        "test": "notebook 08, direct test of the explanation of the gap on firm-level data",
        "run_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "firm_level_source": "CRSP monthly stock file and names file, Center for Research in Security Prices, LLC, "
                             f"accessed via WRDS under Queen Mary University of London's subscription on {manifest_date(wrds_dir)}; "
                             "data kept on the machine that holds them, results only published",
        "french_vintage": inputs["returns"].attrs["provenance"]["vintage_line"],
        "months": int(len(common)), "first_month": str(common[0]), "last_month": str(common[-1]),
        "design": {k: getattr(C, k) for k in ("DIRECT_TEST_SHARE_CODES", "DIRECT_TEST_EXCHANGE_CODES", "DIRECT_TEST_FORMATION_MONTH",
                                                "DIRECT_TEST_MARKET_TE_MAX", "DIRECT_TEST_MIN_CORRELATION", "DIRECT_TEST_SLOPE_RANGE",
                                                "DIRECT_TEST_RESIDUAL_TE_MAX")},
    }
    # Expectation 1: the CRSP market universe reproduces French's market return.
    val = BM.compare(uni["r_market"], market)
    results["expectation_1_validation"] = {**val, "level": C.DIRECT_TEST_MARKET_TE_MAX, "met": bool(val["tracking_error_annual"] <= C.DIRECT_TEST_MARKET_TE_MAX)}
    print(f"expectation 1: CRSP market universe against French's market return, {val['tracking_error_annual'] * 1e4:.1f} bp a year "
          f"over {val['months']} months (level {C.DIRECT_TEST_MARKET_TE_MAX * 1e4:.0f}): {'MET' if results['expectation_1_validation']['met'] else 'NOT MET'}; "
          f"correlation {val['correlation']:.5f}, mean difference {val['mean_difference_annual'] * 1e4:+.1f} bp a year")
    # Expectation 2: the predicted gap explains the observed gap.
    cmp = DT.compare_gaps(observed, uni["predicted_gap"])
    lo, hi = C.DIRECT_TEST_SLOPE_RANGE
    met2 = bool(cmp["correlation"] >= C.DIRECT_TEST_MIN_CORRELATION and lo <= cmp["slope"] <= hi)
    results["expectation_2_predicted_vs_observed"] = {**cmp, "met": met2}
    print(f"expectation 2: correlation {cmp['correlation']:.3f} (at least {C.DIRECT_TEST_MIN_CORRELATION}), slope {cmp['slope']:.3f} (in {lo} to {hi}): {'MET' if met2 else 'NOT MET'}")
    print(f"   tracking error: observed gap {cmp['te_observed_annual'] * 1e4:.1f} bp, predicted gap {cmp['te_predicted_annual'] * 1e4:.1f} bp, "
          f"what remains {cmp['te_residual_annual'] * 1e4:.1f} bp a year; share of variance explained {cmp['share_of_variance_explained']:.1%}")
    # Expectation 3: reported.
    omega_month = DT.by_calendar_month(uni["omega"], "mean")
    te_obs_month = DT.by_calendar_month(observed, "te")
    te_pred_month = DT.by_calendar_month(uni["predicted_gap"], "te")
    te_res_month = DT.by_calendar_month(observed - uni["predicted_gap"], "te")
    omega_year = uni["omega"].groupby(uni.index.year).mean()
    outside_year = uni["n_outside"].groupby(uni.index.year).mean()
    results["expectation_3_reported"] = {
        "omega_by_calendar_month_percent": {k: round(float(v) * 100, 3) for k, v in omega_month.items()},
        "te_observed_by_calendar_month_bp": {k: round(float(v) * 1e4, 1) for k, v in te_obs_month.items()},
        "te_predicted_by_calendar_month_bp": {k: round(float(v) * 1e4, 1) for k, v in te_pred_month.items()},
        "te_residual_by_calendar_month_bp": {k: round(float(v) * 1e4, 1) for k, v in te_res_month.items()},
        "omega_by_year_percent_top5": {str(k): round(float(v) * 100, 3) for k, v in omega_year.sort_values(ascending=False).head(5).items()},
        "omega_by_decade_percent": {str(k): round(float(v) * 100, 3) for k, v in uni["omega"].groupby((uni.index.year // 10) * 10).mean().items()},
        "firms_outside_industries_by_decade_mean": {str(k): round(float(v), 0) for k, v in outside_year.groupby((outside_year.index // 10) * 10).mean().items()},
        "firms_market_by_decade_mean": {str(k): round(float(v), 0) for k, v in uni["n_market"].groupby((uni.index.year // 10) * 10).mean().items()},
    }
    table = pd.DataFrame({"share of market capitalisation outside the industries, %": omega_month * 100, "TE observed gap, bp": te_obs_month * 1e4,
                          "TE predicted gap, bp": te_pred_month * 1e4, "TE what remains, bp": te_res_month * 1e4})
    print("\nexpectation 3, by calendar month (July first):")
    print(table.to_string(float_format=lambda v: f"{v:.1f}"))
    print("\nomega by year, the five largest:", {k: f"{v:.2f}%" for k, v in results["expectation_3_reported"]["omega_by_year_percent_top5"].items()})
    print("omega by decade:", {k: f"{v:.2f}%" for k, v in results["expectation_3_reported"]["omega_by_decade_percent"].items()})
    # Expectation 4: what remains.
    met4 = bool(cmp["te_residual_annual"] <= C.DIRECT_TEST_RESIDUAL_TE_MAX)
    results["expectation_4_residual"] = {"te_residual_annual": cmp["te_residual_annual"], "level": C.DIRECT_TEST_RESIDUAL_TE_MAX, "met": met4}
    print(f"\nexpectation 4: what remains after the predicted gap, {cmp['te_residual_annual'] * 1e4:.1f} bp a year (level {C.DIRECT_TEST_RESIDUAL_TE_MAX * 1e4:.0f}): {'MET' if met4 else 'NOT MET'}")
    # the twelve months of largest observed gap, with the prediction beside them
    worst = observed.abs().sort_values(ascending=False).head(12).index.sort_values()
    side = pd.DataFrame({"observed gap": observed.loc[worst], "predicted gap": uni.loc[worst, "predicted_gap"], "omega": uni.loc[worst, "omega"]})
    results["largest_observed_gaps"] = {str(k): {"observed": round(float(r["observed gap"]), 5), "predicted": round(float(r["predicted gap"]), 5), "omega": round(float(r["omega"]), 4)} for k, r in side.iterrows()}
    print("\nthe twelve months of largest observed gap:")
    print(side.to_string(float_format=lambda v: f"{v:.4f}"))
    path = ROOT / C.DIRECT_TEST_RESULTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=1) + "\n")
    print(f"\nresults written to {path.relative_to(ROOT)}")
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wrds-dir", required=True, help="the raw/ folder of the WRDS extraction, holding crsp_msf/ and crsp_msenames/")
    ap.add_argument("--cache", required=True, help="a folder outside the repository for the intermediate monthly universe returns")
    ap.add_argument("--french-cache", default="data/french", help="where French's files are downloaded (ignored by git)")
    ap.add_argument("--stage", choices=["panel", "compare"], default=None)
    a = ap.parse_args()
    wrds_dir, cache = pathlib.Path(a.wrds_dir), pathlib.Path(a.cache)
    if a.stage in (None, "panel"):
        build_panel(wrds_dir, cache)
    if a.stage in (None, "compare"):
        compare(wrds_dir, cache, a.french_cache)


if __name__ == "__main__":
    main()
