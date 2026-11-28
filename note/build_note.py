"""Builds the note, note/B-P_note_2026-11.html and its PDF, from note/template.html and the tables committed in
results/202608/.

Usage, from the repository root, on any machine with a clone:
    python3 note/build_note.py [--no-pdf]

Sections 3.3 to 3.5, their three tables and every figure the text gives for the two naive portfolios are read from the
committed tables of notebooks 08 and 09 and from the tables in results/202608/source/, and written into the template's
{{name}} keys, so that no figure of those sections is typed by hand. The replication's sections and tables (3.1 and
3.2) stand in the template as they are, their figures read from the replication's tables when the note was written.
The PDF is the HTML printed by Chromium through Playwright on A4, with the author written into its metadata after
printing, because Chromium writes the title and not the author.
"""
import argparse
import os
import re

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
R = os.path.join(REPO, "results", "202608")
NAME = "B-P_note_2026-11"
HTML_OUT = os.path.join(SCRIPT_DIR, NAME + ".html")
PDF_OUT = os.path.join(SCRIPT_DIR, NAME + ".pdf")
FOOTER = ('<div style="width:100%;font:7.5pt Georgia,serif;color:#6b7280;padding:0 20mm;display:flex;justify-content:space-between">'
          '<span>Carlo Hofer &middot; Optimal versus naive diversification &middot; Note, November 2026</span>'
          '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>')

PATHS = ["sample, daily 3y", "ledoit_wolf, daily 3y", "factor, daily 3y", "pca, daily 3y", "sample, monthly 120",
         "robust, all five", "RiskMetrics, daily 5y"]
LABEL = {"sample, daily 3y": "Sample covariance, 3 years daily", "ledoit_wolf, daily 3y": "Ledoit-Wolf shrinkage, 3 years daily",
         "factor, daily 3y": "Six-factor model, 3 years daily", "pca, daily 3y": "Principal components, 3 years daily",
         "sample, monthly 120": "Sample covariance, 120 months", "robust, all five": "Robust (built on the five above)",
         "RiskMetrics, daily 5y": "RiskMetrics (exponentially weighted), 5 years daily"}
TARGETED = ["HML", "RMW", "CMA", "Mom"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def read(name, **kw):
    return pd.read_csv(os.path.join(R, name), **kw)


def f(x, d):
    """A number with d decimals and an ASCII minus."""
    return f"{x:.{d}f}"


def s(x, d):
    """A signed number with d decimals."""
    return f"{x:+.{d}f}"


def rng(values, d, sign=False, by_size=False):
    """The range of values as "lo to hi"; by_size orders negative ranges from the smaller to the larger magnitude."""
    v = sorted(values, key=abs) if by_size else sorted(values)
    lo, hi = v[0], v[-1]
    fmt = s if sign else f
    return f"{fmt(lo, d)} to {fmt(hi, d)}"


def month_words(ym):
    y, m = str(ym).split("-")
    return f"{MONTHS[int(m) - 1]} {y}"


def table(caption, head, rows, note, groups=None):
    """A table in the note's markup: the first column left-aligned, numbers right-aligned, group rows across the table."""
    out = ['<div class="tblock"><div class="tw"><div class="tscroll"><table class="num"><caption>' + caption + "</caption>",
           "<thead><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"]
    for r in rows:
        if isinstance(r, str):
            out.append(f'<tr><td class=l colspan={len(head)}><i>{r}</i></td></tr>')
        else:
            out.append("<tr>" + f"<td class=l>{r[0]}</td>" + "".join(f"<td>{c}</td>" for c in r[1:]) + "</tr>")
    out.append("</tbody></table></div></div>")
    out.append(f'<p class="tn">{note}</p></div>')
    return "\n".join(out)


def build():
    P = {}
    # --- the naive tilt (notebook 08) ---
    paired = read("naive_tilt_paired_tests_202608.csv")
    costs = read("naive_tilt_returns_and_costs_202608.csv", index_col=0)
    meas = read("naive_tilt_measures_202608.csv", index_col=0).loc["naive tilt"]
    monthly = read("naive_tilt_monthly_202608.csv")
    irn = read("naive_tilt_information_ratios_202608.csv", index_col=0)
    betn = read("naive_tilt_realised_betas_202608.csv", index_col=0)["realised beta"]
    attn = read("naive_tilt_attribution_summary_202608.csv", index_col=0).loc["naive tilt"]
    spread = read("naive_tilt_spread_202608.csv").iloc[0]
    irdn = read("naive_tilt_information_ratio_differences_202608.csv")
    roll = read("source/rolling_evaluation_202608.csv")
    roll = roll[roll["set"] == "C3 tilt only"].set_index("variant").loc[PATHS]
    atts = read("source/attribution_summary_202608.csv")
    atts = atts[atts["set"] == "C3 tilt only"].set_index("variant").loc[PATHS]
    tl = [f"{v} | C3 tilt only" for v in PATHS]
    paired = paired.set_index("path").loc[tl]
    d = paired["difference (bp)"]
    P["nt_te"] = f(paired["naive tilt (bp)"].iloc[0], 1)
    P["nt_paths_te"] = rng(paired["path (bp)"], 1)
    P["nt_diff_lo"], P["nt_diff_hi"] = f(d.min(), 1), f(d.max(), 1)
    P["nt_diff_lo0"], P["nt_diff_hi0"] = f(d.min(), 0), f(d.max(), 0)
    P["nt_share_lo"] = f(100 * d.min() / paired["naive tilt (bp)"].iloc[0], 0)
    P["nt_share_hi"] = f(100 * d.max() / paired["naive tilt (bp)"].iloc[0], 0)
    assert (paired["Holm p-value"] < 0.05).all() and (d > 0).all()
    P["nt_holm_lo"], P["nt_holm_hi"] = f(paired["Holm p-value"].min(), 4), f(paired["Holm p-value"].max(), 4)
    lo_row, hi_row = paired.loc[d.idxmin()], paired.loc[d.idxmax()]
    assert d.idxmin().startswith("sample, monthly 120") and d.idxmax().startswith("RiskMetrics")
    P["nt_min_diff"], P["nt_min_int"] = f(lo_row["difference (bp)"], 1), f"{f(lo_row['lower (bp)'], 1)} to {f(lo_row['upper (bp)'], 1)}"
    P["nt_max_diff"], P["nt_max_int"] = f(hi_row["difference (bp)"], 1), f"{f(hi_row['lower (bp)'], 1)} to {f(hi_row['upper (bp)'], 1)}"
    P["nt_corr"] = rng(paired["correlation"], 2)
    nt_sum = sum(meas[f"mean exposure {fac}"] for fac in TARGETED)
    p_sum = sum(atts[f"exposure {fac}"] for fac in TARGETED)
    P["nt_x_sum"], P["p_x_sum"] = f(nt_sum, 3), rng(p_sum, 3, by_size=True)
    assert nt_sum < 0 and (p_sum < 0).all() and (p_sum.abs() < abs(nt_sum)).all()   # the text: the paths' total is smaller
    P["nt_turn"] = f(100 * meas["turnover (one-way)"], 2)
    P["nt_paths_turn"] = rng(100 * roll["turnover (one-way)"], 2)
    P["nt_first"] = f(100 * meas["first month turnover"], 1)
    P["nt_cap"] = str(int(meas["months above the turnover cap"]))
    rel = sorted(set(roll["relaxed months"].astype(int)))
    P["nt_relaxed"] = " or ".join(str(x) for x in rel)
    P["nt_beta"] = f(betn.loc["naive tilt"], 3)
    P["nt_paths_beta"] = rng(betn.loc[tl], 3)
    P["removed_lo"] = f(100 * monthly["removed weight"].min(), 1)
    P["removed_hi"] = f(100 * monthly["removed weight"].max(), 1)
    P["nt_gross"] = s(1e4 * meas["active return (gross)"], 1)
    P["nt_paths_gross"] = rng(1e4 * roll["active return (gross)"], 1, sign=True)
    P["nt_net"] = s(1e4 * meas["net active return at 100 bp"], 1)
    P["nt_paths_net"] = rng(1e4 * roll["net active return at 100 bp"], 1, sign=True)
    g = irdn[irdn["ratio"] == "gross"]
    assert (g["p-value"] >= 0.05).all()                      # the text: none statistically significant before costs
    P["nt_irgap"] = rng(g["difference"], 2)
    P["nt_ir_pse"] = rng(g["paired standard error"], 2)
    h = irdn[irdn["ratio"] == "at 100 bp"]
    P["nt_ir_100_alone"] = ["none", "one", "two", "three", "four", "five", "six", "seven"][int((h["p-value"] < 0.05).sum())]
    P["nt_ir_100_holm"] = ["none", "one", "two", "three", "four", "five", "six", "seven"][int((h["Holm p-value"] < 0.05).sum())]
    assert (irdn["Holm p-value"] >= 0.05).all()              # the text: none after Holm's correction, at any cost
    P["spread_mean"] = s(100 * spread["mean per year"], 2)
    P["spread_sd"] = f(100 * spread["standard deviation per year"], 2)
    P["spread_t"] = f(spread["t-ratio"], 2)
    P["nt_resid"] = s(1e4 * attn["residual (per year)"], 1)
    P["p_resid"] = rng(1e4 * atts["residual (per year)"], 1, sign=True)

    # --- the tilted index (notebook 09) ---
    boot = read("tilted_index_bootstrap_202608.csv").set_index("path")
    beside = read("tilted_index_beside_paths_202608.csv", index_col=0)
    meas2 = read("tilted_index_measures_202608.csv", index_col=0).loc["tilted index"]
    k = read("tilted_index_k_202608.csv").iloc[0]
    kat = read("tilted_index_k_set_at_202608.csv", index_col=0)["months"]
    mon2 = read("tilted_index_monthly_202608.csv")
    budgets = read("tilted_index_budgets_75_and_150_202608.csv", index_col=0)
    irt = read("tilted_index_information_ratios_202608.csv", index_col=0)
    bett = read("tilted_index_realised_betas_202608.csv", index_col=0)["realised beta"]
    att2 = read("tilted_index_attribution_summary_202608.csv", index_col=0).loc["tilted index"]
    irdt = read("tilted_index_information_ratio_differences_202608.csv")
    foe = read("source/factor_objective_evaluation_202608.csv", index_col=0)
    foa = read("source/factor_objective_attribution_202608.csv").set_index("path")
    fl = [f"{v} | 100" for v in PATHS]
    boot = boot.loc[fl]
    paths2 = beside.loc[fl]
    assert (boot["Holm p-value"] < 0.05).all() and (boot["difference"] < 0).all()
    P["ti_obj"] = f(meas2["mean objective"], 3)
    P["ti_te"] = f(1e4 * meas2["realised TE"], 1)
    P["ti_epb"] = f(meas2["exposure per bp of realised TE"], 6)
    P["ti_paths_obj"] = rng(paths2["mean objective"], 3)
    P["ti_paths_te"] = rng(1e4 * paths2["realised TE"], 1)
    P["ti_paths_epb"] = rng(paths2["exposure per bp of realised TE"], 6)
    ratio = paths2["exposure per bp of realised TE"] / meas2["exposure per bp of realised TE"]
    P["ti_ratio_lo"], P["ti_ratio_hi"] = f(ratio.min(), 1), f(ratio.max(), 1)
    assert boot["Holm p-value"].round(3).nunique() == 1
    P["ti_holm"] = f(boot["Holm p-value"].iloc[0], 3)
    assert (boot["upper"] < 0).all()
    te_lo, te_hi = (1e4 * paths2["realised TE"]).min(), (1e4 * paths2["realised TE"]).max()
    assert te_lo < 1e4 * meas2["realised TE"] < te_hi
    b75 = budgets.loc[[i for i in budgets.index if i.endswith("| 75")], "exposure per bp of realised TE"]
    b150 = budgets.loc[[i for i in budgets.index if i.endswith("| 150")], "exposure per bp of realised TE"]
    assert b75.min() > meas2["exposure per bp of realised TE"]
    P["ti_b75"], P["ti_b150"] = rng(b75, 6), rng(b150, 6)
    P["k_bound"], P["k_floor"] = str(int(k["months set by the bound"])), str(int(k["months set by the floor"]))
    P["k_banks"], P["k_softw"] = str(int(kat.loc["Banks"])), str(int(kat.loc["Softw"]))
    assert kat.index[0] == "Banks" and kat.index[1] == "Softw"
    floor = mon2[mon2["k set by"] == "floor"]
    assert set(floor["k set at"]) == {"Gold"}
    P["k_floor_first"], P["k_floor_last"] = month_words(floor["month"].min()), month_words(floor["month"].max())
    P["k_median"] = f(k["k median"], 3)
    P["ti_turn"] = f(100 * meas2["turnover (one-way)"], 2)
    P["ti_paths_turn"] = rng(100 * paths2["turnover (one-way)"], 2)
    P["ti_first"] = f(100 * meas2["first month turnover"], 1)
    P["ti_cap"] = str(int(meas2["months above the turnover cap"]))
    rel2 = foe.loc[fl, "relaxed months"].astype(int)
    P["ti_relaxed"] = f"{rel2.min()} to {rel2.max()}"
    P["ti_beta"] = f(bett.loc["tilted index"], 3)
    P["ti_paths_beta"] = rng(bett.loc[fl], 3)
    P["ti_gross"] = s(1e4 * meas2["active return (gross)"], 1)
    P["ti_paths_gross"] = rng(1e4 * paths2["active return (gross)"], 1, sign=True)
    P["ti_net"] = s(1e4 * meas2["net active return at 100 bp"], 1)
    P["ti_paths_net"] = rng(1e4 * paths2["net active return at 100 bp"], 1, sign=True)
    g2 = irdt[irdt["ratio"] == "gross"]
    P["ti_irgap"] = rng(g2["difference"], 2)
    P["ti_ir_pse"] = rng(g2["paired standard error"], 2)
    assert (irdt["p-value"] >= 0.05).all()                   # the text: under the factor objective none, at any cost
    rx = read("tilted_index_realised_exposure_202608.csv", index_col=0)
    rxp, rxi = rx.loc[fl], rx.loc["tilted index"]
    assert (rxp["Holm p-value"] >= 0.05).all()               # the text: no difference in realised exposure is significant
    assert abs(rxi["forecast exposure per bp"] - meas2["exposure per bp of realised TE"]) < 5e-9   # the tables print 8 to 10 decimals
    assert (abs(rxp["forecast exposure per bp"] - paths2["exposure per bp of realised TE"]) < 5e-9).all()
    P["ti_rratio_lo"], P["ti_rratio_hi"] = f(rxp["realised multiple of the tilted index"].min(), 1), f(rxp["realised multiple of the tilted index"].max(), 1)
    P["ti_rratio2_lo"], P["ti_rratio2_hi"] = f(rxp["realised multiple of the tilted index"].min(), 2), f(rxp["realised multiple of the tilted index"].max(), 2)
    P["ti_rx_frac"] = rng(rxp["realised over forecast"], 2)
    P["ti_rx_index"] = f(rxi["realised over forecast"], 1)
    P["ti_rx_epb"] = f(rxi["realised exposure per bp"], 6)
    P["ti_rx_holm"] = rng(rxp["Holm p-value"], 3) if rxp["Holm p-value"].round(3).nunique() > 1 else f(rxp["Holm p-value"].iloc[0], 3)
    P["fp_targ"] = rng(1e4 * foa.loc[fl, "targeted total (per year)"], 1, sign=True)
    P["fp_resid"] = rng(1e4 * foa.loc[fl, "residual (per year)"], 1, sign=True, by_size=True)
    P["ti_targ"] = s(1e4 * att2["targeted total (per year)"], 1)
    P["fp_ftot"] = rng(1e4 * foa.loc[fl, "factor total (per year)"], 1, sign=True)
    P["ti_ftot"] = s(1e4 * att2["factor total (per year)"], 1)
    P["ti_resid"] = s(1e4 * att2["residual (per year)"], 1)

    # --- the three tables ---
    src = "Source: Kenneth R. French Data Library and author's calculations. Monthly, July 1979 to August 2026, 49 US industries, USD."
    rows = []
    for v in PATHS:
        p, c = paired.loc[f"{v} | C3 tilt only"], costs.loc[f"{v} | C3 tilt only"]
        rows.append([LABEL[v], f(p["path (bp)"], 1), s(p["difference (bp)"], 1), f"{s(p['lower (bp)'], 1)} to {s(p['upper (bp)'], 1)}",
                     f(p["Holm p-value"], 4), f(p["correlation"], 2), f(100 * c["turnover (one-way)"], 2),
                     s(c["active return (gross) (bp)"], 1), s(c["net active return at 100 bp (bp)"], 1)])
    c = costs.loc["naive tilt"]
    rows.append(["Naive tilt", f(c["realised TE (bp)"], 1), "", "", "", "", f(100 * c["turnover (one-way)"], 2),
                 s(c["active return (gross) (bp)"], 1), s(c["net active return at 100 bp (bp)"], 1)])
    P["table4"] = table(
        "Table 4. The naive tilt and the seven optimised paths under the tilt, July 1979 to August 2026 (566 months)",
        ["Covariance estimate", "Realised tracking error, bp a year", "Naive tilt minus path, bp a year", "95% interval",
         "Holm p-value", "Correlation", "One-way turnover, % a month", "Active return, bp a year",
         "Net of 100 bp per unit of turnover, bp a year"], rows,
        "Each path is an optimised portfolio of the companion study under the tilt, made with one of six covariance estimators or as the robust portfolio built from five of them. The difference is "
        "the naive tilt's realised tracking error minus the path's, with its 95 per cent interval from the paired variance test "
        "of Ledoit and Wolf (2011) in its bootstrap form, blocks of 12 months and 2,000 resamples. The Holm p-value corrects the "
        "seven comparisons. The correlation is that of the two monthly active returns. Active returns are simulated and "
        "annualised, gross and net of 100 basis points per unit of one-way turnover. " + src +
        " results/202608/naive_tilt_paired_tests_202608.csv and naive_tilt_returns_and_costs_202608.csv, notebook 08.")
    rows = []
    for v in PATHS:
        b, p, r = boot.loc[f"{v} | 100"], paths2.loc[f"{v} | 100"], rxp.loc[f"{v} | 100"]
        rows.append([LABEL[v], f(1e4 * p["realised TE"], 1), f(p["mean objective"], 3), f(p["exposure per bp of realised TE"], 6),
                     f(b["difference"], 6), f"{f(b['lower'], 6)} to {f(b['upper'], 6)}", f(b["Holm p-value"], 3),
                     f(r["realised exposure per bp"], 6), f(r["Holm p-value"], 3),
                     f(100 * p["turnover (one-way)"], 2), s(1e4 * p["active return (gross)"], 1), s(1e4 * p["net active return at 100 bp"], 1)])
    rows.append(["Tilted index", f(1e4 * meas2["realised TE"], 1), f(meas2["mean objective"], 3), f(meas2["exposure per bp of realised TE"], 6),
                 "", "", "", f(rxi["realised exposure per bp"], 6), "", f(100 * meas2["turnover (one-way)"], 2), s(1e4 * meas2["active return (gross)"], 1),
                 s(1e4 * meas2["net active return at 100 bp"], 1)])
    P["table5"] = table(
        "Table 5. The tilted index and the seven optimised paths under the factor objective, budget 100 basis points a year, "
        "July 1979 to August 2026 (566 months)",
        ["Covariance estimate", "Realised tracking error, bp a year", "Mean forecast exposure", "Forecast exposure per bp",
         "Tilted index minus path", "95% interval", "Holm p-value", "Realised exposure per bp<sup>a</sup>", "Holm p-value<sup>a</sup>",
         "One-way turnover, % a month", "Active return, bp a year", "Net of 100 bp per unit of turnover, bp a year"], rows,
        "Each path is an optimised portfolio of the companion study under the factor objective, made with one of six covariance estimators or as the robust portfolio built from five of them. The "
        "forecast exposure is the factor objective, the sum of the active exposures to value, profitability, investment and momentum "
        "computed with the betas of the three years before each month, and its mean is over the 566 months. The forecast exposure "
        "per basis point divides it by the realised tracking error in basis points. The difference and its 95 per cent interval "
        "come from 2,000 circular block bootstrap resamples of the months in blocks of 12, the same months drawn for both "
        "portfolios, and the p-value is two-sided. The Holm p-value corrects the seven comparisons. "
        "<sup>a</sup> Added after the results were known: the realised exposure, the sum of the slopes on the four factors in a "
        "regression of the 566 monthly active returns on the six factors' monthly returns, per basis point of realised tracking "
        "error, and the Holm p-value of the tilted index minus the path, from the same resamples. Active returns are simulated "
        "and annualised. " + src + " results/202608/tilted_index_bootstrap_202608.csv, tilted_index_beside_paths_202608.csv "
        "and tilted_index_realised_exposure_202608.csv, notebook 09.")

    def att_row(label, ir, att, targeted):
        return [label, f"{f(ir['information ratio (gross)'], 3)} ({f(ir['standard error (gross)'], 3)})",
                f"{f(ir['information ratio at 100 bp'], 3)} ({f(ir['standard error at 100 bp'], 3)})",
                f"{s(1e4 * att['factor total (per year)'], 1)} ({f(1e4 * att['factor total (standard error)'], 1)})",
                s(1e4 * targeted, 1),
                f"{s(1e4 * att['residual (per year)'], 1)} ({f(1e4 * att['residual (standard error)'], 1)})",
                s(1e4 * att["active return (per year)"], 1)]

    rows = ["Under the tilt", att_row("Naive tilt", irn.loc["naive tilt"], attn, attn["targeted total (per year)"])]
    for v in PATHS:
        a = atts.loc[v]
        rows.append(att_row(LABEL[v], irn.loc[f"{v} | C3 tilt only"], a, sum(a[f"contribution {x} (per year)"] for x in TARGETED)))
    rows += ["Under the factor objective, budget 100 bp a year", att_row("Tilted index", irt.loc["tilted index"], att2, att2["targeted total (per year)"])]
    for v in PATHS:
        a = foa.loc[f"{v} | 100"]
        rows.append(att_row(LABEL[v], irt.loc[f"{v} | 100"], a, a["targeted total (per year)"]))
    P["table6"] = table(
        "Table 6. Information ratios and the attribution of the active return, July 1979 to August 2026 (566 months)",
        ["Portfolio", "Information ratio, gross (s.e.)", "Information ratio net of 100 bp (s.e.)",
         "Factor contributions, bp a year (s.e.)", "Of which the four targeted factors, bp a year",
         "Residual, bp a year (s.e.)", "Active return, bp a year"], rows,
        "The information ratio is the active return per year over the realised tracking error, before costs and net of 100 basis "
        "points per unit of one-way turnover, with its standard error from 2,000 block bootstrap resamples of the months, the "
        "cost held at its full-sample figure. A contribution is the active exposure to a factor times the factor's return in the "
        "month, and the residual is the active return minus the six contributions. The standard errors of the contributions and "
        "the residual take the months as independent. Under the tilt, the targeted factors' contribution of each path is the sum "
        "of its four contributions. " + src + " results/202608/naive_tilt_information_ratios_202608.csv, "
        "naive_tilt_attribution_summary_202608.csv, tilted_index_information_ratios_202608.csv and "
        "tilted_index_attribution_summary_202608.csv, notebooks 08 and 09; for the paths, results/202608/source/"
        "attribution_summary_202608.csv and factor_objective_attribution_202608.csv.")
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true", help="write the HTML only")
    args = ap.parse_args()
    P = build()
    tpl = open(os.path.join(SCRIPT_DIR, "template.html"), encoding="utf-8").read()
    keys = set(re.findall(r"\{\{(\w+)\}\}", tpl))
    assert not keys - set(P), sorted(keys - set(P))
    assert not set(P) - keys, sorted(set(P) - keys)
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: P[m.group(1)], tpl)
    assert "{{" not in page and chr(0x2014) not in page
    open(HTML_OUT, "w", encoding="utf-8").write(page)
    print("written", os.path.relpath(HTML_OUT, REPO), len(page), "bytes")
    if args.no_pdf:
        return
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader, PdfWriter
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        pg.goto("file://" + HTML_OUT)
        pg.emulate_media(media="print")
        pg.wait_for_load_state("networkidle")
        pg.pdf(path=PDF_OUT, format="A4", print_background=True, display_header_footer=True,
               header_template="<span></span>", footer_template=FOOTER,
               margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"})
        browser.close()
    reader = PdfReader(PDF_OUT)
    writer = PdfWriter(clone_from=reader)
    title = re.search(r"<title>(.*?)</title>", page).group(1)
    subject = re.search(r'<meta name="description" content="([^"]*)">', page).group(1).replace("&#x27;", "'")
    writer.add_metadata({"/Title": title, "/Author": "Carlo Hofer", "/Subject": subject, "/Creator": "HTML rendered to PDF with Chromium"})
    with open(PDF_OUT, "wb") as fh:
        writer.write(fh)
    print("written", os.path.relpath(PDF_OUT, REPO), os.path.getsize(PDF_OUT), "bytes,", len(reader.pages), "pages")


if __name__ == "__main__":
    main()
