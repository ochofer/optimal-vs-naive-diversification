"""Builds the dashboard, dashboard/B-P_dashboard.html, from the tables committed in results/<vintage>/ and from
dashboard/template.html.

Usage, from the repository root, after the tables are committed:
    python3 dashboard/build_dashboard.py

The page embeds the data it draws, so it opens from a file; the charts are drawn in the browser by Plotly, loaded
from its content delivery network, so the interactive page needs a connection once. Every number in the page's prose
is computed here from the committed tables and substituted into the template, and the build stops if a table is not
the file at the current commit, so that the page can only be built from the tables a reader can open at the commit.
The tables of notebooks 03, 07, 08 and 09 are in results/<vintage>/, and the optimised portfolios' tables, copied
unchanged from the companion study risk-models-for-index-tracking at commit ddbb75c, in results/<vintage>/source/.
The source lines name no file (the house standard's C6); the Method view's table "Where each exhibit comes from"
links each exhibit's tables and the notebook that writes them on GitHub, each at the commit that last changed it.
The figures and tables are numbered here in page order (C5): the template names each exhibit by a key, {{n:key}} is
its number and {{id:key}} its anchor. The data are embedded with two decimals more than the page displays, so that
no displayed number is rounded twice.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import zoneinfo

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
OUT = os.path.join(SCRIPT_DIR, "B-P_dashboard.html")
GITHUB = "https://github.com/ochofer/optimal-vs-naive-diversification"
SOURCE_REPO = "https://github.com/ochofer/risk-models-for-index-tracking"
SOURCE_COMMIT = "ddbb75c46ff0b4622522aa0a0156427a200ac6cb"


def git(*args):
    try:
        return subprocess.run(["git", "-C", REPO, *args], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sys.exit("dashboard/build_dashboard.py: the build runs inside the repository's checkout, because the Method view links each table on GitHub at the commit that last changed it (git " + " ".join(args) + " failed)")


COMMIT = git("rev-parse", "HEAD")
assert git("rev-parse", SOURCE_COMMIT) == SOURCE_COMMIT


def last_change(relpath):
    sha = git("log", "-1", "--format=%H", "--", relpath)
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        sys.exit(f"dashboard/build_dashboard.py: {relpath} has no commit; commit it before building, so that the Method view can link it")
    return sha


READ = []


def table(relpath, **kw):
    """A committed table, read after checking that the file in the checkout is the file at the current commit."""
    path = os.path.join(REPO, relpath)
    at_commit = subprocess.run(["git", "-C", REPO, "rev-parse", "--verify", "-q", f"HEAD:{relpath}"], capture_output=True, text=True).stdout.strip()
    if not at_commit or at_commit != git("hash-object", path):
        sys.exit(f"dashboard/build_dashboard.py: {relpath} is not the file at commit {COMMIT[:7]}; commit the tables before building")
    READ.append(relpath)
    return pd.read_csv(path, **kw)


prov = json.load(open(os.path.join(REPO, "results", "202608", "provenance_french.json")))
vintages = {m.group(1) for rec in prov for m in [re.search(r"using the (\d{6}) CRSP", rec.get("vintage_line", ""))] if m}
assert len(vintages) == 1
V = vintages.pop()
R = f"results/{V}/"
S = f"results/{V}/source/"

# --- inputs ---
rep_sharpe = table(R + f"replication_sharpe_{V}.csv")
rep_turn = table(R + f"replication_turnover_{V}.csv")
ext_sharpe = table(R + f"extended_sample_sharpe_{V}.csv")
ext_vs = table(R + f"extended_sample_vs_1N_{V}.csv")
nt_paired = table(R + f"naive_tilt_paired_tests_{V}.csv").set_index("path")
nt_costs = table(R + f"naive_tilt_returns_and_costs_{V}.csv", index_col=0)
nt_meas = table(R + f"naive_tilt_measures_{V}.csv", index_col=0).loc["naive tilt"]
nt_month = table(R + f"naive_tilt_monthly_{V}.csv", index_col=0)
nt_ir = table(R + f"naive_tilt_information_ratios_{V}.csv", index_col=0)
nt_spread = table(R + f"naive_tilt_spread_{V}.csv").iloc[0]
nt_ird = table(R + f"naive_tilt_information_ratio_differences_{V}.csv")
ti_boot = table(R + f"tilted_index_bootstrap_{V}.csv").set_index("path")
ti_beside = table(R + f"tilted_index_beside_paths_{V}.csv", index_col=0)
ti_meas = table(R + f"tilted_index_measures_{V}.csv", index_col=0).loc["tilted index"]
ti_month = table(R + f"tilted_index_monthly_{V}.csv", index_col=0)
ti_k = table(R + f"tilted_index_k_{V}.csv").iloc[0]
ti_kat = table(R + f"tilted_index_k_set_at_{V}.csv", index_col=0)["months"]
ti_bud = table(R + f"tilted_index_budgets_75_and_150_{V}.csv", index_col=0)
ti_ir = table(R + f"tilted_index_information_ratios_{V}.csv", index_col=0)
ti_att = table(R + f"tilted_index_attribution_summary_{V}.csv", index_col=0).loc["tilted index"]
ti_ird = table(R + f"tilted_index_information_ratio_differences_{V}.csv")
ti_rx = table(R + f"tilted_index_realised_exposure_{V}.csv", index_col=0)
roll = table(S + f"rolling_evaluation_{V}.csv")
active = table(S + f"active_returns_{V}.csv", index_col=0)
att_src = table(S + f"attribution_summary_{V}.csv")
fo_eval = table(S + f"factor_objective_evaluation_{V}.csv", index_col=0)
fo_att = table(S + f"factor_objective_attribution_{V}.csv").set_index("path")

PATHS = ["sample, daily 3y", "ledoit_wolf, daily 3y", "factor, daily 3y", "pca, daily 3y", "sample, monthly 120", "robust, all five", "RiskMetrics, daily 5y"]
PLABEL = {"sample, daily 3y": "Sample covariance, 3 years daily", "ledoit_wolf, daily 3y": "Ledoit-Wolf shrinkage, 3 years daily",
          "factor, daily 3y": "Six-factor model, 3 years daily", "pca, daily 3y": "Principal components, 3 years daily",
          "sample, monthly 120": "Sample covariance, 120 months", "robust, all five": "Robust, built on the five",
          "RiskMetrics, daily 5y": "RiskMetrics, 5 years daily"}
PSHORT = {"sample, daily 3y": "Sample, daily", "ledoit_wolf, daily 3y": "Ledoit-Wolf", "factor, daily 3y": "Six-factor", "pca, daily 3y": "Principal comp.",
          "sample, monthly 120": "Sample, monthly", "robust, all five": "Robust", "RiskMetrics, daily 5y": "RiskMetrics"}
RULES = ["ew", "mv", "bs", "min", "vw", "mv-c", "bs-c", "min-c", "g-min-c"]
RULE_LABEL = {"ew": "1/N", "mv": "mean-variance", "bs": "Bayes-Stein", "min": "minimum variance", "vw": "value-weighted market",
              "mv-c": "mean-variance, constrained", "bs-c": "Bayes-Stein, constrained", "min-c": "minimum variance, constrained",
              "g-min-c": "minimum variance, generalised constraint"}
RULE_SHORT = {"ew": "1/N", "mv": "mean-variance", "bs": "Bayes-Stein", "min": "min. variance", "vw": "VW market",
              "mv-c": "mean-var., constr.", "bs-c": "Bayes-Stein, constr.", "min-c": "min. var., constr.", "g-min-c": "min. var., gen. constr."}
DATASETS = ["Industry", "MKT/SMB/HML", "FF-1-factor", "FF-4-factor"]
FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
FLABEL = {"Mkt-RF": "market", "SMB": "size", "HML": "value", "RMW": "profitability", "CMA": "investment", "Mom": "momentum"}
TARGETED = ["HML", "RMW", "CMA", "Mom"]
TL = {v: f"{v} | C3 tilt only" for v in PATHS}
FL = {v: f"{v} | 100" for v in PATHS}
tilt_rows = roll[roll["set"] == "C3 tilt only"].set_index("variant").loc[PATHS]
att_tilt = att_src[att_src["set"] == "C3 tilt only"].set_index("variant").loc[PATHS]
MONTHS = len(nt_month)
FIRST, LAST = nt_month.index[0], nt_month.index[-1]
assert MONTHS == 566 and len(ti_month) == MONTHS


def r(x, d=4):
    return float(round(float(x), d))


def irs(row):
    return {"g": r(row["information ratio (gross)"], 5), "se_g": r(row["standard error (gross)"], 5),
            "n50": r(row["information ratio at 50 bp"], 5), "se_n50": r(row["standard error at 50 bp"], 5),
            "n100": r(row["information ratio at 100 bp"], 5), "se_n100": r(row["standard error at 100 bp"], 5)}


# --- the data the page embeds ---
D = {"vintage": V, "months": MONTHS, "paths": PATHS, "plabel": PLABEL, "pshort": PSHORT, "factors": FACTORS, "flabel": FLABEL,
     "rules": RULES, "rulelabel": RULE_LABEL, "ruleshort": RULE_SHORT, "datasets": DATASETS}
D["rep_sharpe"] = [{"rule": row.rule, "dataset": row.dataset, "x": r(row.published, 6), "y": r(row.replicated, 6), "verdict": row.verdict}
                   for row in rep_sharpe.itertuples() if row.rule != "mv (in sample)"]
D["rep_turn"] = [{"rule": row.rule, "dataset": row.dataset, "x": r(row.published, 4), "y": r(row.replicated, 4), "verdict": row.verdict}
                 for row in rep_turn.itertuples() if row.rule != "vw" and row.published == row.published]
gated = rep_sharpe[rep_sharpe.verdict.isin(["pass", "MISS"])]
gated_t = rep_turn[rep_turn.verdict.isin(["pass", "MISS"])]
periods = list(dict.fromkeys(ext_sharpe["period"]))
assert len(periods) == 3
D["ext_periods"] = periods
D["ext_sharpe"] = {}
for p in periods:
    sub = ext_sharpe[ext_sharpe.period == p].set_index("rule")
    D["ext_sharpe"][p] = {d: {rule: r(sub.loc[rule, d], 6) for rule in RULES} for d in DATASETS}
D["ext_vs"] = [{"dataset": row.dataset, "rule": row.rule, "p": r(row._6, 4)} for row in ext_vs.itertuples()]

# the naive tilt and the optimised portfolios under the tilt alone
D["nt"] = {"naive": {"te": r(1e4 * nt_meas["realised TE"], 3), "turn": r(100 * nt_meas["turnover (one-way)"], 4),
                     "gross": r(1e4 * nt_meas["active return (gross)"], 3), "net50": r(1e4 * nt_meas["net active return at 50 bp"], 3),
                     "net100": r(1e4 * nt_meas["net active return at 100 bp"], 3), "ir": irs(nt_ir.loc["naive tilt"]),
                     "x": {f: r(nt_meas[f"mean exposure {f}"], 5) for f in FACTORS}}, "paths": {}}
for v in PATHS:
    p, t = nt_paired.loc[TL[v]], tilt_rows.loc[v]
    D["nt"]["paths"][v] = {"te": r(p["path (bp)"], 3), "diff": r(p["difference (bp)"], 3), "lo": r(p["lower (bp)"], 3), "hi": r(p["upper (bp)"], 3),
                           "holm": r(p["Holm p-value"], 5), "corr": r(p["correlation"], 4), "turn": r(100 * t["turnover (one-way)"], 4),
                           "gross": r(1e4 * t["active return (gross)"], 3), "net50": r(1e4 * t["net active return at 50 bp"], 3),
                           "net100": r(1e4 * t["net active return at 100 bp"], 3), "ir": irs(nt_ir.loc[TL[v]]),
                           "x": {f: r(att_tilt.loc[v, f"exposure {f}"], 5) for f in FACTORS}}
    assert abs(p["path (bp)"] - 1e4 * t["realised TE"]) < 5e-5
month_dates = [f"{m}-15" for m in nt_month.index]
D["cum"] = {"month": month_dates, "naive": [r(x, 4) for x in 100 * nt_month["active_return"].cumsum()],
            "paths": {v: [r(x, 4) for x in 100 * active.loc[nt_month.index, TL[v]].cumsum()] for v in PATHS}}

# the tilted index and the optimised portfolios under the factor objective
def contributions(row):
    return {f: r(1e4 * row[f"contribution {f} (per year)"], 3) for f in FACTORS}


D["ti"] = {"naive": {"te": r(1e4 * ti_meas["realised TE"], 3), "obj": r(ti_meas["mean objective"], 5), "epb": r(ti_meas["exposure per bp of realised TE"], 8),
                     "turn": r(100 * ti_meas["turnover (one-way)"], 4), "gross": r(1e4 * ti_meas["active return (gross)"], 3),
                     "net50": r(1e4 * ti_meas["net active return at 50 bp"], 3), "net100": r(1e4 * ti_meas["net active return at 100 bp"], 3),
                     "ir": irs(ti_ir.loc["tilted index"]), "contribution": contributions(ti_att), "residual": r(1e4 * ti_att["residual (per year)"], 3),
                     "active": r(1e4 * ti_att["active return (per year)"], 3), "targeted": r(1e4 * ti_att["targeted total (per year)"], 3),
                     "rx_epb": r(ti_rx.loc["tilted index", "realised exposure per bp"], 8)}, "paths": {}}
for v in PATHS:
    b, e, a = ti_boot.loc[FL[v]], fo_eval.loc[FL[v]], fo_att.loc[FL[v]]
    D["ti"]["paths"][v] = {"te": r(1e4 * e["realised TE"], 3), "obj": r(ti_beside.loc[FL[v], "mean objective"], 5), "epb": r(b["path value"], 8),
                           "diff": r(b["difference"], 8), "lo": r(b["lower"], 8), "hi": r(b["upper"], 8), "holm": r(b["Holm p-value"], 5),
                           "turn": r(100 * e["turnover (one-way)"], 4), "gross": r(1e4 * e["active return (gross)"], 3),
                           "net50": r(1e4 * e["net active return at 50 bp"], 3), "net100": r(1e4 * e["net active return at 100 bp"], 3),
                           "ir": irs(ti_ir.loc[FL[v]]), "contribution": contributions(a), "residual": r(1e4 * a["residual (per year)"], 3),
                           "active": r(1e4 * a["active return (per year)"], 3), "targeted": r(1e4 * a["targeted total (per year)"], 3),
                           "rx_epb": r(ti_rx.loc[FL[v], "realised exposure per bp"], 8), "rx_holm": r(ti_rx.loc[FL[v], "Holm p-value"], 5)}
D["k"] = {"month": month_dates, "k": [r(x, 5) for x in ti_month["k"]], "floor": [bool(x == "floor") for x in ti_month["k set by"]],
          "at": [str(x) for x in ti_month["k set at"]]}
D["bud"] = [{"path": i.split(" | ")[0], "budget": int(i.split(" | ")[1]), "te": r(1e4 * row["realised TE"], 3), "epb": r(row["exposure per bp of realised TE"], 8)}
            for i, row in ti_bud.iterrows()]

# --- the prose numbers ---
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def words(ym):
    y, m = ym.split("-")
    return f"{MONTH_NAMES[int(m) - 1]} {int(y)}"


def signed(x, d):
    v = round(float(x), d)
    if v == 0:
        return f"{0:.{d}f}"
    return ("+" if v > 0 else "−") + f"{abs(v):.{d}f}"


def plain(x, d):
    v = round(float(x), d)
    return ("−" if v < 0 else "") + f"{abs(v):.{d}f}"


def rng(xs, d, sign=False, by_size=False):
    xs = sorted(xs, key=abs) if by_size else sorted(xs)
    f = (lambda x: signed(x, d)) if sign else (lambda x: plain(x, d))
    return f"{f(xs[0])} to {f(xs[-1])}"


NT, TI = D["nt"], D["ti"]
P = {"vintage": V, "months": str(MONTHS), "first_w": words(FIRST), "last_w": words(LAST)}
P["gated_pass"] = str(int((gated.verdict == "pass").sum()))
P["gated_n"] = str(len(gated))
P["turn_n"] = str(int((gated_t.rule != "vw").sum()))   # the value-weighted market trades nothing, so its four figures test nothing
assert (P["gated_pass"], P["gated_n"], P["turn_n"]) == ("29", "30", "26") and (gated_t.verdict == "pass").all()
new_lo, new_hi = re.search(r"\((\d{4}-\d{2}) to (\d{4}-\d{2})\)", periods[1]).groups()
P["new_months"] = str((pd.Period(new_hi, "M") - pd.Period(new_lo, "M")).n + 1)
P["new_lo_w"], P["new_hi_w"] = words(new_lo), words(new_hi)
paper_lo, paper_hi = re.search(r"\((\d{4}-\d{2}) to (\d{4}-\d{2})\)", periods[0]).groups()
P["paper_lo_w"], P["paper_hi_w"] = words(paper_lo), words(paper_hi)
_opt = [x for x in RULES if x not in ("ew", "vw")]
_beat = ext_vs[ext_vs["beats 1/N at 5%"]]
assert len(_beat) == 1 and _beat["rule"].iloc[0] == "vw" and not _beat["rule"].isin(_opt).any() and ext_vs["dataset"].nunique() == 4
P["datasets_w"] = "four"
P["beat_cell"] = f"the {RULE_LABEL[_beat['rule'].iloc[0]]}'s on {_beat['dataset'].iloc[0]}"

pv = NT["paths"]
diffs = [pv[v]["diff"] for v in PATHS]
assert all(pv[v]["holm"] < 0.05 and pv[v]["lo"] > 0 for v in PATHS)
assert min(PATHS, key=lambda v: pv[v]["diff"]) == "sample, monthly 120" and max(PATHS, key=lambda v: pv[v]["diff"]) == "RiskMetrics, daily 5y"
P["nt_te"] = plain(NT["naive"]["te"], 1)
P["nt_paths_te"] = rng([pv[v]["te"] for v in PATHS], 1)
P["nt_diff_lo"], P["nt_diff_hi"] = plain(min(diffs), 1), plain(max(diffs), 1)
P["nt_diff_lo0"], P["nt_diff_hi0"] = plain(min(diffs), 0), plain(max(diffs), 0)
P["nt_holm_lo"], P["nt_holm_hi"] = plain(min(pv[v]["holm"] for v in PATHS), 4), plain(max(pv[v]["holm"] for v in PATHS), 4)
P["nt_turn"] = plain(NT["naive"]["turn"], 2)
P["nt_paths_turn"] = rng([pv[v]["turn"] for v in PATHS], 2)
P["nt_cap"] = str(int(nt_meas["months above the turnover cap"]))
P["nt_gross"] = signed(NT["naive"]["gross"], 1)
P["nt_paths_gross"] = rng([pv[v]["gross"] for v in PATHS], 1, sign=True)
P["nt_net"] = signed(NT["naive"]["net100"], 1)
P["nt_paths_net"] = rng([pv[v]["net100"] for v in PATHS], 1, sign=True)
for f in TARGETED:
    P[f"nt_x_{f.lower()}"] = signed(NT["naive"]["x"][f], 3)
    if f != "Mom":   # the text says the optimised portfolios' exposures to value, profitability and investment are closer to zero
        assert all(abs(pv[v]["x"][f]) < abs(NT["naive"]["x"][f]) for v in PATHS)
P["nt_cum_end"] = signed(D["cum"]["naive"][-1], 2)
P["nt_paths_cum_end"] = rng([D["cum"]["paths"][v][-1] for v in PATHS], 2, sign=True)
P["spread_mean"] = signed(100 * nt_spread["mean per year"], 2)
P["spread_sd"] = plain(100 * nt_spread["standard deviation per year"], 2)
P["spread_t"] = plain(nt_spread["t-ratio"], 2)
g = nt_ird[nt_ird["ratio"] == "gross"]
assert (g["p-value"] >= 0.05).all() and (nt_ird["Holm p-value"] >= 0.05).all()
P["nt_irgap"] = rng(g["difference"], 2)
P["nt_ir_pse"] = rng(g["paired standard error"], 2)
h = nt_ird[nt_ird["ratio"] == "at 100 bp"]
P["nt_ir_100_alone"] = ["none", "one", "two", "three", "four", "five", "six", "seven"][int((h["p-value"] < 0.05).sum())]
P["nt_ir_100_holm"] = ["none", "one", "two", "three", "four", "five", "six", "seven"][int((h["Holm p-value"] < 0.05).sum())]

tp = TI["paths"]
assert all(tp[v]["holm"] < 0.05 and tp[v]["hi"] < 0 for v in PATHS)
ratios = [tp[v]["epb"] / TI["naive"]["epb"] for v in PATHS]
P["ti_ratio_lo"], P["ti_ratio_hi"] = plain(min(ratios), 1), plain(max(ratios), 1)
P["ti_epb"] = plain(TI["naive"]["epb"], 6)
P["ti_paths_epb"] = rng([tp[v]["epb"] for v in PATHS], 6)
P["ti_holm"] = plain(tp[PATHS[0]]["holm"], 3)
assert len({round(tp[v]["holm"], 3) for v in PATHS}) == 1
P["ti_te"] = plain(TI["naive"]["te"], 1)
P["ti_paths_te"] = rng([tp[v]["te"] for v in PATHS], 1)
assert min(tp[v]["te"] for v in PATHS) < TI["naive"]["te"] < max(tp[v]["te"] for v in PATHS)
P["ti_turn"] = plain(TI["naive"]["turn"], 2)
P["ti_paths_turn"] = rng([tp[v]["turn"] for v in PATHS], 2)
P["ti_gross"] = signed(TI["naive"]["gross"], 1)
P["ti_paths_gross"] = rng([tp[v]["gross"] for v in PATHS], 1, sign=True)
P["ti_net"] = signed(TI["naive"]["net100"], 1)
P["ti_paths_net"] = rng([tp[v]["net100"] for v in PATHS], 1, sign=True)
P["k_bound"], P["k_floor"] = str(int(ti_k["months set by the bound"])), str(int(ti_k["months set by the floor"]))
assert list(ti_kat.index[:2]) == ["Banks", "Softw"]
assert {a for a, fl in zip(D["k"]["at"], D["k"]["floor"]) if fl} == {"Gold"}
P["k_median"] = plain(ti_k["k median"], 3)
P["fp_ftot"] = rng([1e4 * fo_att.loc[FL[v], "factor total (per year)"] for v in PATHS], 1, sign=True)
P["fp_resid"] = rng([tp[v]["residual"] for v in PATHS], 1, sign=True, by_size=True)
P["ti_ftot"] = signed(1e4 * ti_att["factor total (per year)"], 1)
P["ti_resid"] = signed(TI["naive"]["residual"], 1)
g2 = ti_ird[ti_ird["ratio"] == "gross"]
assert (ti_ird["p-value"] >= 0.05).all()
P["ti_irgap"] = rng(g2["difference"], 2)
P["ti_ir_pse"] = rng(g2["paired standard error"], 2)
rxp = ti_rx.loc[[FL[v] for v in PATHS]]
assert (rxp["Holm p-value"] >= 0.05).all()
assert all(abs(ti_rx.loc[FL[v], "forecast exposure per bp"] - tp[v]["epb"]) < 5e-9 for v in PATHS)
P["ti_rratio_lo"], P["ti_rratio_hi"] = plain(rxp["realised multiple of the tilted index"].min(), 1), plain(rxp["realised multiple of the tilted index"].max(), 1)
P["ti_rratio2_lo"], P["ti_rratio2_hi"] = plain(rxp["realised multiple of the tilted index"].min(), 2), plain(rxp["realised multiple of the tilted index"].max(), 2)
P["ti_rx_frac"] = rng(rxp["realised over forecast"], 2)
P["ti_rx_index"] = plain(ti_rx.loc["tilted index", "realised over forecast"], 1)
P["ti_rx_epb"] = plain(ti_rx.loc["tilted index", "realised exposure per bp"], 6)
rx_up = (ti_rx.loc["tilted index", "realised exposure per bp"] - rxp["lower"]) / ti_rx.loc["tilted index", "realised exposure per bp"]   # the largest multiple each interval leaves open
rx_dn = (ti_rx.loc["tilted index", "realised exposure per bp"] - rxp["upper"]) / ti_rx.loc["tilted index", "realised exposure per bp"]   # the smallest multiple each interval leaves open
P["ti_rx_up_lo"], P["ti_rx_up_hi"] = plain(rx_up.min(), 1), plain(rx_up.max(), 1)
P["ti_rx_dn_lo"], P["ti_rx_dn_hi"] = plain(rx_dn.min(), 1), plain(rx_dn.max(), 1)
assert (rx_up > 2).all() and (rx_dn < 1).all()   # the text: the intervals rule out neither a multiple below 1 nor one above 2
assert all(row["exposure per bp of realised TE"] > TI["naive"]["epb"] for _, row in ti_bud.iterrows())
P["build_date"] = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam")).strftime("%-d %B %Y")

# the key figures table
def kf_row(label, te, epb, turn, gross, net):
    return {"label": label, "te": te, "epb": epb, "turn": turn, "gross": gross, "net": net}


D["kf"] = [{"group": "Under the tilt alone"},
           kf_row("Naive tilt", plain(NT["naive"]["te"], 1), "", plain(NT["naive"]["turn"], 2), signed(NT["naive"]["gross"], 1), signed(NT["naive"]["net100"], 1)),
           kf_row("The seven optimised portfolios", P["nt_paths_te"], "", P["nt_paths_turn"], P["nt_paths_gross"], P["nt_paths_net"]),
           {"group": "Under the factor objective, budget 100 bp a year"},
           kf_row("Tilted index", plain(TI["naive"]["te"], 1), plain(TI["naive"]["epb"], 6), plain(TI["naive"]["turn"], 2), signed(TI["naive"]["gross"], 1), signed(TI["naive"]["net100"], 1)),
           kf_row("The seven optimised portfolios", P["ti_paths_te"], P["ti_paths_epb"], P["ti_paths_turn"], P["ti_paths_gross"], P["ti_paths_net"])]

# --- the exhibits: their sources, their numbers in page order, and the Method view's table (C5, C6, G10) ---
NB = {"03": "notebooks/03_shrinkage_and_constraints.ipynb", "07": "notebooks/07_extended_sample.ipynb", "08": "notebooks/08_naive_tilt.ipynb",
      "09": "notebooks/09_tilted_index.ipynb"}
SRC_NB = {"rolling_evaluation": "12_rolling_evaluation.ipynb", "active_returns": "12_rolling_evaluation.ipynb", "attribution_summary": "13_factor_attribution.ipynb",
          "factor_objective_evaluation": "15_factor_objective_evaluation.ipynb", "factor_objective_attribution": "16_factor_objective_attribution.ipynb"}
SOURCES = {
    "kf": [f"naive_tilt_measures_{V}.csv", f"tilted_index_measures_{V}.csv", f"source/rolling_evaluation_{V}.csv", f"source/factor_objective_evaluation_{V}.csv"],
    "f1": [f"naive_tilt_paired_tests_{V}.csv"],
    "rep": [f"replication_sharpe_{V}.csv", f"replication_turnover_{V}.csv"],
    "since": [f"extended_sample_sharpe_{V}.csv", f"extended_sample_vs_1N_{V}.csv"],
    "tediff": [f"naive_tilt_paired_tests_{V}.csv"],
    "cum": [f"naive_tilt_monthly_{V}.csv", f"source/active_returns_{V}.csv", f"naive_tilt_spread_{V}.csv"],
    "expo": [f"naive_tilt_measures_{V}.csv", f"source/attribution_summary_{V}.csv"],
    "turn": [f"naive_tilt_returns_and_costs_{V}.csv", f"naive_tilt_measures_{V}.csv", f"source/rolling_evaluation_{V}.csv"],
    "irt": [f"naive_tilt_information_ratios_{V}.csv", f"naive_tilt_information_ratio_differences_{V}.csv"],
    "epb": [f"tilted_index_bootstrap_{V}.csv", f"tilted_index_beside_paths_{V}.csv", f"tilted_index_realised_exposure_{V}.csv", f"source/factor_objective_evaluation_{V}.csv"],
    "k": [f"tilted_index_monthly_{V}.csv", f"tilted_index_k_{V}.csv", f"tilted_index_k_set_at_{V}.csv"],
    "fatt": [f"tilted_index_attribution_summary_{V}.csv", f"source/factor_objective_attribution_{V}.csv"],
    "fturn": [f"tilted_index_measures_{V}.csv", f"source/factor_objective_evaluation_{V}.csv"],
    "irf": [f"tilted_index_information_ratios_{V}.csv", f"tilted_index_information_ratio_differences_{V}.csv"],
    "bud": [f"tilted_index_budgets_75_and_150_{V}.csv", f"tilted_index_measures_{V}.csv"],
}


def writer(name):
    """The notebook that writes a table: one of this repository's, or, for a copied table, the companion study's at ddbb75c."""
    if name.startswith("source/"):
        stem = re.sub(rf"_{V}\.csv$", "", name[len("source/"):])
        nb = SRC_NB[stem]
        return f"<a href=\"{SOURCE_REPO}/blob/{SOURCE_COMMIT}/notebooks/{nb}\">notebook {nb[:2]} of the companion study</a>"
    if name.startswith(("replication_",)):
        key = "03"
    elif name.startswith("extended_sample_"):
        key = "07"
    elif name.startswith("naive_tilt_"):
        key = "08"
    else:
        key = "09"
    # the notebook at the commit that last changed the table, the version that wrote it, so that a later change to the
    # notebook's text alone does not move the link and a rebuild at any later commit reproduces the page
    return f"<a href=\"{GITHUB}/blob/{last_change(R + name)}/{NB[key]}\">notebook {key}</a>"


for key, files in SOURCES.items():
    for name in files:
        assert R + name in READ, (key, name)

tpl = open(os.path.join(SCRIPT_DIR, "template.html"), encoding="utf-8").read()
exhibits = re.findall(r"<(?:figure|div) class=\"fig\" data-key=\"(\w+)\" data-kind=\"(figure|table)\"", tpl)
keys = [k for k, _ in exhibits]
assert len(keys) == len(set(keys)) and set(keys) == set(SOURCES), sorted(set(keys) ^ set(SOURCES))
NUMBER, ANCHOR, LABEL = {}, {}, {}
counts = {"figure": 0, "table": 0}
for key, kind in exhibits:
    counts[kind] += 1
    NUMBER[key], ANCHOR[key], LABEL[key] = str(counts[kind]), f"{kind}-{counts[kind]}", f"{kind.capitalize()} {counts[kind]}"
for key, kind in exhibits:
    assert re.search(rf"<h2[^>]*>{kind.capitalize()} \{{\{{n:{key}\}}\}} \| ", tpl), key
refs = set(re.findall(r"\{\{(?:n|id):(\w+)\}\}", tpl))
assert refs <= set(keys), sorted(refs - set(keys))
visible = re.sub(r"<script>.*?</script>", "", tpl, flags=re.S)
stale = [m.group(0) for m in re.finditer(r"\b(?:Figures?|figures?|Tables?|tables?) \d", visible)]
assert stale == ["Tables 3"], stale   # the paper's Tables 3 and 5, named in the replication figure's source line
for line in visible.split("\n"):
    if "class=\"src\"" in line:
        assert "results/" not in line and "notebook" not in line, line
tpl = re.sub(r"\{\{n:(\w+)\}\}", lambda m: NUMBER[m.group(1)], tpl)
tpl = re.sub(r"\{\{id:(\w+)\}\}", lambda m: ANCHOR[m.group(1)], tpl)


def exhibit_table():
    rows = []
    for key, kind in exhibits:
        m = re.search(rf"<h2[^>]*>{LABEL[key]} \| (.*?)</h2>", tpl)
        title = re.sub(r"\{\{(\w[\w-]*)\}\}", lambda mm: P[mm.group(1)], m.group(1))
        files = "<br>".join(f"<a href=\"{GITHUB}/blob/{last_change(R + name)}/{R}{name}\">{name}</a>" for name in SOURCES[key])
        books = []
        for name in SOURCES[key]:
            w = writer(name)
            label = re.search(r">(notebook [^<]*)</a>", w).group(1)
            if label not in [re.search(r">(notebook [^<]*)</a>", x).group(1) for x in books]:
                books.append(w)
        rows.append(f"<tr><th>{LABEL[key]} | {title}</th><td>{files}</td><td>{'<br>'.join(books)}</td></tr>")
    return ("<h2 id=\"sources\">Where each exhibit comes from</h2>\n"
            "<p class=\"cap\">The committed tables each exhibit is drawn from, each linked on GitHub at the commit that last changed it, and the notebooks that write them, at that same commit. The tables in source/ are copied unchanged from the companion study, and their notebooks are linked in its repository at the commit they were copied from.</p>\n"
            "<div class=\"tw\"><div class=\"tscroll\"><table class=\"from\"><thead><tr><th>Exhibit</th><th>Committed tables</th><th>Written by</th></tr></thead>\n<tbody>\n"
            + "\n".join(rows) + "\n</tbody></table></div></div>")


P["exhibit_table"] = exhibit_table()
missing = sorted(set(re.findall(r"\{\{(\w[\w-]*)\}\}", tpl)) - set(P))
assert not missing, missing
html = re.sub(r"\{\{(\w[\w-]*)\}\}", lambda m: P[m.group(1)], tpl)
assert "{{" not in html and chr(0x2014) not in html
html = html.replace("/*DATA*/null", json.dumps(D, separators=(",", ":")))
open(OUT, "w", encoding="utf-8").write(html)
print("exhibits in page order:", ", ".join(f"{LABEL[k]} {k}" for k, _ in exhibits), "; tables checked at commit", COMMIT[:7])
print("written", os.path.relpath(OUT, REPO), len(html), "bytes; vintage", V, "; months", MONTHS, FIRST, "to", LAST)
