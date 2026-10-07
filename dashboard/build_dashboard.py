"""Builds the dashboard, dashboard/B-P_dashboard.html, and the static figures in dashboard/figures/
from the output files the notebooks write to outputs/ and from template.html.

Usage, from the repository root, after notebooks 03, 07, 08, 10, 11, 12 and 13 have run:
    python3 dashboard/build_dashboard.py

The page embeds the data it draws, so it opens from a file; the charts are drawn in the browser by
Plotly, loaded from its content delivery network, so the interactive page needs a connection once.
The two static figures (SVG, drawn with matplotlib) are the ones the README shows and need nothing.
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
committed(V)
direct = json.load(open(os.path.join(REPO, "checks", "results_crsp_direct_test.json")))   # committed with notebook 08; aggregates only

RULES = ["ew", "mv", "bs", "min", "vw", "mv-c", "bs-c", "min-c", "g-min-c"]
RULE_LABEL = {"ew": "1/N", "mv": "mean-variance", "bs": "Bayes-Stein", "min": "minimum variance", "vw": "value-weighted market",
              "mv-c": "mean-variance, constrained", "bs-c": "Bayes-Stein, constrained", "min-c": "minimum variance, constrained",
              "g-min-c": "minimum variance, generalised constraint"}
DATASETS = ["Industry", "MKT/SMB/HML", "FF-1-factor", "FF-4-factor"]
VARIANTS = ["sample, daily 3y", "ledoit_wolf, daily 3y", "factor, daily 3y", "pca, daily 3y", "sample, monthly 120", "robust, all five", "RiskMetrics, daily 5y"]
VLABEL = {"sample, daily 3y": "Sample, 3y daily", "ledoit_wolf, daily 3y": "Ledoit-Wolf, 3y daily", "factor, daily 3y": "Six-factor model, 3y daily",
          "pca, daily 3y": "Principal components, 3y daily", "sample, monthly 120": "Sample, 120 months", "robust, all five": "Robust (worst of five)",
          "RiskMetrics, daily 5y": "RiskMetrics, 5y daily"}
VCOLOUR = {"sample, daily 3y": "#1f5fa8", "ledoit_wolf, daily 3y": "#4c9ed9", "factor, daily 3y": "#d1731e", "pca, daily 3y": "#e0a53a",
           "sample, monthly 120": "#8a8a8a", "robust, all five": "#2e8b57", "RiskMetrics, daily 5y": "#9b4dca"}
SETS = ["C0", "C1", "C2", "C3 tilt only", "C3"]
SET_LABEL = {"C0": "long-only", "C1": "+ active weight bound", "C2": "+ turnover cap", "C3 tilt only": "+ tilt", "C3": "+ exclusions and beta neutrality"}
FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
FLABEL = {"Mkt-RF": "market", "SMB": "size", "HML": "value", "RMW": "profitability", "CMA": "investment", "Mom": "momentum"}
FCOLOUR = {"Mkt-RF": "#555555", "SMB": "#1f5fa8", "HML": "#d1731e", "RMW": "#2e8b57", "CMA": "#9b4dca", "Mom": "#e0a53a"}
RESID_COLOUR = "#c9c9c9"

assert list(bench.columns) == ["benchmark", "market"]
assert set(roll["variant"]) == set(VARIANTS) and set(roll["set"]) == set(SETS)
assert set(att["variant"]) == set(VARIANTS)
MONTHS = int(att["months"].iloc[0])
FIRST, LAST = active.index[0], active.index[-1]
assert len(active) == MONTHS


def r(x, d=4):
    return float(round(float(x), d))


# --- the data the page embeds ---
D = {"vintage": V, "months": MONTHS, "first": FIRST, "last": LAST, "variants": VARIANTS, "vlabel": VLABEL, "vcolour": VCOLOUR,
     "sets": SETS, "setlabel": SET_LABEL, "factors": FACTORS, "flabel": FLABEL, "fcolour": FCOLOUR, "resid": RESID_COLOUR,
     "rules": RULES, "rulelabel": RULE_LABEL, "datasets": DATASETS}

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

# 9. the attribution
D["att"] = {}
for s in ["C3", "C3 tilt only"]:
    sub = att[att.set == s].set_index("variant")
    D["att"][s] = {v: {"exposure": {f: r(sub.loc[v, f"exposure {f}"], 6) for f in FACTORS},
                       "contribution": {f: r(sub.loc[v, f"contribution {f} (per year)"] * 1e4, 4) for f in FACTORS},
                       "residual": r(sub.loc[v, "residual (per year)"] * 1e4, 4), "active": r(sub.loc[v, "active return (per year)"] * 1e4, 4),
                       "se": r(sub.loc[v, "active return (standard error)"] * 1e4, 4), "share": r(sub.loc[v, "factor share"], 5)} for v in VARIANTS}
D["att_dec"] = {"period": list(att_dec.iloc[:, 0]), "contribution": {f: [r(x * 1e4, 4) for x in att_dec[f"contribution {f}"]] for f in FACTORS},
                "residual": [r(x * 1e4, 4) for x in att_dec["residual"]]}
mc = att_cost.set_index("variant")
D["att_cost"] = {v: {"active": r(mc.loc[v, "active return"] * 1e4, 4), "factor": r(mc.loc[v, "factor total"] * 1e4, 4), "residual": r(mc.loc[v, "residual"] * 1e4, 4),
                     "se": r(mc.loc[v, "active return (standard error)"] * 1e4, 4)} for v in VARIANTS}

# 10. the optimiser
D["opt_months"] = list(dict.fromkeys(opt_fixes["month"]))
D["opt_fixes"] = [{"month": row.month, "estimator": EST_LABEL.get(row.estimator, row.estimator) + (" (120 months)" if row.data == "monthly_120" else ""),
                   "tilt": r(row._4, 3), "mandate": r(row._5, 3)} for row in opt_fixes.itertuples()]
assert list(opt_fixes.columns)[3:5] == ["tilt only (bp)", "mandate C3 (bp)"]
D["speed"] = {"rebalance": [int(x) for x in opt_speed["rebalance"]], "distance": [r(x * 100, 4) for x in opt_speed["one-way distance to the benchmark"]],
              "te": [r(x, 3) for x in opt_speed["forecast tracking error (bp a year)"]]}

# --- the prose numbers ---
P = {}
P["vintage"] = V
P["months"] = str(MONTHS)
P["first"] = FIRST
P["last"] = LAST
P["gated_pass"] = str(int((gated.verdict == "pass").sum()))
P["gated_n"] = str(len(gated))
P["turn_pass"] = str(int((gated_t.verdict == "pass").sum()))
P["turn_n"] = str(len(gated_t))
new_lo, new_hi = re.search(r"\((\d{4}-\d{2}) to (\d{4}-\d{2})\)", periods[1]).groups()
P["new_months"] = str((pd.Period(new_hi, "M") - pd.Period(new_lo, "M")).n + 1)
P["new_lo"], P["new_hi"] = new_lo, new_hi
paper_lo, paper_hi = re.search(r"\((\d{4}-\d{2}) to (\d{4}-\d{2})\)", periods[0]).groups()
P["paper_lo"], P["paper_hi"] = paper_lo, paper_hi
P["beats"] = str(int(ext_vs["beats 1/N at 5%"].sum()))
P["cells"] = str(len(ext_vs))
P["bench_te"] = f"{gap.std() * np.sqrt(12) * 1e4:.1f}"
P["gap_share"] = f"{direct['expectation_2_predicted_vs_observed']['share_of_variance_explained'] * 100:.0f}"
P["bench_months"] = str(len(bench))
P["bench_first"] = bench.index[0]
te_c3 = {v: roll[(roll.variant == v) & (roll.set == "C3")]["realised TE"].iloc[0] * 1e4 for v in VARIANTS}
daily4 = [te_c3[v] for v in VARIANTS[:4]]
P["te_lo"] = f"{min(daily4):.1f}"
P["te_hi"] = f"{max(daily4):.1f}"
P["te_monthly"] = f"{te_c3['sample, monthly 120']:.1f}"
P["te_range"] = f"{max(daily4) - min(daily4):.1f}"
bias_c3 = [roll[(roll.variant == v) & (roll.set == "C3")]["bias"].iloc[0] for v in VARIANTS[:4]]
P["bias_lo"] = f"{min(bias_c3):.2f}"
P["bias_hi"] = f"{max(bias_c3):.2f}"
P["bias_monthly"] = f"{roll[(roll.variant == 'sample, monthly 120') & (roll.set == 'C3')]['bias'].iloc[0]:.2f}"
cal4 = [calset.loc[v, "bias, calibrated"] for v in VARIANTS[:4]]
P["cal_lo"] = f"{min(cal4):.2f}"
P["cal_hi"] = f"{max(cal4):.2f}"
att_tilt = att[att.set == "C3 tilt only"].set_index("variant")
tilt_gross = [att_tilt.loc[v, "active return (per year)"] * 1e4 for v in VARIANTS]
tilt_se = [att_tilt.loc[v, "active return (standard error)"] * 1e4 for v in VARIANTS]
P["tilt_lo"] = f"{min(tilt_gross):+.0f}"
P["tilt_hi"] = f"{max(tilt_gross):+.0f}"
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
P["tilt_cost_first"] = f"{opt_fixes[opt_fixes.month == first_month]['tilt only (bp)'].max():.0f}"
mo = main[main.data == "monthly_120"].set_index("estimator")
P["gmv_sample"] = f"{mo.loc['sample', 'GMV unconstrained vol %']:.1f}"
P["gmv_lo"] = f"{mo.drop('sample')['GMV unconstrained vol %'].min():.1f}"
P["gmv_hi"] = f"{mo.drop('sample')['GMV unconstrained vol %'].max():.1f}"
P["lo_lo"] = f"{main['GMV long-only vol %'].min():.1f}"
P["lo_hi"] = f"{main['GMV long-only vol %'].max():.1f}"
P["build_date"] = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam")).strftime("%-d %B %Y")
P["top_ind"] = ", ".join(top_ind)

# --- the static figures ---
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none", "figure.dpi": 100,
                     "svg.hashsalt": "B-P"})  # fixed element ids, so a rebuild from the same files is byte-identical
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
ax.set_title("Realised (filled) and forecast (hollow) tracking error by constraint set, 1979-07 to 2026-08", loc="left", fontsize=9.5)
ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
ax.grid(axis="y", lw=0.4, alpha=0.5)
fig.text(0.01, 0.01, f"Source: results/{V}/rolling_evaluation_{V}.csv (notebook 12), {MONTHS} months; the first three sets realise {lo3:.0f} to {hi3:.1f} basis points.", fontsize=7.2, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1))
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
        ax.barh(y, pos, left=left_pos, color=FCOLOUR[f], height=0.62, label=FLABEL[f])
        ax.barh(y, neg, left=left_neg, color=FCOLOUR[f], height=0.62)
        left_pos += pos
        left_neg += neg
    resid = np.array([D["att"][s][v]["residual"] for v in VARIANTS])
    ax.barh(y, np.where(resid > 0, resid, 0), left=left_pos, color=RESID_COLOUR, height=0.62, label="residual (the industries' own returns)")
    ax.barh(y, np.where(resid < 0, resid, 0), left=left_neg, color=RESID_COLOUR, height=0.62)
    tot = np.array([D["att"][s][v]["active"] for v in VARIANTS])
    ax.plot(tot, y, "k|", ms=11, mew=1.6, label="active return")
    ax.axvline(0, color="#333", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([VLABEL[v] for v in VARIANTS])
    ax.set_title(title, loc="left", fontsize=9.5)
    ax.set_xlabel("basis points a year")
    ax.set_xlim(-26, 26)
    ax.grid(axis="x", lw=0.4, alpha=0.5)
axes[0].invert_yaxis()
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, fontsize=7.5, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.04))
fig.text(0.01, 0.005, f"Source: results/{V}/attribution_summary_{V}.csv (notebook 13). The black mark is the active return, the sum of the bars.", fontsize=7.2, color="#555")
fig.tight_layout(rect=(0, 0.12, 1, 1))
fig.savefig(os.path.join(FIG_DIR, "fig_attribution.svg"), metadata={"Creator": None, "Date": None})
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
