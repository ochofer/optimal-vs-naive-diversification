"""Builds the companion page, companion/industry_tilts_factor_exposures.html, from the output
files that notebooks 13 and 11 write to outputs/ and from page_template.html.

Usage, from the repository root, after notebooks 11 and 13 have run:  python3 companion/build.py

Every number in the page's prose is computed here from the output files, or from the design
parameters in src/bp/constants.py, and substituted into the template, so that the text, the tables
and the calculator agree; the two worked examples in the arithmetic section use round numbers and
say so. The build stops, naming the notebook to run, if an input file is missing. The footer states
the vintage, the source notebooks and the build date; the page is rebuilt whenever those notebooks
are rerun.
"""
import datetime
import glob
import json
import os
import re
import sys
import zoneinfo

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
OUTPUTS = os.path.join(REPO, "outputs")
OUT = os.path.join(SCRIPT_DIR, "industry_tilts_factor_exposures.html")
sys.path.insert(0, os.path.join(REPO, "src"))
from bp import constants as C  # noqa: E402  the design parameters, read from the same file the notebooks read


def need(pattern, notebook):
    """The one file matching pattern under outputs/, or a message naming the notebook that writes it."""
    hits = sorted(glob.glob(os.path.join(OUTPUTS, pattern)))
    if len(hits) != 1:
        sys.exit(f"companion/build.py: expected one file outputs/{pattern}, found {len(hits)}; run notebook {notebook} first")
    return hits[0]


provenance = json.load(open(need("provenance_french.json", "13")))
vintages = {m.group(1) for rec in provenance for m in [re.search(r"using the (\d{6}) CRSP", rec.get("vintage_line", ""))] if m}
if len(vintages) != 1:
    sys.exit(f"companion/build.py: expected one CRSP vintage in outputs/provenance_french.json, found {sorted(vintages)}")
VINTAGE = vintages.pop()

bm = pd.read_csv(need(f"attribution_betas_mean_{VINTAGE}.csv", "13"), index_col=0)
betas_last_file = need(f"attribution_betas_????-??_{VINTAGE}.csv", "13")
ba = pd.read_csv(betas_last_file, index_col=0)
w = pd.read_csv(need(f"attribution_benchmark_weights_{VINTAGE}.csv", "13"), index_col=0)
fm_file = need(f"factor_means_*_{VINTAGE}.csv", "13")
fm = pd.read_csv(fm_file, index_col=0)
summ = pd.read_csv(need(f"attribution_summary_{VINTAGE}.csv", "13"))
mcost = pd.read_csv(need(f"attribution_mandate_cost_{VINTAGE}.csv", "13")).set_index("variant")
opt = pd.read_csv(need(f"optimiser_report_{VINTAGE}.csv", "11"))
F = list(bm.columns)
assert F == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
assert list(bm.index) == list(ba.index) == list(w.index) and len(bm) == 49

NAMES = {
    "Agric": "Agriculture", "Food": "Food products", "Soda": "Candy and soda", "Beer": "Beer and liquor",
    "Smoke": "Tobacco products", "Toys": "Recreation", "Fun": "Entertainment", "Books": "Printing and publishing",
    "Hshld": "Consumer goods", "Clths": "Apparel", "Hlth": "Healthcare", "MedEq": "Medical equipment",
    "Drugs": "Pharmaceutical products", "Chems": "Chemicals", "Rubbr": "Rubber and plastic products",
    "Txtls": "Textiles", "BldMt": "Construction materials", "Cnstr": "Construction", "Steel": "Steel works",
    "FabPr": "Fabricated products", "Mach": "Machinery", "ElcEq": "Electrical equipment",
    "Autos": "Automobiles and trucks", "Aero": "Aircraft", "Ships": "Shipbuilding and railroad equipment",
    "Guns": "Defense", "Gold": "Precious metals", "Mines": "Non-metallic and industrial metal mining",
    "Coal": "Coal", "Oil": "Petroleum and natural gas", "Util": "Utilities", "Telcm": "Communication",
    "PerSv": "Personal services", "BusSv": "Business services", "Hardw": "Computers",
    "Softw": "Computer software", "Chips": "Electronic equipment", "LabEq": "Measuring and control equipment",
    "Paper": "Business supplies", "Boxes": "Shipping containers", "Trans": "Transportation",
    "Whlsl": "Wholesale", "Rtail": "Retail", "Meals": "Restaurants, hotels and motels", "Banks": "Banking",
    "Insur": "Insurance", "RlEst": "Real estate", "Fin": "Trading", "Other": "Firms in no other industry",
}
assert set(NAMES) == set(bm.index)
TAGS = {"Oil": "tilted", "Coal": "tilted", "Util": "tilted", "Smoke": "excluded", "Guns": "excluded",
        "Food": "bought", "Telcm": "bought", "Other": "bought", "Soda": "bought", "Agric": "bought"}

WM = w["mean weight"] / w["mean weight"].sum()
WA = w["weight 2026-08"] / w["weight 2026-08"].sum()
BENCH_M = bm.mul(WM, axis=0).sum()

# The design, read from the constants file: the tilt's industries and share, the exclusions, the bound.
TILT = list(C.TILT_INDUSTRIES)
EXCL = list(C.MANDATE_EXCLUSIONS)
BOUND_PTS = C.ACTIVE_WEIGHT_BOUND * 100
TILT_SHARE = C.TILT_MAX_SHARE_OF_BENCHMARK
assert set(TILT) <= set(bm.index) and set(EXCL) <= set(bm.index)
assert TILT == ["Coal", "Oil", "Util"] and EXCL == ["Smoke", "Guns"], "the template names these industries in its prose"

# The study's sales in its first evaluation month: the active weights of the sample covariance's
# portfolio under the tilt alone (notebook 11's first design, its set C3), from the optimiser's report.
FIRST_MONTH = sorted(opt["month"].unique())[0]
row0 = opt[(opt["month"] == FIRST_MONTH) & (opt["estimator"] == "sample") & (opt["data"] == "daily_3y") & (opt["set"] == "C3")]
assert len(row0) == 1, "one row for the sample covariance's tilt-only portfolio in the first month"
row0 = row0.iloc[0]
assert row0["binding: tilt"] == len(TILT), "the tilt binds for every tilted industry in the first month"
SALES = {k: round(float(row0[f"active {k} (pp)"]), 1) for k in TILT}     # Oil -7.6, Util -4.0, Coal -0.1
assert all(v <= 0 for v in SALES.values())
PRESETS = {
    "a": {**SALES, "Food": BOUND_PTS, "Telcm": BOUND_PTS, "Other": BOUND_PTS},
    "b": {"Smoke": -round(float(w.loc["Smoke", "mean weight"] * 100), 1), "Guns": -round(float(w.loc["Guns", "mean weight"] * 100), 1)},
    "c": {**SALES, "Banks": BOUND_PTS, "Fin": BOUND_PTS, "Insur": BOUND_PTS},
}
assert PRESETS["b"] == {"Smoke": -1.0, "Guns": -0.3}, PRESETS["b"]


def full_weights(points, weights=WM):
    """Active weights as fractions for all 49 industries, the remainder spread over the
    industries not named, in proportion to their benchmark weights."""
    a = pd.Series(0.0, index=bm.index)
    for k, v in points.items():
        a[k] = v / 100
    rest = [i for i in bm.index if i not in points]
    a[rest] += -a.sum() * weights[rest] / weights[rest].sum()
    return a


def exposure(a, betas=bm):
    return betas.mul(a, axis=0).sum()


MINUS = "−"


def n(x, d=2, sign=False):
    s = f"{abs(x):.{d}f}"
    if float(s) == 0:
        return s
    if x < 0:
        return MINUS + s
    return ("+" + s) if sign else s


P = {}


def expr(a, beta, bench):
    """The written-out part of one industry: active weight times the gap between its beta
    and the benchmark's."""
    inner = f"{n(beta, 3)} {MINUS} {n(bench, 3)}"
    if bench < 0:
        inner = f"{n(beta, 3)} + {n(-bench, 3)}"
    return f"{n(a, 3)} \u00d7 ({inner})"


mean_ret = fm["mean return per year"]
vol = fm["volatility per year"]

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def month_text(ym, short=False):
    y, mo = ym.split("-")
    name = MONTH_NAMES[int(mo) - 1]
    return (name[:3] if short else name) + " " + y


LAST_MONTH = re.search(r"attribution_betas_(\d{4}-\d{2})_", os.path.basename(betas_last_file)).group(1)
fm_first, fm_last = re.search(r"factor_means_(\d{4}-\d{2})_to_(\d{4}-\d{2})_", os.path.basename(fm_file)).groups()
assert fm_first == FIRST_MONTH and fm_last == LAST_MONTH, (fm_first, FIRST_MONTH, fm_last, LAST_MONTH)
MONTHS = int(summ["months"].iloc[0])
assert (summ["months"] == MONTHS).all() and int(fm["months"].iloc[0]) == MONTHS
P["months"] = str(MONTHS)
P["first_month_text"] = month_text(FIRST_MONTH)
P["last_month_text"] = month_text(LAST_MONTH)
P["first_month_short"] = month_text(FIRST_MONTH, True)
P["last_month_short"] = month_text(LAST_MONTH, True)
P["vintage"] = VINTAGE
P["vintage_text"] = month_text(VINTAGE[:4] + "-" + VINTAGE[4:])
P["build_date"] = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam")).strftime("%-d %B %Y")
P["tilt_list"] = ", ".join(TILT)
P["excl_list"] = ", ".join(EXCL)
P["bound_pts"] = n(BOUND_PTS, 0)
P["tilt_share_text"] = "half" if TILT_SHARE == 0.5 else n(TILT_SHARE * 100, 0) + "% of"
P["t_oil"] = n(-SALES["Oil"], 1)
P["t_util"] = n(-SALES["Util"], 1)
P["t_coal"] = n(-SALES["Coal"], 1)
oil_full = -2 * float(row0["active Oil (pp)"]) if TILT_SHARE == 0.5 else -float(row0["active Oil (pp)"]) / (1 - TILT_SHARE)
P["oil_full"] = n(oil_full, 1)
P["oil_half"] = n(oil_full * TILT_SHARE, 1)
assert P["oil_half"] == P["t_oil"]
P["c_buy_each"] = n(BOUND_PTS, 0)
excl_part = (mcost[[f for f in F if f != "Mkt-RF"]].sum(axis=1) * 1e4).abs()
P["excl_lo"] = n(excl_part.min(), 1)
P["excl_hi"] = n(excl_part.max(), 1)

# The portfolio section
P["w_banks"] = n(w.loc["Banks", "mean weight"] * 100, 1)
P["w_oil"] = n(w.loc["Oil", "mean weight"] * 100, 1)
P["w_softw"] = n(w.loc["Softw", "mean weight"] * 100, 1)
P["wa_chips"] = n(w.loc["Chips", "weight 2026-08"] * 100, 1)
P["wa_softw"] = n(w.loc["Softw", "weight 2026-08"] * 100, 1)
P["wa_oil"] = n(w.loc["Oil", "weight 2026-08"] * 100, 1)
P["w_smoke"] = n(w.loc["Smoke", "mean weight"] * 100, 1)
P["w_guns"] = n(w.loc["Guns", "mean weight"] * 100, 1)
P["w_coal"] = n(w.loc["Coal", "mean weight"] * 100, 1)
top3 = WM.sort_values(ascending=False).index[:3].tolist()
assert top3 == ["Banks", "Oil", "Softw"], top3
assert WA.sort_values(ascending=False).index[:2].tolist() == ["Chips", "Softw"]

# Step 1 spread example: Oil at -3 points, the rest spread
rest_w = 100 - w.loc["Oil", "mean weight"] * 100
P["rest_w_oil"] = n(rest_w, 1)
P["banks_share"] = n(3 * w.loc["Banks", "mean weight"] * 100 / rest_w, 2)
P["w_banks2"] = n(w.loc["Banks", "mean weight"] * 100, 2)
P["rest_w_oil2"] = n(rest_w, 2)
assert n(3 * float(P["w_banks2"]) / float(P["rest_w_oil2"]), 2) == P["banks_share"]
chk = full_weights({"Oil": -3.0})["Banks"] * 100
assert abs(chk - 3 * w.loc["Banks", "mean weight"] * 100 / rest_w) < 1e-5

# Map notes
for ind in ["Oil", "Util", "Smoke", "Guns", "Food", "Soda", "Coal", "Banks", "Fin", "Insur", "Autos", "FabPr",
            "Softw", "Gold", "Telcm"]:
    for f in F:
        P[f"b_{ind}_{f}"] = n(bm.loc[ind, f], 2)
        P[f"bs_{ind}_{f}"] = n(bm.loc[ind, f], 2, True)
        P[f"b3_{ind}_{f}"] = n(bm.loc[ind, f], 3)
for f in F:
    P[f"bench_{f}"] = n(BENCH_M[f], 2)
    P[f"bench3_{f}"] = n(BENCH_M[f], 3)
    P[f"benchs_{f}"] = n(BENCH_M[f], 2, True)
    P[f"ret_{f}"] = n(mean_ret[f] * 100, 2)
    P[f"vol_{f}"] = n(vol[f] * 100, 2)
P["ba_Oil_HML"] = n(ba.loc["Oil", "HML"], 2)


def rank(ind, f):
    return int((bm[f] > bm.loc[ind, f]).sum() + 1)


ORD = {1: "highest", 2: "second highest", 3: "third highest", 4: "fourth highest", 5: "fifth highest",
       6: "sixth highest"}
P["rank_oil_cma"] = ORD[rank("Oil", "CMA")]
P["rank_smoke_rmw"] = ORD[rank("Smoke", "RMW")]
P["rank_smoke_cma"] = ORD[rank("Smoke", "CMA")]
assert rank("Banks", "HML") == 1 and rank("Fin", "HML") == 2 and rank("Insur", "HML") == 3


def case(points):
    a = full_weights(points)
    e = exposure(a)
    c = e * mean_ret * 1e4
    rest = [i for i in bm.index if i not in points]
    r = a[rest].sum()
    beta_rest = bm.loc[rest].mul(WM[rest], axis=0).sum() / WM[rest].sum()
    gap = {}
    for k, v in points.items():
        gap[k] = (v / 100) * (bm.loc[k] - BENCH_M)
    gap["rest"] = r * (beta_rest - BENCH_M)
    tot_gap = sum(gap.values())
    assert (abs(tot_gap - e) < 1e-12).all()
    return a, e, c, gap, r


for key, pts in PRESETS.items():
    a, e, c, gap, r = case(pts)
    for f in F:
        P[f"{key}_e_{f}"] = n(e[f], 3, True)
        P[f"{key}_e4_{f}"] = n(e[f], 4, True)
        P[f"{key}_c_{f}"] = n(c[f], 1, True)
        P[f"{key}_cpct_{f}"] = n(e[f] * mean_ret[f] * 100, 3, True)
        for k in pts:
            P[f"{key}_g_{k}_{f}"] = n(gap[k][f], 4, True)
            P[f"{key}_x_{k}_{f}"] = expr(pts[k] / 100, bm.loc[k, f], BENCH_M[f])
        # parts shown in the text are rounded to 4 decimals; the remainder lines are the rounded
        # total minus the rounded parts, so that the numbers a reader adds up give the total shown
        sold = [k for k in pts if pts[k] < 0]
        tot4 = round(e[f], 4)
        tol = 0.00005 * (len(pts) + 1)     # each rounded part is within 0.00005 of its value
        others = tot4 - sum(round(gap[k][f], 4) for k in sold)
        assert abs(others - (e[f] - sum(gap[k][f] for k in sold))) < tol
        P[f"{key}_buys_{f}"] = n(others, 4, True)
        rest4 = tot4 - sum(round(gap[k][f], 4) for k in pts)
        assert abs(rest4 - gap["rest"][f]) < tol
        P[f"{key}_restg_{f}"] = n(rest4, 4, True)
        if abs(rest4) < 0.00005:
            P[f"{key}_restg_{f}"] = "less than 0.0001"
        P[f"{key}_named_buys_{f}"] = n(sum(round(gap[k][f], 4) for k in pts if pts[k] > 0), 4, True)
    P[f"{key}_ctot"] = n(c.sum(), 1, True)
    P[f"{key}_ctotpct"] = n(c.sum() / 100, 3, True)
    P[f"{key}_rest"] = n(r * 100, 1)
    P[f"{key}_nrest"] = str(49 - len(pts))
    P[f"{key}_c5"] = n(c.drop("Mkt-RF").sum(), 1, True)
    rest = [i for i in bm.index if i not in pts]
    rb = bm.loc[rest].mul(WM[rest], axis=0).sum() / WM[rest].sum()
    for f in F:
        P[f"{key}_restbeta_{f}"] = n(rb[f], 2)
    print(key, e.round(4).to_dict(), c.round(2).to_dict(), round(c.sum(), 2))

# preset b checks against the brief: profitability and investment move by 0.004 to 0.006, 1 to 2 bp each
_, eb, cb, _, _ = case(PRESETS["b"])
assert 0.004 <= abs(eb["RMW"]) <= 0.0065 and 0.004 <= abs(eb["CMA"]) <= 0.0065
assert 1 <= abs(cb["RMW"]) <= 2 and 1 <= abs(cb["CMA"]) <= 2
assert P["b_c_RMW"] == P["b_c_CMA"]
P["b_c_each"] = P["b_c_RMW"]
P["b_other_max"] = n(max(abs(eb[f]) for f in ["Mkt-RF", "SMB", "HML", "Mom"]), 3)
# preset a checks: size positive, value and investment negative
_, ea, ca, _, _ = case(PRESETS["a"])
assert ea["SMB"] > 0 and ea["HML"] < 0 and ea["CMA"] < 0
_, ec, cc, _, _ = case(PRESETS["c"])
assert max(abs(ea[f]) for f in ["Mkt-RF", "RMW", "Mom"]) < 0.01
assert max(abs(eb[f]) for f in ["SMB", "HML", "Mom"]) <= 0.003
assert abs(ec["HML"]) < 0.5 * abs(ea["HML"]) and ec["HML"] * ea["HML"] > 0, "the hedge cuts the value exposure by at least half without crossing zero"
assert abs(ec["CMA"]) > abs(ea["CMA"]) and abs(ec["RMW"]) > abs(ea["RMW"]) and ec["Mkt-RF"] > 0
P["c_hml_cut"] = n(100 * (1 - abs(ec["HML"]) / abs(ea["HML"])), 0)
P["c_cma_x"] = n(abs(ec["CMA"]) / abs(ea["CMA"]), 1)
P["c_rmw_x"] = n(abs(ec["RMW"]) / abs(ea["RMW"]), 1)
# coal check: halving coal at its average weight moves no exposure by more than 0.001
coal_move = (0.5 * w.loc["Coal", "mean weight"] * (bm.loc["Coal"] - BENCH_M)).abs().max()
assert coal_move < 0.001, coal_move

# The study's measured averages (one version: sample covariance on three years of daily returns)
row_t = summ[(summ["variant"] == "sample, daily 3y") & (summ["set"] == "C3 tilt only")].iloc[0]
row_m = summ[(summ["variant"] == "sample, daily 3y") & (summ["set"] == "C3")].iloc[0]
for f in F:
    P[f"st_e_{f}"] = n(row_t[f"exposure {f}"], 3, True)
    P[f"sm_e_{f}"] = n(row_m[f"exposure {f}"], 3, True)
P["st_factor"] = n(row_t["factor total (per year)"] * 1e4, 2, True)
P["st_resid"] = n(row_t["residual (per year)"] * 1e4, 2, True)
P["st_resid_u"] = n(row_t["residual (per year)"] * 1e4, 2)
P["st_active_u"] = n(row_t["active return (per year)"] * 1e4, 2)
P["st_active"] = n(row_t["active return (per year)"] * 1e4, 2, True)
assert abs(row_t["factor total (per year)"] + row_t["residual (per year)"] - row_t["active return (per year)"]) < 1e-12
st_hml = row_t["exposure HML"]
P["st_hml"] = n(abs(st_hml), 3)
P["unc_exp"] = n(st_hml * mean_ret["HML"] * 100, 3, True)
P["unc_exp_bp"] = n(abs(st_hml * mean_ret["HML"] * 1e4), 1)
P["unc_sd"] = n(abs(st_hml) * vol["HML"] * 100, 2)
P["unc_sd_bp"] = n(abs(st_hml) * vol["HML"] * 1e4, 0)
P["unc_ratio"] = n(vol["HML"] / mean_ret["HML"], 1)
mn = summ["factor share"].min(); mx = summ["factor share"].max()
P["fshare_lo"] = f"{mn*100:.0f}"
P["fshare_hi"] = f"{mx*100:.0f}"

# The data embedded in the page
DATA = {
    "factors": [
        {"code": "Mkt-RF", "name": "Market", "low": "market"},
        {"code": "SMB", "name": "Size", "low": "size"},
        {"code": "HML", "name": "Value", "low": "value"},
        {"code": "RMW", "name": "Profitability", "low": "profitability"},
        {"code": "CMA", "name": "Investment", "low": "investment"},
        {"code": "Mom", "name": "Momentum", "low": "momentum"},
    ],
    "ind": [
        {"c": i, "n": NAMES[i], "t": TAGS.get(i, ""),
         "bm": [round(float(bm.loc[i, f]), 6) for f in F],
         "ba": [round(float(ba.loc[i, f]), 6) for f in F],
         "wm": round(float(w.loc[i, "mean weight"]), 6),
         "wa": round(float(w.loc[i, "weight 2026-08"]), 6)}
        for i in bm.index
    ],
    "fmean": [round(float(mean_ret[f]), 6) for f in F],
    "fvol": [round(float(vol[f]), 6) for f in F],
    "presets": PRESETS,
    "study": {"tilt": [float(row_t[f"exposure {f}"]) for f in F],
              "all": [float(row_m[f"exposure {f}"]) for f in F]},
}

tpl = open(os.path.join(SCRIPT_DIR, "page_template.html"), encoding="utf-8").read()
missing = sorted(set(re.findall(r"\{\{(\w[\w-]*)\}\}", tpl)) - set(P))
assert not missing, missing
html = re.sub(r"\{\{(\w[\w-]*)\}\}", lambda m: P[m.group(1)], tpl)
assert "{{" not in html
html = html.replace("/*DATA*/null", json.dumps(DATA, separators=(",", ":")))
open(OUT, "w", encoding="utf-8").write(html)
print("written", os.path.relpath(OUT, REPO), len(html), "bytes; vintage", VINTAGE, "; months", MONTHS, FIRST_MONTH, "to", LAST_MONTH)
