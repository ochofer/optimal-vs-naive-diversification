"""Builds the dashboard, dashboard/B-P_dashboard.html, and the static figures in dashboard/figures/
from the output files the notebooks write to outputs/ and from template.html.

Usage, from the repository root, after notebooks 03, 07, 08, 10, 11, 12, 13, 15 and 16 have run:
    python3 dashboard/build_dashboard.py

The page embeds the data it draws, so it opens from a file; the charts are drawn in the browser by
Plotly, loaded from its content delivery network, so the interactive page needs a connection once.
The three static figures (SVG, drawn with matplotlib) are the ones the README shows and need nothing.
Every number in the page's prose is computed here from the output files and substituted into the
template; the build stops, naming the notebook to run, if an input file is missing, and stops again
if an input file differs from its committed copy in results/<vintage>/, so that the page can only be
built from the tables a reader can open at the commit; the source lines name that folder. The footer
states the vintage, the source notebooks and the build date, and the page is rebuilt whenever a
notebook is rerun (copy the new output files to results/<vintage>/ first). The data are embedded
with two decimals more than the page displays, so that no displayed number is rounded twice.
"""
import datetime
import glob
import json
import os
import re
import sys
import zoneinfo

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
OUTPUTS = os.path.join(REPO, "outputs")
FIG_DIR = os.path.join(SCRIPT_DIR, "figures")
OUT = os.path.join(SCRIPT_DIR, "B-P_dashboard.html")


INPUTS = []


def need(pattern, notebook):
    """The one file matching pattern under outputs/, or a message naming the notebook that writes it."""
    hits = sorted(glob.glob(os.path.join(OUTPUTS, pattern)))
    if len(hits) != 1:
        sys.exit(f"dashboard/build_dashboard.py: expected one file outputs/{pattern}, found {len(hits)}; run notebook {notebook} first")
    INPUTS.append(hits[0])
    return hits[0]


def committed(vintage):
    """Stops unless every input read so far is byte-identical to its copy in results/<vintage>/."""
    for path in INPUTS:
        name = os.path.basename(path)
        copy = os.path.join(REPO, "results", vintage, name)
        if not os.path.exists(copy):
            sys.exit(f"dashboard/build_dashboard.py: outputs/{name} has no committed copy results/{vintage}/{name}; copy the output files to results/{vintage}/ and commit them before building")
        if open(path, "rb").read() != open(copy, "rb").read():
            sys.exit(f"dashboard/build_dashboard.py: outputs/{name} differs from the committed copy results/{vintage}/{name}; copy the output files to results/{vintage}/ and commit them before building")


provenance = json.load(open(need("provenance_french.json", "13")))
vintages = {m.group(1) for rec in provenance for m in [re.search(r"using the (\d{6}) CRSP", rec.get("vintage_line", ""))] if m}
if len(vintages) != 1:
    sys.exit(f"dashboard/build_dashboard.py: expected one CRSP vintage in outputs/provenance_french.json, found {sorted(vintages)}")
V = vintages.pop()

# --- inputs, one line per file, with the notebook that writes it ---
rep_sharpe = pd.read_csv(need(f"replication_sharpe_{V}.csv", "03"))
rep_turn = pd.read_csv(need(f"replication_turnover_{V}.csv", "03"))
ext_sharpe = pd.read_csv(need(f"extended_sample_sharpe_{V}.csv", "07"))
ext_vs = pd.read_csv(need(f"extended_sample_vs_1N_{V}.csv", "07"))
bench = pd.read_csv(need(f"benchmark_returns_{V}.csv", "08"), index_col=0)
bench_w = pd.read_csv(need(f"benchmark_weights_{V}.csv", "08"), index_col=0)
cov = pd.read_csv(need(f"covariance_estimators_{V}.csv", "10"))
mv_costs = pd.read_csv(need(f"minimum_variance_costs_{V}.csv", "10"))
opt_fixes = pd.read_csv(need(f"optimiser_fixes_{V}.csv", "11"))
opt_speed = pd.read_csv(need(f"optimiser_speed_limit_{V}.csv", "11"))
roll = pd.read_csv(need(f"rolling_evaluation_{V}.csv", "12"))
roll_dec = pd.read_csv(need(f"rolling_evaluation_by_decade_{V}.csv", "12"))
roll_cal = pd.read_csv(need(f"rolling_evaluation_calibration_{V}.csv", "12"))
active = pd.read_csv(need(f"active_returns_{V}.csv", "12"), index_col=0)
att = pd.read_csv(need(f"attribution_summary_{V}.csv", "13"))
att_cost = pd.read_csv(need(f"attribution_mandate_cost_{V}.csv", "13"))
att_dec = pd.read_csv(need(f"attribution_by_decade_{V}.csv", "13"))
roll_desc = pd.read_csv(need(f"rolling_evaluation_descriptives_{V}.csv", "12"))
roll_bias_dec = pd.read_csv(need(f"rolling_evaluation_bias_by_decade_{V}.csv", "12"))
fc_te = pd.read_csv(need(f"forecast_tracking_errors_{V}.csv", "12"), index_col=0)
roll_te = pd.read_csv(need(f"rolling_tracking_error_{V}.csv", "12"), index_col=0)
roll_w = pd.read_csv(need(f"rolling_weights_*_{V}.csv", "12"), index_col=0)
fo_eval = pd.read_csv(need(f"factor_objective_evaluation_{V}.csv", "15"), index_col=0)
fo_verd = pd.read_csv(need(f"factor_objective_verdicts_{V}.csv", "15"))
fo_bm = pd.read_csv(need(f"factor_objective_budget_months_{V}.csv", "15"))
fo_att = pd.read_csv(need(f"factor_objective_attribution_{V}.csv", "16"), index_col=0)
fo_verd16 = pd.read_csv(need(f"factor_objective_attribution_verdict_{V}.csv", "16"))
fo_bought = pd.read_csv(need(f"factor_objective_exposure_bought_{V}.csv", "16"), index_col=0)
fo_gap = pd.read_csv(need(f"factor_objective_gap_{V}.csv", "16"), index_col=0)
committed(V)
direct = json.load(open(os.path.join(REPO, "checks", "results_crsp_direct_test.json")))   # committed with notebook 08; aggregates only

RULES = ["ew", "mv", "bs", "min", "vw", "mv-c", "bs-c", "min-c", "g-min-c"]
RULE_LABEL = {"ew": "1/N", "mv": "mean-variance", "bs": "Bayes-Stein", "min": "minimum variance", "vw": "value-weighted market",
              "mv-c": "mean-variance, constrained", "bs-c": "Bayes-Stein, constrained", "min-c": "minimum variance, constrained",
              "g-min-c": "minimum variance, generalised constraint"}
RULE_SHORT = {"ew": "1/N", "mv": "mean-variance", "bs": "Bayes-Stein", "min": "min. variance", "vw": "VW market",
              "mv-c": "mean-var., constr.", "bs-c": "Bayes-Stein, constr.", "min-c": "min. var., constr.", "g-min-c": "min. var., gen. constr."}   # phones only
DATASETS = ["Industry", "MKT/SMB/HML", "FF-1-factor", "FF-4-factor"]
VARIANTS = ["sample, daily 3y", "ledoit_wolf, daily 3y", "factor, daily 3y", "pca, daily 3y", "sample, monthly 120", "robust, all five", "RiskMetrics, daily 5y"]
VLABEL = {"sample, daily 3y": "Sample, 3y daily", "ledoit_wolf, daily 3y": "Ledoit-Wolf, 3y daily", "factor, daily 3y": "Six-factor model, 3y daily",
          "pca, daily 3y": "Principal components, 3y daily", "sample, monthly 120": "Sample, 120 months", "robust, all five": "Robust (worst of five)",
          "RiskMetrics, daily 5y": "RiskMetrics, 5y daily"}
# Colours: the house categorical palette of the public output standard of 9 October 2026, in one fixed slot
# order for the seven estimator variants and one for the six factors, never cycled; on white it passes the
# lightness, chroma, colour-vision-deficiency separation and normal-vision checks of an OKLab palette validator
# for neighbouring slots, and the pages keep series in their slots and label marks directly where two series can
# meet. The residual and the reference series are greys; a miss is the status red. Light only.
PALETTE = ["#24599e", "#d9711c", "#12929f", "#c8423b", "#6b45b8", "#7c9a12", "#b03a72", "#a87b00"]
NAVY, INK, INK2, META, FRAME, GRID = "#16213a", "#262b33", "#5d6470", "#6b7280", "#cfcfcf", "#e5e5e5"
VCOLOUR = dict(zip(VARIANTS, PALETTE[:7]))
VSHORT = {"sample, daily 3y": "Sample, daily", "ledoit_wolf, daily 3y": "Ledoit-Wolf", "factor, daily 3y": "Six-factor", "pca, daily 3y": "Principal comp.",
          "sample, monthly 120": "Sample, monthly", "robust, all five": "Robust", "RiskMetrics, daily 5y": "RiskMetrics"}
SETS = ["C0", "C1", "C2", "C3 tilt only", "C3"]
SET_LABEL = {"C0": "long-only", "C1": "+ active weight bound", "C2": "+ turnover cap", "C3 tilt only": "+ tilt", "C3": "+ exclusions and beta neutrality"}
FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
FLABEL = {"Mkt-RF": "market", "SMB": "size", "HML": "value", "RMW": "profitability", "CMA": "investment", "Mom": "momentum"}
FCOLOUR = dict(zip(FACTORS, PALETTE[:6]))
RESID_COLOUR = "#8c8c8c"      # the residual: a neutral grey, the remainder after the six factors
MISS_COLOUR = "#b42318"       # the status red of the standard, always with its label

assert list(bench.columns) == ["benchmark", "market"]
assert set(roll["variant"]) == set(VARIANTS) and set(roll["set"]) == set(SETS)
assert set(att["variant"]) == set(VARIANTS)
MONTHS = int(att["months"].iloc[0])
FIRST, LAST = active.index[0], active.index[-1]
assert len(active) == MONTHS


def r(x, d=4):
    return float(round(float(x), d))


# --- the data the page embeds ---
D = {"vintage": V, "months": MONTHS, "first": FIRST, "last": LAST, "variants": VARIANTS, "vlabel": VLABEL, "vshort": VSHORT,
     "sets": SETS, "setlabel": SET_LABEL, "factors": FACTORS, "flabel": FLABEL, "tilted": ["Oil", "Util", "Coal"],
     "rules": RULES, "rulelabel": RULE_LABEL, "ruleshort": RULE_SHORT, "datasets": DATASETS}

# 1. replication
D["rep_sharpe"] = [{"rule": row.rule, "dataset": row.dataset, "x": r(row.published, 6), "y": r(row.replicated, 6), "verdict": row.verdict}
                   for row in rep_sharpe.itertuples() if row.rule != "mv (in sample)"]
D["rep_turn"] = [{"rule": row.rule, "dataset": row.dataset, "x": r(row.published, 4), "y": r(row.replicated, 4), "verdict": row.verdict}
                 for row in rep_turn.itertuples() if row.rule != "vw" and row.published == row.published]
gated = rep_sharpe[rep_sharpe.verdict.isin(["pass", "MISS"])]
gated_t = rep_turn[rep_turn.verdict.isin(["pass", "MISS"])]

# 2. the months since the paper
periods = list(dict.fromkeys(ext_sharpe["period"]))
assert len(periods) == 3
D["ext_periods"] = periods
D["ext_sharpe"] = {}
for p in periods:
    sub = ext_sharpe[ext_sharpe.period == p].set_index("rule")
    D["ext_sharpe"][p] = {d: {rule: r(sub.loc[rule, d], 6) for rule in RULES} for d in DATASETS}
D["ext_vs"] = [{"dataset": row.dataset, "rule": row.rule, "p": r(row._6, 4)} for row in ext_vs.itertuples()]

# 3. the benchmark
cum_b = (1 + bench["benchmark"]).cumprod()
cum_m = (1 + bench["market"]).cumprod()
gap = (bench["benchmark"] - bench["market"])
D["bench"] = {"month": list(bench.index), "benchmark": [r(x, 4) for x in cum_b], "market": [r(x, 4) for x in cum_m],
              "gap_cum_bp": [r(x * 1e4, 2) for x in gap.cumsum()]}
D["bench_te_bp"] = r(gap.std() * np.sqrt(12) * 1e4, 1)
D["bench_corr"] = r(bench.corr().iloc[0, 1], 4)
top_ind = bench_w.mean().sort_values(ascending=False).index[:8].tolist()
w_q = bench_w.iloc[::3]   # every third month keeps the file small
D["bench_w"] = {"month": list(w_q.index), "ind": top_ind, "w": {i: [r(x, 5) for x in w_q[i]] for i in top_ind},
                "other": [r(x, 5) for x in (1 - w_q[top_ind].sum(axis=1))]}

# 4. estimators without constraints
main = cov[cov.estimator.isin(["sample", "ledoit_wolf", "factor", "pca"]) & cov.data.isin(["monthly_120", "daily_3y"])]
EST_LABEL = {"sample": "sample", "ledoit_wolf": "Ledoit-Wolf", "factor": "six-factor model", "pca": "principal components"}
D["cov"] = [{"estimator": EST_LABEL[row.estimator], "data": row.data, "unconstrained": r(row._10, 3), "long_only": r(row._9, 3)} for row in main.itertuples()]
assert list(main.columns)[8:10] == ["GMV long-only vol %", "GMV unconstrained vol %"]

# 5. the frontier
D["frontier"] = {v: {s: {"realised": r(roll[(roll.variant == v) & (roll.set == s)]["realised TE"].iloc[0] * 1e4, 4),
                         "forecast": r(roll[(roll.variant == v) & (roll.set == s)]["forecast TE (mean)"].iloc[0] * 1e4, 4)} for s in SETS} for v in VARIANTS}

# 6. bias by decade
dec_col = roll_dec.columns[1]
DECADES = list(dict.fromkeys(roll_dec[dec_col]))
D["decades"] = DECADES
D["bias_raw"] = {v: [r(roll_dec[(roll_dec.variant == v) & (roll_dec[dec_col] == d)]["realised / forecast"].iloc[0], 5) for d in DECADES] for v in VARIANTS}
cal_cols = [c for c in roll_cal.columns if c.startswith("calibrated bias, ")]
assert [c.replace("calibrated bias, ", "") for c in cal_cols] == DECADES
calset = roll_cal.set_index("variant")
D["bias_cal"] = {v: [r(calset.loc[v, c], 5) for c in cal_cols] for v in VARIANTS}
D["bias_all"] = {v: {"raw": r(calset.loc[v, "bias, 21 rule"], 5), "calibrated": r(calset.loc[v, "bias, calibrated"], 5)} for v in VARIANTS}

# 7. cumulative active return, by path
D["active"] = {"month": list(active.index)}
for s in ["C3", "C3 tilt only"]:
    D["active"][s] = {v: [r(x * 100, 4) for x in active[f"{v} | {s}"].cumsum()] for v in VARIANTS}

# 8. turnover and cost
c3 = roll[roll.set == "C3"].set_index("variant")
D["turn"] = {v: {"one_way": r(c3.loc[v, "turnover (one-way)"] * 100, 5), "cost50": r(c3.loc[v, "cost at 50 bp"] * 1e4, 4),
                 "gross": r(c3.loc[v, "active return (gross)"] * 1e4, 4), "net50": r(c3.loc[v, "net active return at 50 bp"] * 1e4, 4)} for v in VARIANTS}
D["bench_turn"] = r(c3["benchmark turnover"].iloc[0] * 100, 5)
bench_cost50 = c3["benchmark turnover"].iloc[0] * 0.005 * 12 * 1e4
# Table 1: the key figures under the mandate, one row per path, with the standard error from the attribution
att_c3 = att[att.set == "C3"].set_index("variant")
D["table1"] = [{"variant": v, "forecast": r(c3.loc[v, "forecast TE (mean)"] * 1e4, 4), "realised": r(c3.loc[v, "realised TE"] * 1e4, 4), "bias": r(c3.loc[v, "bias"], 5),
                "gross": r(c3.loc[v, "active return (gross)"] * 1e4, 4), "net50": r(c3.loc[v, "net active return at 50 bp"] * 1e4, 4), "se": r(att_c3.loc[v, "active return (standard error)"] * 1e4, 4),
                "turnover": r(c3.loc[v, "turnover (one-way)"] * 100, 5), "cost50": r(c3.loc[v, "cost at 50 bp"] * 1e4, 4), "held": r(c3.loc[v, "industries held"], 4)} for v in VARIANTS]

# 9. the attribution
D["att"] = {}
for s in ["C3", "C3 tilt only"]:
    sub = att[att.set == s].set_index("variant")
    D["att"][s] = {v: {"exposure": {f: r(sub.loc[v, f"exposure {f}"], 6) for f in FACTORS},
                       "contribution": {f: r(sub.loc[v, f"contribution {f} (per year)"] * 1e4, 4) for f in FACTORS},
                       "residual": r(sub.loc[v, "residual (per year)"] * 1e4, 4), "active": r(sub.loc[v, "active return (per year)"] * 1e4, 4),
                       "se": r(sub.loc[v, "active return (standard error)"] * 1e4, 4), "share": r(sub.loc[v, "factor share"], 5)} for v in VARIANTS}
D["att_dec"] = {"period": list(att_dec.iloc[:, 0]), "contribution": {f: [r(x * 1e4, 4) for x in att_dec[f"contribution {f}"]] for f in FACTORS},
                "residual": [r(x * 1e4, 4) for x in att_dec["residual"]], "active": [r(x * 1e4, 4) for x in att_dec["active return"]]}
mc = att_cost.set_index("variant")
D["att_cost"] = {v: {"active": r(mc.loc[v, "active return"] * 1e4, 4), "factor": r(mc.loc[v, "factor total"] * 1e4, 4), "residual": r(mc.loc[v, "residual"] * 1e4, 4),
                     "se": r(mc.loc[v, "active return (standard error)"] * 1e4, 4)} for v in VARIANTS}

# 10. the optimiser
D["opt_months"] = list(dict.fromkeys(opt_fixes["month"]))
OPT_VARIANT = {("sample", "daily_3y"): "sample, daily 3y", ("ledoit_wolf", "daily_3y"): "ledoit_wolf, daily 3y", ("factor", "daily_3y"): "factor, daily 3y",
               ("pca", "daily_3y"): "pca, daily 3y", ("sample", "monthly_120"): "sample, monthly 120"}
D["opt_fixes"] = [{"month": row.month, "estimator": EST_LABEL.get(row.estimator, row.estimator) + (" (120 months)" if row.data == "monthly_120" else ""),
                   "variant": OPT_VARIANT[(row.estimator, row.data)], "tilt": r(row._4, 3), "mandate": r(row._5, 3)} for row in opt_fixes.itertuples()]
assert list(opt_fixes.columns)[3:5] == ["tilt only (bp)", "mandate C3 (bp)"]
D["speed"] = {"rebalance": [int(x) for x in opt_speed["rebalance"]], "distance": [r(x * 100, 4) for x in opt_speed["one-way distance to the benchmark"]],
              "te": [r(x, 3) for x in opt_speed["forecast tracking error (bp a year)"]]}

# 11. the bias statistic by decade in both states (as forecast, calibrated), and the block-bootstrap band on the whole-period statistic
BSETS = ["C3", "C3 tilt only"]
bd = roll_bias_dec.set_index(["set", "variant"])
BIAS_DECADES = [c.replace("bias, 21 rule, ", "") for c in roll_bias_dec.columns if c.startswith("bias, 21 rule, ")]
assert [c.replace("bias, calibrated, ", "") for c in roll_bias_dec.columns if c.startswith("bias, calibrated, ")] == BIAS_DECADES == DECADES
D["bias_dec"] = {s: {"raw": {v: [r(bd.loc[(s, v), "bias, 21 rule"], 5)] + [r(bd.loc[(s, v), f"bias, 21 rule, {d}"], 5) for d in DECADES] for v in VARIANTS},
                     "cal": {v: [r(bd.loc[(s, v), "bias, calibrated"], 5)] + [r(bd.loc[(s, v), f"bias, calibrated, {d}"], 5) for d in DECADES] for v in VARIANTS}} for s in BSETS}
ds = roll_desc.set_index(["set", "variant"])
D["bias_band"] = {s: {"raw": {v: [r(ds.loc[(s, v), "bias"], 5), r(ds.loc[(s, v), "bias band low"], 5), r(ds.loc[(s, v), "bias band high"], 5)] for v in VARIANTS},
                      "cal": {v: [r(ds.loc[(s, v), "bias, calibrated"], 5), r(ds.loc[(s, v), "calibrated band low"], 5), r(ds.loc[(s, v), "calibrated band high"], 5)] for v in VARIANTS}} for s in BSETS}
for s in BSETS:
    for v in VARIANTS:
        assert abs(D["bias_band"][s]["raw"][v][0] - D["bias_dec"][s]["raw"][v][0]) < 1e-4 and abs(D["bias_band"][s]["cal"][v][0] - D["bias_dec"][s]["cal"][v][0]) < 1e-4
# the two descriptive figures of the active return, reported in no claim
D["desc"] = {s: {v: {"fall": r(ds.loc[(s, v), "worst cumulative fall"] * 1e4, 2), "peak": str(ds.loc[(s, v), "fall peak"]), "trough": str(ds.loc[(s, v), "fall trough"]),
                     "months": int(ds.loc[(s, v), "fall months"]), "positive": r(ds.loc[(s, v), "share of positive months"], 5)} for v in VARIANTS} for s in BSETS}

# 12. the realised tracking error over the 36 months ending in each month, beside the mean forecast over the same months
WINDOW = len(active) - len(roll_te) + 1
assert WINDOW == 36 and list(roll_te.index) == list(active.index[WINDOW - 1:]) and list(fc_te.index) == list(active.index)
fc_roll = fc_te.rolling(WINDOW).mean().iloc[WINDOW - 1:]
D["rolling"] = {"window": WINDOW, "month": list(roll_te.index), "median": {s: [r(x * 1e4, 2) for x in roll_te[f"median of seven | {s}"]] for s in BSETS}}
for s in BSETS:
    D["rolling"][s] = {v: {"realised": [r(x * 1e4, 2) for x in roll_te[f"{v} | {s}"]], "forecast": [r(x * 1e4, 2) for x in fc_roll[f"{v} | {s}"]]} for v in VARIANTS}

# 13. the weights of the last month, every path under the mandate and under the tilt alone, against the benchmark's
INDUSTRIES = list(roll_w.columns)
assert len(INDUSTRIES) == 49 and "benchmark" in roll_w.index
D["weights"] = {"industries": INDUSTRIES, "benchmark": [r(x * 100, 4) for x in roll_w.loc["benchmark"]], "excluded": ["Smoke", "Guns"]}
for s in BSETS:
    D["weights"][s] = {v: [r(x * 100, 4) for x in roll_w.loc[f"{v} | {s}"]] for v in VARIANTS}

# 14. version 2, module A: the nineteen paths of the factor objective (notebooks 15 and 16)
FO_PATHS = list(fo_eval.index)
assert FO_PATHS == list(fo_att.index) == list(fo_bought.index) == list(fo_gap.index) and len(FO_PATHS) == 19
BUDGETS = sorted(set(int(b) for b in fo_eval["budget (bp)"]))
assert BUDGETS == [75, 100, 150]
TARGETED = ["HML", "RMW", "CMA", "Mom"]
FO_VLABEL = dict(VLABEL)
FO_VLABEL.update({"sample, daily 3y, value alone": "Sample, 3y daily, value alone", "sample, daily 3y, momentum alone": "Sample, 3y daily, momentum alone"})
FO_VSHORT = dict(VSHORT)
FO_VSHORT.update({"sample, daily 3y, value alone": "Value alone", "sample, daily 3y, momentum alone": "Momentum alone"})
D["fo"] = {"budgets": BUDGETS, "targeted": TARGETED, "vlabel": FO_VLABEL, "vshort": FO_VSHORT, "paths": []}
for p in FO_PATHS:
    e, a, b, g = fo_eval.loc[p], fo_att.loc[p], fo_bought.loc[p], fo_gap.loc[p]
    v = p.split(" | ")[0]   # the estimator, with "value alone" or "momentum alone" appended on the two single-factor paths
    assert v in FO_VLABEL and v.startswith(e["variant"]) and a["variant"] == e["variant"] and int(a["budget (bp)"]) == int(e["budget (bp)"])
    D["fo"]["paths"].append({
        "path": p, "variant": v, "budget": int(e["budget (bp)"]), "main": v in VARIANTS[:5], "target": e["target"],
        "realised": r(e["realised TE"] * 1e4, 4), "forecast": r(e["forecast TE (mean)"] * 1e4, 4), "bias": r(e["bias"], 5), "ratio": r(e["realised over budget"], 5),
        "gross": r(e["active return (gross)"] * 1e4, 4), "se": r(e["standard error of the gross active return"] * 1e4, 4),
        "cost50": r(e["cost at 50 bp"] * 1e4, 4), "net50": r(e["net active return at 50 bp"] * 1e4, 4), "turnover": r(e["turnover (one-way)"] * 100, 5),
        "cap_binds": int(e["cap binds months"]), "budget_binds": int(e["budget binds months"]), "not_met": int(e["budget not met months"]),
        "objective": r(e["mean objective"], 6), "exposure": {f: r(e[f"mean exposure {f}"], 6) for f in TARGETED}, "four": r(sum(e[f"mean exposure {f}"] for f in TARGETED), 6), "per_bp": r(e["exposure per bp of realised TE"], 7),
        "contribution": {f: r(a[f"contribution {f} (per year)"] * 1e4, 4) for f in FACTORS}, "residual": r(a["residual (per year)"] * 1e4, 4),
        "active": r(a["active return (per year)"] * 1e4, 4), "active_se": r(a["active return (standard error)"] * 1e4, 4),
        "targeted_total": r(a["targeted total (per year)"] * 1e4, 4), "targeted_se": r(a["targeted total (standard error)"] * 1e4, 4), "share": r(a["factor share"], 5),
        "var_factor": r(a["factor total variance share"], 5), "var_residual": r(a["residual variance share"], 5), "var_cov": r(a["covariance share"], 5),
        "bought": {f: r(b[FLABEL[f]], 7) for f in TARGETED}, "bought_total": r(b["total"], 7), "gap": r(g["mean absolute gap"], 6), "gap_per_unit": r(g["gap per unit"], 5)})
    assert abs(sum(D["fo"]["paths"][-1]["bought"].values()) - D["fo"]["paths"][-1]["bought_total"]) < 2e-6
verd = fo_verd.set_index("expectation")
verd16 = fo_verd16.set_index("expectation")
assert verd.loc["E4", "verdict"] == "notebook 16" and set(verd16.index) == {"E4"}
def detail_words(text):
    """A path's code label inside a verdict's text becomes its name, with the measure the clause is about."""
    for p in FO_PATHS:
        if p in text:
            v = p.split(" | ")[0]
            name = FO_VLABEL[v][0].lower() + FO_VLABEL[v][1:]
            name = name.replace("sample, ", "sample covariance, ", 1)
            text = text.replace("worst calibrated " + p, f"worst calibrated: the {name} ({fo_eval.loc[p, 'bias']:.2f})").replace(p, name)
    return text
D["fo"]["verdicts"] = [{"expectation": x, "verdict": str((verd16 if x == "E4" else verd).loc[x, "verdict"]), "detail": detail_words(str((verd16 if x == "E4" else verd).loc[x, "detail"]))} for x in ["E1", "E2", "E3", "E4", "E5", "E6", "E7"]]
FO = {q["path"]: q for q in D["fo"]["paths"]}
FO_MAIN = [p for p in FO_PATHS if FO[p]["main"]]
assert len(FO_MAIN) == 15

# --- the prose numbers ---
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def words(ym):
    """'1979-07' as 'July 1979', for prose and captions; tables and axes keep the ISO form."""
    y, m = ym.split("-")
    return f"{MONTH_NAMES[int(m) - 1]} {int(y)}"


def signed(x, d):
    """A display number with the true minus sign and a plus sign on positive values, for active figures."""
    v = round(float(x), d)
    if v == 0:
        return f"{0:.{d}f}"
    return ("+" if v > 0 else "\u2212") + f"{abs(v):.{d}f}"


P = {}
P["vintage"] = V
P["months"] = str(MONTHS)
P["first"] = FIRST
P["last"] = LAST
P["first_w"] = words(FIRST)
P["last_w"] = words(LAST)
P["gated_pass"] = str(int((gated.verdict == "pass").sum()))
P["gated_n"] = str(len(gated))
P["turn_pass"] = str(int((gated_t.verdict == "pass").sum()))
P["turn_n"] = str(len(gated_t))
new_lo, new_hi = re.search(r"\((\d{4}-\d{2}) to (\d{4}-\d{2})\)", periods[1]).groups()
P["new_months"] = str((pd.Period(new_hi, "M") - pd.Period(new_lo, "M")).n + 1)
P["new_lo"], P["new_hi"] = new_lo, new_hi
P["new_lo_w"], P["new_hi_w"] = words(new_lo), words(new_hi)
paper_lo, paper_hi = re.search(r"\((\d{4}-\d{2}) to (\d{4}-\d{2})\)", periods[0]).groups()
P["paper_lo"], P["paper_hi"] = paper_lo, paper_hi
P["paper_lo_w"], P["paper_hi_w"] = words(paper_lo), words(paper_hi)
P["beats"] = str(int(ext_vs["beats 1/N at 5%"].sum()))
P["cells"] = str(len(ext_vs))
P["bench_te"] = f"{gap.std() * np.sqrt(12) * 1e4:.1f}"
P["gap_share"] = f"{direct['expectation_2_predicted_vs_observed']['share_of_variance_explained'] * 100:.0f}"
P["bench_months"] = str(len(bench))
P["bench_first"] = bench.index[0]
P["bench_first_w"] = words(bench.index[0])
te_c3 = {v: roll[(roll.variant == v) & (roll.set == "C3")]["realised TE"].iloc[0] * 1e4 for v in VARIANTS}
daily4 = [te_c3[v] for v in VARIANTS[:4]]
P["te_lo"] = f"{min(daily4):.1f}"
P["te_hi"] = f"{max(daily4):.1f}"
P["te_monthly"] = f"{te_c3['sample, monthly 120']:.1f}"
P["te_range"] = f"{max(daily4) - min(daily4):.1f}"
c2 = [roll[(roll.variant == v) & (roll.set == "C2")]["realised TE"].iloc[0] * 1e4 for v in VARIANTS]
tilt_te = [roll[(roll.variant == v) & (roll.set == "C3 tilt only")]["realised TE"].iloc[0] * 1e4 for v in VARIANTS]
c3_add = [te_c3[v] - roll[(roll.variant == v) & (roll.set == "C3 tilt only")]["realised TE"].iloc[0] * 1e4 for v in VARIANTS]
assert min(c3_add) > 0
P["c2_lo"], P["c2_hi"] = f"{min(c2):.1f}", f"{max(c2):.1f}"
P["tilt_te_lo"], P["tilt_te_hi"] = f"{min(tilt_te):.1f}", f"{max(tilt_te):.1f}"
P["c3_add_lo"], P["c3_add_hi"] = f"{min(c3_add):.1f}", f"{max(c3_add):.1f}"
gross_c3 = [c3.loc[v, "active return (gross)"] * 1e4 for v in VARIANTS]
P["gross_lo"], P["gross_hi"] = signed(min(gross_c3), 1), signed(max(gross_c3), 1)
bias_c3 = [roll[(roll.variant == v) & (roll.set == "C3")]["bias"].iloc[0] for v in VARIANTS[:4]]
P["bias_lo"] = f"{min(bias_c3):.2f}"
P["bias_hi"] = f"{max(bias_c3):.2f}"
bias_monthly = roll[(roll.variant == 'sample, monthly 120') & (roll.set == 'C3')]['bias'].iloc[0]
P["bias_monthly"] = f"{bias_monthly:.2f}"
P["bias_pct_lo"] = f"{(min(bias_c3) - 1) * 100:.0f}"
P["bias_pct_hi"] = f"{(max(bias_c3 + [bias_monthly]) - 1) * 100:.0f}"
cal4 = [calset.loc[v, "bias, calibrated"] for v in VARIANTS[:4]]
P["cal_lo"] = f"{min(cal4):.2f}"
P["cal_hi"] = f"{max(cal4):.2f}"
att_tilt = att[att.set == "C3 tilt only"].set_index("variant")
tilt_gross = [att_tilt.loc[v, "active return (per year)"] * 1e4 for v in VARIANTS]
tilt_se = [att_tilt.loc[v, "active return (standard error)"] * 1e4 for v in VARIANTS]
P["tilt_lo"] = signed(min(tilt_gross), 0)
P["tilt_hi"] = signed(max(tilt_gross), 0)
P["tilt_se_lo"] = f"{min(tilt_se):.0f}"
P["tilt_se_hi"] = f"{max(tilt_se):.0f}"
cost = [mc.loc[v, "active return"] * 1e4 for v in VARIANTS]   # the mandate minus the tilt alone, negative on every path
assert max(cost) < 0
P["mandate_lo"] = f"{-max(cost):.0f}"   # a cost is written as a positive number
P["mandate_hi"] = f"{-min(cost):.0f}"
ftot = [sum(att_tilt.loc[v, f"contribution {f} (per year)"] for f in FACTORS) * 1e4 for v in VARIANTS]
assert max(ftot) < 0
res = [att_tilt.loc[v, "residual (per year)"] * 1e4 for v in VARIANTS]
P["factor_lo"] = f"{-max(ftot):.0f}"
P["factor_hi"] = f"{-min(ftot):.0f}"
P["resid_lo"] = f"{min(res):.0f}"
P["resid_hi"] = f"{max(res):.0f}"
shares = list(att["factor share"])
P["share_lo"] = f"{min(shares) * 100:.0f}"
P["share_hi"] = f"{max(shares) * 100:.0f}"
P["turn_lo"] = f"{c3['turnover (one-way)'].min() * 100:.2f}"
P["turn_hi"] = f"{c3['turnover (one-way)'].max() * 100:.2f}"
P["bench_turn"] = f"{c3['benchmark turnover'].iloc[0] * 100:.2f}"
P["cost_lo"] = f"{c3['cost at 50 bp'].min() * 1e4:.1f}"
P["cost_hi"] = f"{c3['cost at 50 bp'].max() * 1e4:.1f}"
P["bench_cost"] = f"{bench_cost50:.1f}"
# the speed limit: the distance before the first rebalance is the first row's distance plus the cap it traded
cap = opt_speed["one-way turnover"].iloc[0]
assert (opt_speed["one-way turnover"] == cap).all()
P["speed_months"] = str(int(opt_speed["rebalance"].max()))
P["speed_cap"] = f"{cap * 100:.0f}"
P["speed_start"] = f"{opt_speed['one-way distance to the benchmark'].iloc[0] + cap:.2f}"
P["speed_te_first"] = f"{opt_speed['forecast tracking error (bp a year)'].iloc[0]:.0f}"
P["speed_te_last"] = f"{opt_speed['forecast tracking error (bp a year)'].iloc[-1]:.0f}"
P["speed_left"] = f"{opt_speed['one-way distance to the benchmark'].iloc[-1]:.2f}"
last_month, first_month = opt_fixes["month"].iloc[-1], opt_fixes["month"].iloc[0]
tilt_last = opt_fixes[(opt_fixes.month == last_month) & (opt_fixes.data != "monthly_120")]["tilt only (bp)"]
P["tilt_cost_last"] = f"{tilt_last.min():.0f} to {tilt_last.max():.0f}"
P["last_opt_month"] = last_month
P["first_opt_month"] = first_month
P["last_opt_month_w"], P["first_opt_month_w"] = words(last_month), words(first_month)
opt_w = [words(m) for m in D["opt_months"]]
P["opt_months_w"] = ", ".join(opt_w[:-1]) + " and " + opt_w[-1]
P["oil_first"] = f"{bench_w.loc[FIRST, 'Oil'] * 100:.1f}"   # Oil's share at the first optimiser month
P["oil_last"] = f"{bench_w['Oil'].iloc[-1] * 100:.1f}"
P["tilt_cost_first"] = f"{opt_fixes[opt_fixes.month == first_month]['tilt only (bp)'].max():.0f}"
mo = main[main.data == "monthly_120"].set_index("estimator")
P["gmv_sample"] = f"{mo.loc['sample', 'GMV unconstrained vol %']:.1f}"
P["gmv_lo"] = f"{mo.drop('sample')['GMV unconstrained vol %'].min():.1f}"
P["gmv_hi"] = f"{mo.drop('sample')['GMV unconstrained vol %'].max():.1f}"
P["lo_lo"] = f"{main['GMV long-only vol %'].min():.1f}"
P["lo_hi"] = f"{main['GMV long-only vol %'].max():.1f}"
P["build_date"] = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam")).strftime("%-d %B %Y")
P["top_ind"] = ", ".join(top_ind)
tilted_in_top = [{"Util": "Utilities"}.get(i, i) for i in top_ind if i in D["tilted"]]   # French's label, written out in prose
P["tilted_in_top"] = (", ".join(tilted_in_top[:-1]) + " and " + tilted_in_top[-1] if len(tilted_in_top) > 1 else tilted_in_top[0]) + " are " + \
                     {1: "one", 2: "two", 3: "three"}[len(tilted_in_top)] + " of the three industries" if tilted_in_top else "none of the three industries"

# the prose numbers of the additions of 18 October and 6 and 8 November 2026 (version 1), and of version 2, module A
WORDS = ["none", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
def word(n, of=None):
    """A count under ten as a word; a count equal to its total as 'all <total>'."""
    n = int(n)
    if of is not None and n == of:
        return "all " + WORDS[of]
    return WORDS[n] if n < 10 else str(n)


# The one cell that earns a higher Sharpe ratio than 1/N at the 5 per cent level in the new period is the
# value-weighted market, which is not an optimising rule; the sentence of the page names it from the table
# and holds only while no optimising rule's cell does, which the assertions check.
_opt = [r for r in RULES if r not in ("ew", "vw")]
_beat = ext_vs[ext_vs["beats 1/N at 5%"]]
assert len(_opt) == 7 and len(_beat) == 1 and _beat["rule"].iloc[0] == "vw" and ext_vs["dataset"].nunique() == 4
assert not _beat["rule"].isin(_opt).any()
P["opt_rules_w"] = word(len(_opt))
P["datasets_w"] = word(ext_vs["dataset"].nunique())
P["beat_cell"] = f"the {RULE_LABEL[_beat['rule'].iloc[0]]} on {_beat['dataset'].iloc[0]}"


def lohi(xs, d, sign=False):
    f = (lambda x: signed(x, d)) if sign else (lambda x: f"{x:.{d}f}")
    return f(min(xs)), f(max(xs))


falls = [D["desc"]["C3"][v]["fall"] for v in VARIANTS]
P["fall_lo"], P["fall_hi"] = lohi(falls, 0)
fall_months = [D["desc"]["C3"][v]["months"] for v in VARIANTS]
def span(m):
    return f"{m} months" if m < 24 else f"{m / 12:.0f} years"
P["fall_span_lo"], P["fall_span_hi"] = span(min(fall_months)), span(max(fall_months))
P["positive_lo"], P["positive_hi"] = lohi([D["desc"]["C3"][v]["positive"] for v in VARIANTS], 2)
troughs = [D["desc"]["C3"][v]["trough"] for v in VARIANTS]
P["trough_common"] = words(max(set(troughs), key=troughs.count))
P["trough_count_w"] = word(troughs.count(max(set(troughs), key=troughs.count)))
P["bands_without_one_w"] = word(sum(1 for v in VARIANTS if D["bias_band"]["C3"]["raw"][v][1] > 1))
P["bands_cal_with_one_w"] = word(sum(1 for v in VARIANTS if D["bias_band"]["C3"]["cal"][v][1] <= 1 <= D["bias_band"]["C3"]["cal"][v][2]), of=len(VARIANTS))
P["bias_decade_first_lo"], P["bias_decade_first_hi"] = lohi([D["bias_dec"]["C3"]["raw"][v][1] for v in VARIANTS[:4]], 2)
P["bias_decade_cal_first_lo"], P["bias_decade_cal_first_hi"] = lohi([D["bias_dec"]["C3"]["cal"][v][1] for v in VARIANTS[:4]], 2)
P["bias_first_decade"] = DECADES[0].replace(" to ", " to ")
robust_band = D["bias_band"]["C3"]["raw"]["robust, all five"]
P["robust_band_lo"], P["robust_band_hi"] = f"{robust_band[1]:.2f}", f"{robust_band[2]:.2f}"
sample_band = D["bias_band"]["C3"]["raw"]["sample, daily 3y"]
P["sample_band_lo"], P["sample_band_hi"] = f"{sample_band[1]:.2f}", f"{sample_band[2]:.2f}"
P["window"] = str(WINDOW)
med = roll_te["median of seven | C3"] * 1e4
P["roll_max"], P["roll_max_w"], P["roll_last"] = f"{med.max():.0f}", words(med.idxmax()), f"{med.iloc[-1]:.0f}"
P["roll_min"], P["roll_min_w"] = f"{med.min():.0f}", words(med.idxmin())
med_t = roll_te["median of seven | C3 tilt only"] * 1e4
P["roll_tilt_max"], P["roll_tilt_last"] = f"{med_t.max():.0f}", f"{med_t.iloc[-1]:.0f}"
below = [(roll_te[f"{v} | C3"] > fc_roll[f"{v} | C3"]).mean() * 100 for v in VARIANTS]
P["roll_below_lo"], P["roll_below_hi"] = f"{min(below):.0f}", f"{max(below):.0f}"
P["roll_first"], P["roll_first_w"] = roll_te.index[0], words(roll_te.index[0])
sw = roll_w.loc["sample, daily 3y | C3"] - roll_w.loc["benchmark"]
P["w_sample_bound"] = str(int((sw.abs() >= 0.0199).sum()))
P["w_sample_over"] = sw.idxmax()
P["w_sample_over_pp"] = f"{sw.max() * 100:.1f}"
P["w_sample_held"] = str(int((roll_w.loc["sample, daily 3y | C3"] > 1e-6).sum()))
P["w_oil_bench"] = f"{roll_w.loc['benchmark', 'Oil'] * 100:.1f}"
P["w_oil_sample"] = f"{roll_w.loc['sample, daily 3y | C3', 'Oil'] * 100:.1f}"
P["w_util_bench"] = f"{roll_w.loc['benchmark', 'Util'] * 100:.1f}"
P["w_util_sample"] = f"{roll_w.loc['sample, daily 3y | C3', 'Util'] * 100:.1f}"

# version 2, module A
main100 = [p for p in FO_MAIN if FO[p]["budget"] == 100]
main150 = [p for p in FO_MAIN if FO[p]["budget"] == 150]
main75 = [p for p in FO_MAIN if FO[p]["budget"] == 75]
daily100 = [p for p in main100 if FO[p]["variant"] in VARIANTS[:4]]
monthly = {b: f"sample, monthly 120 | {b}" for b in BUDGETS}
P["fo_paths"] = str(len(FO_PATHS))
P["fo_budgets"] = ", ".join(str(b) for b in BUDGETS[:-1]) + " or " + str(BUDGETS[-1])
P["fo_te_lo"], P["fo_te_hi"] = lohi([FO[p]["realised"] for p in daily100], 1)
P["fo_te_monthly"] = f"{FO[monthly[100]]['realised']:.1f}"
P["fo_spread"] = f"{max(FO[p]['realised'] for p in daily100) - min(FO[p]['realised'] for p in daily100):.1f}"
P["fo_ratio_lo"], P["fo_ratio_hi"] = lohi([FO[p]["ratio"] for p in daily100], 2)
P["fo_ratio_monthly"] = f"{FO[monthly[100]]['ratio']:.2f}"
daily_all = [p for p in FO_MAIN if FO[p]["variant"] in VARIANTS[:4]]
P["fo_ratio_daily_lo"], P["fo_ratio_daily_hi"] = lohi([FO[p]["ratio"] for p in daily_all], 2)
P["fo_ratio_inside"] = str(sum(1 for p in daily_all if 1.2 <= FO[p]["ratio"] <= 1.6))
P["fo_ratio_cells"] = str(len(daily_all))
P["fo_ratio_monthly_lo"], P["fo_ratio_monthly_hi"] = lohi([FO[monthly[b]]["ratio"] for b in BUDGETS], 2)
P["fo_robust_te"] = f"{FO['robust, all five | 100']['realised']:.1f}"
P["fo_robust_bias"] = f"{FO['robust, all five | 100']['bias']:.2f}"
P["fo_monthly_bias"] = f"{FO[monthly[100]]['bias']:.2f}"
P["fo_monthly_bias150"] = f"{FO[monthly[150]]['bias']:.2f}"
P["fo_factor_bias150"] = f"{FO['factor, daily 3y | 150']['bias']:.2f}"
P["fo_bias_daily_lo"], P["fo_bias_daily_hi"] = lohi([FO[p]["bias"] for p in daily100], 2)
assert FO[monthly[75]]["bias"] > max(FO[f"{v} | 75"]["bias"] for v in VARIANTS[:4]) and FO[monthly[100]]["bias"] > max(FO[p]["bias"] for p in daily100) and FO[monthly[150]]["bias"] < FO["factor, daily 3y | 150"]["bias"]
P["fo_obj_lo"], P["fo_obj_hi"] = lohi([FO[p]["objective"] for p in main100], 3)
P["fo_obj150_lo"], P["fo_obj150_hi"] = lohi([FO[p]["objective"] for p in main150], 3)
P["fo_obj75_lo"], P["fo_obj75_hi"] = lohi([FO[p]["objective"] for p in main75], 3)
for f, wd in [("HML", "value"), ("RMW", "prof"), ("CMA", "inv"), ("Mom", "mom")]:
    P[f"fo_{wd}_lo"], P[f"fo_{wd}_hi"] = lohi([FO[p]["exposure"][f] for p in main100], 3, sign=True)
    P[f"fo_bought_{wd}_lo"], P[f"fo_bought_{wd}_hi"] = lohi([FO[p]["bought"][f] for p in main100], 5)
P["fo_sample_avg"] = f"{FO['sample, daily 3y | 100']['objective'] / 4:.4f}"
P["fo_perbp_lo"], P["fo_perbp_hi"] = lohi([FO[p]["per_bp"] for p in main100], 5)
perbp4 = [FO[p]["per_bp"] for p in daily100]
P["fo_perbp_pct"] = f"{(max(perbp4) - min(perbp4)) / np.mean(perbp4) * 100:.1f}"
P["fo_value_alone_value"] = f"{FO['sample, daily 3y, value alone | 100']['bought']['HML']:.5f}"
P["fo_value_alone_inv"] = f"{FO['sample, daily 3y, value alone | 100']['bought']['CMA']:.5f}"
P["fo_mom_alone_mom"] = f"{FO['sample, daily 3y, momentum alone | 100']['bought']['Mom']:.5f}"
P["fo_mom_alone_total"] = f"{FO['sample, daily 3y, momentum alone | 100']['bought_total']:.5f}"
P["fo_gross_lo"], P["fo_gross_hi"] = lohi([FO[p]["gross"] for p in main100], 1, sign=True)
P["fo_se_lo"], P["fo_se_hi"] = lohi([FO[p]["se"] for p in main100], 0)
P["fo_gross150_lo"], P["fo_gross150_hi"] = lohi([FO[p]["gross"] for p in main150], 1, sign=True)
P["fo_se150_lo"], P["fo_se150_hi"] = lohi([FO[p]["se"] for p in main150], 0)
P["fo_gross75_lo"], P["fo_gross75_hi"] = lohi([FO[p]["gross"] for p in main75], 1, sign=True)
P["fo_se75_lo"], P["fo_se75_hi"] = lohi([FO[p]["se"] for p in main75], 0)
P["fo_cost_lo"], P["fo_cost_hi"] = lohi([FO[p]["cost50"] for p in main100], 1)
P["fo_net_lo"], P["fo_net_hi"] = lohi([FO[p]["net50"] for p in main100], 1, sign=True)
P["fo_turn_lo"], P["fo_turn_hi"] = lohi([FO[p]["turnover"] for p in main100], 2)
P["fo_cap_lo"], P["fo_cap_hi"] = str(min(FO[p]["cap_binds"] for p in main100)), str(max(FO[p]["cap_binds"] for p in main100))
P["fo_positive"] = str(sum(1 for p in main100 if FO[p]["gross"] > 0))
ratios = {p: abs(FO[p]["active"]) / FO[p]["active_se"] for p in FO_PATHS}
P["fo_largest_ratio"] = f"{max(ratios.values()):.2f}"
P["fo_largest_ratio_path"] = FO_VLABEL[FO[max(ratios, key=ratios.get)]["variant"]] + f" at {FO[max(ratios, key=ratios.get)]['budget']}"
P["fo_beyond_two"] = str(sum(1 for x in ratios.values() if x > 2))
P["fo_tt_lo"], P["fo_tt_hi"] = lohi([FO[p]["targeted_total"] for p in main100], 1, sign=True)
P["fo_tt150_lo"], P["fo_tt150_hi"] = lohi([FO[p]["targeted_total"] for p in main150], 1, sign=True)
P["fo_tt75_lo"], P["fo_tt75_hi"] = lohi([FO[p]["targeted_total"] for p in main75], 1, sign=True)
P["fo_tt_se_lo"], P["fo_tt_se_hi"] = lohi([FO[p]["targeted_se"] for p in main100 + main150], 0)
P["fo_tt_se100_lo"], P["fo_tt_se100_hi"] = lohi([FO[p]["targeted_se"] for p in main100], 0)
P["fo_tt_beyond"] = str(sum(1 for p in FO_MAIN if FO[p]["targeted_total"] / FO[p]["targeted_se"] > 2))
P["fo_tt_positive"] = str(sum(1 for p in FO_MAIN if FO[p]["targeted_total"] > 0))
P["fo_main"] = str(len(FO_MAIN))
P["fo_tt_all_lo"], P["fo_tt_all_hi"] = lohi([FO[p]["targeted_total"] for p in FO_MAIN], 1, sign=True)
share10 = [FO[p]["share"] for p in main100 + main150]
P["fo_share_lo"], P["fo_share_hi"] = lohi(share10, 2)
P["fo_share_above"] = str(sum(1 for x in share10 if x >= 0.30))
P["fo_varf_lo"], P["fo_varf_hi"] = lohi([FO[p]["var_factor"] * 100 for p in main100 + main150], 0)
P["fo_varr_lo"], P["fo_varr_hi"] = lohi([FO[p]["var_residual"] * 100 for p in main100 + main150], 0)
P["fo_varc_lo"], P["fo_varc_hi"] = lohi([-FO[p]["var_cov"] * 100 for p in main100 + main150], 0)
ftot100 = [sum(FO[p]["contribution"].values()) for p in main100]
P["fo_factor_lo"], P["fo_factor_hi"] = lohi(ftot100, 0, sign=True)
P["fo_resid_back_lo"], P["fo_resid_back_hi"] = lohi([-FO[p]["residual"] for p in main100], 0)
P["fo_resid_lo"], P["fo_resid_hi"] = lohi([FO[p]["residual"] for p in FO_PATHS], 0, sign=True)
assert max(FO[p]["residual"] for p in FO_PATHS) < 0
P["fo_mkt_lo"], P["fo_mkt_hi"] = lohi([fo_att.loc[p, "exposure Mkt-RF"] for p in daily100], 3)
P["fo_mkt_monthly"] = f"{fo_att.loc[monthly[100], 'exposure Mkt-RF']:.3f}"
P["fo_mkt_c_lo"], P["fo_mkt_c_hi"] = lohi([FO[p]["contribution"]["Mkt-RF"] for p in daily100], 1, sign=True)
P["fo_mkt_se_lo"], P["fo_mkt_se_hi"] = lohi([fo_att.loc[p, "contribution Mkt-RF (standard error)"] * 1e4 for p in daily100], 1)
P["fo_smb_c_lo"], P["fo_smb_c_hi"] = lohi([FO[p]["contribution"]["SMB"] for p in main100], 1, sign=True)
P["v1_mkt_abs_max"] = f"{max(abs(att_c3.loc[v, 'exposure Mkt-RF']) for v in VARIANTS[:4]):.4f}"
P["fo_gap_lo"], P["fo_gap_hi"] = lohi([FO[p]["gap_per_unit"] for p in main100], 3)
P["fo_gap150_lo"], P["fo_gap150_hi"] = lohi([FO[p]["gap_per_unit"] for p in main150], 3)
P["fo_gap75_lo"], P["fo_gap75_hi"] = lohi([FO[p]["gap_per_unit"] for p in main75], 3)
P["fo_gap_val"] = f"{FO['sample, daily 3y, value alone | 100']['gap']:.5f}"
P["fo_gap_mom"] = f"{FO['sample, daily 3y, momentum alone | 100']['gap']:.5f}"
P["fo_gpu_val"] = f"{FO['sample, daily 3y, value alone | 100']['gap_per_unit']:.3f}"
P["fo_gpu_mom"] = f"{FO['sample, daily 3y, momentum alone | 100']['gap_per_unit']:.3f}"
fo_met = sum(1 for q in D["fo"]["verdicts"] if q["verdict"] == "MET")
fo_not_met = sum(1 for q in D["fo"]["verdicts"] if q["verdict"] == "NOT MET")
assert fo_met + fo_not_met == 7
P["fo_met_w"], P["fo_not_met_w"] = word(fo_met), word(fo_not_met)
bm = fo_bm.set_index("path")
P["fo_e1_lo"], P["fo_e1_hi"] = lohi([bm.loc[p, "E1 share"] * 100 for p in daily100], 1)
P["fo_e1_cannot_lo"], P["fo_e1_cannot_hi"] = str(int(min(bm.loc[p, "mandate alone cannot meet"] for p in daily100))), str(int(max(bm.loc[p, "mandate alone cannot meet"] for p in daily100)))
P["fo_e1_further_lo"], P["fo_e1_further_hi"] = str(int(min(bm.loc[p, "path further misses"] for p in daily100))), str(int(max(bm.loc[p, "path further misses"] for p in daily100)))
# --- the static figures ---
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "path", "figure.dpi": 100, "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": FRAME,
                     "xtick.color": META, "ytick.color": META, "xtick.labelcolor": META, "ytick.labelcolor": META,
                     "svg.hashsalt": "B-P"})  # fixed element ids, so a rebuild from the same files is byte-identical
# svg.fonttype "path" draws the text as outlines, so the figures look the same on every machine
os.makedirs(FIG_DIR, exist_ok=True)

# Figure 1: realised tracking error by constraint set and covariance estimate, with the forecast as hollow markers
first3 = roll[roll.set.isin(SETS[:3])]["realised TE"] * 1e4
lo3, hi3 = first3.min(), first3.max()
fig, ax = plt.subplots(figsize=(8.2, 4.4))
x = np.arange(len(SETS))
for v in VARIANTS:
    ys = [D["frontier"][v][s]["realised"] for s in SETS]
    fs = [D["frontier"][v][s]["forecast"] for s in SETS]
    ax.plot(x, ys, "-o", color=VCOLOUR[v], label=VLABEL[v], lw=1.4, ms=4.5)
    ax.plot(x, fs, "o", mfc="white", mec=VCOLOUR[v], ms=4.5, lw=0)
ax.set_xticks(x)
ax.set_xticklabels(["long-only", "+ active weight\nbound", "+ turnover cap", "+ tilt", "+ exclusions,\nbeta neutrality"])
ax.set_ylabel("tracking error, basis points a year")
ax.set_title(f"Realised (filled) and forecast (hollow) tracking error by constraint set, {words(FIRST)} to {words(LAST)}", loc="left", fontsize=9.5, color=INK)
ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
ax.grid(axis="y", lw=0.6, color=GRID)
fig.text(0.01, 0.035, "Source: Kenneth R. French Data Library and author's calculations.", fontsize=7.2, color=META)
fig.text(0.01, 0.005, f"results/{V}/rolling_evaluation_{V}.csv (notebook 12), {MONTHS} months; the first three sets realise {lo3:.0f} to {hi3:.1f} basis points.", fontsize=7.2, color=META)
fig.tight_layout(rect=(0, 0.06, 1, 1))
fig.savefig(os.path.join(FIG_DIR, "fig_tracking_error.svg"), metadata={"Creator": None, "Date": None})
plt.close(fig)

# Figure 2: the attribution of the active return, tilt alone and mandate, contributions and residual
fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.6), sharey=True)
for ax, s, title in zip(axes, ["C3 tilt only", "C3"], ["Under the tilt alone", "Under the mandate"]):
    y = np.arange(len(VARIANTS))
    left_pos = np.zeros(len(VARIANTS))
    left_neg = np.zeros(len(VARIANTS))
    for f in FACTORS:
        vals = np.array([D["att"][s][v]["contribution"][f] for v in VARIANTS])
        pos = np.where(vals > 0, vals, 0)
        neg = np.where(vals < 0, vals, 0)
        ax.barh(y, pos, left=left_pos, color=FCOLOUR[f], height=0.62, edgecolor="white", linewidth=0.6, label=FLABEL[f])
        ax.barh(y, neg, left=left_neg, color=FCOLOUR[f], height=0.62, edgecolor="white", linewidth=0.6)
        left_pos += pos
        left_neg += neg
    resid = np.array([D["att"][s][v]["residual"] for v in VARIANTS])
    ax.barh(y, np.where(resid > 0, resid, 0), left=left_pos, color=RESID_COLOUR, height=0.62, edgecolor="white", linewidth=0.6, label="residual (the industries' own returns)")
    ax.barh(y, np.where(resid < 0, resid, 0), left=left_neg, color=RESID_COLOUR, height=0.62, edgecolor="white", linewidth=0.6)
    tot = np.array([D["att"][s][v]["active"] for v in VARIANTS])
    ax.plot(tot, y, "|", color=INK, ms=11, mew=1.6, label="active return")
    ax.axvline(0, color=FRAME, lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([VLABEL[v] for v in VARIANTS])
    ax.set_title(title, loc="left", fontsize=9.5)
    ax.set_xlabel("basis points a year")
    ax.set_xlim(-26, 26)
    ax.grid(axis="x", lw=0.6, color=GRID)
axes[0].invert_yaxis()
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, fontsize=7.5, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.04))
fig.text(0.01, 0.03, "Source: Kenneth R. French Data Library and author's calculations.", fontsize=7.2, color=META)
fig.text(0.01, 0.005, f"results/{V}/attribution_summary_{V}.csv (notebook 13). The mark is the active return, the sum of the bars.", fontsize=7.2, color=META)
fig.tight_layout(rect=(0, 0.13, 1, 1))
fig.savefig(os.path.join(FIG_DIR, "fig_attribution.svg"), metadata={"Creator": None, "Date": None})
plt.close(fig)

# Figure 3: version 2, module A. Left: the factor objective bought against the realised tracking error it cost, by estimator
# and budget. Right: the attribution of the nineteen paths' active return, contributions and residual.
fig, (axl, axr) = plt.subplots(1, 2, figsize=(8.2, 5.2), gridspec_kw={"width_ratios": [1, 1.25]})
for v in VARIANTS[:5]:
    ps = [p for p in FO_MAIN if FO[p]["variant"] == v]
    xs = [FO[p]["realised"] for p in ps]
    ys = [FO[p]["objective"] for p in ps]
    axl.plot(xs, ys, "-o", color=VCOLOUR[v], label=VLABEL[v], lw=1.4, ms=4.5)
for b in BUDGETS:
    pb = [p for p in FO_MAIN if FO[p]["budget"] == b]
    left = min(pb, key=lambda p: FO[p]["realised"])   # the leftmost marker at this budget; the label sits to its left
    axl.annotate(f"{b} bp", (FO[left]["realised"], FO[left]["objective"]), xytext=(-3, 5), textcoords="offset points", fontsize=7.2, color=INK2, ha="right")
axl.set_xlim(left=min(FO[p]["realised"] for p in FO_MAIN) - 10)   # room for the budget labels left of the leftmost markers
axl.set_xlabel("realised tracking error, basis points a year")
axl.set_ylabel("mean factor objective, beta units")
axl.set_title("The exposure bought, against what it cost", loc="left", fontsize=9.5, color=INK)
axl.legend(frameon=False, fontsize=7.5, loc="lower right")
axl.grid(axis="both", lw=0.6, color=GRID)
y = np.arange(len(FO_PATHS))
left_pos = np.zeros(len(FO_PATHS))
left_neg = np.zeros(len(FO_PATHS))
for f in FACTORS:
    vals = np.array([FO[p]["contribution"][f] for p in FO_PATHS])
    pos = np.where(vals > 0, vals, 0)
    neg = np.where(vals < 0, vals, 0)
    axr.barh(y, pos, left=left_pos, color=FCOLOUR[f], height=0.66, edgecolor="white", linewidth=0.5, label=FLABEL[f])
    axr.barh(y, neg, left=left_neg, color=FCOLOUR[f], height=0.66, edgecolor="white", linewidth=0.5)
    left_pos += pos
    left_neg += neg
resid = np.array([FO[p]["residual"] for p in FO_PATHS])
axr.barh(y, np.where(resid > 0, resid, 0), left=left_pos, color=RESID_COLOUR, height=0.66, edgecolor="white", linewidth=0.5, label="residual (the industries' own returns)")
axr.barh(y, np.where(resid < 0, resid, 0), left=left_neg, color=RESID_COLOUR, height=0.66, edgecolor="white", linewidth=0.5)
axr.plot([FO[p]["active"] for p in FO_PATHS], y, "|", color=INK, ms=9, mew=1.5, label="active return")
axr.axvline(0, color=FRAME, lw=0.8)
axr.set_yticks(y)
axr.set_yticklabels([f"{FO_VSHORT[FO[p]['variant']]} | {FO[p]['budget']}" for p in FO_PATHS], fontsize=7.2)
axr.invert_yaxis()
axr.set_title("Where the active return came from, by path", loc="left", fontsize=9.5, color=INK)
axr.set_xlabel("basis points a year")
axr.grid(axis="x", lw=0.6, color=GRID)
handles, labels = axr.get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, fontsize=7.2, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.045))
fig.text(0.01, 0.03, "Source: Kenneth R. French Data Library and author's calculations. The mark is the active return, the sum of the bars.", fontsize=7.2, color=META)
fig.text(0.01, 0.005, f"results/{V}/factor_objective_evaluation_{V}.csv (notebook 15) and factor_objective_attribution_{V}.csv (notebook 16), {MONTHS} months.", fontsize=7.2, color=META)
fig.tight_layout(rect=(0, 0.13, 1, 1))
fig.savefig(os.path.join(FIG_DIR, "fig_factor_objective.svg"), metadata={"Creator": None, "Date": None})
plt.close(fig)

# --- the page ---
tpl = open(os.path.join(SCRIPT_DIR, "template.html"), encoding="utf-8").read()
missing = sorted(set(re.findall(r"\{\{(\w[\w-]*)\}\}", tpl)) - set(P))
assert not missing, missing
html = re.sub(r"\{\{(\w[\w-]*)\}\}", lambda m: P[m.group(1)], tpl)
assert "{{" not in html
html = html.replace("/*DATA*/null", json.dumps(D, separators=(",", ":")))
open(OUT, "w", encoding="utf-8").write(html)
print("written", os.path.relpath(OUT, REPO), len(html), "bytes; figures in dashboard/figures/; vintage", V, "; months", MONTHS, FIRST, "to", LAST)
