"""
Builds the notebooks in notebooks/ from this file and from the modules in src/bp/.

A .ipynb is JSON with outputs and execution counts stored beside the code, so a
hand-edited notebook cannot be reviewed as a diff. The notebooks here are build
artefacts: this script is the source of truth for the prose, and src/bp/ is the
source of truth for the code. Each notebook writes the modules it needs into
src/bp/ with %%writefile cells, so it runs standalone in Colab from a blank
runtime, and the same modules run from the repository checkout.

Run:  python3 build_notebooks.py
Notebooks are written without outputs. Never commit a notebook with outputs.

Carlo Hofer, 2026.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src" / "bp"
OUT = ROOT / "notebooks"


def _lines(src: str) -> list[str]:
    """Split text into the list-of-strings form a .ipynb expects (each line keeps its newline)."""
    parts = src.split("\n")
    return [p + "\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text.strip("\n"))}


def code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": _lines(text.strip("\n"))}


def writefile(relpath: str) -> dict:
    """A cell that writes one module from src/bp/ so the notebook runs from a blank runtime."""
    body = (SRC / relpath).read_text()
    return code(f"%%writefile src/bp/{relpath}\n{body}")


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }


def write(name: str, cells: list[dict]) -> pathlib.Path:
    OUT.mkdir(exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(notebook(cells), indent=1, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------------------
# 01: the French data loader
# ---------------------------------------------------------------------------

NB01 = [
    md("""
# 01. The data: Ken French's library, downloaded and counted

**Terms used in this notebook.** Vintage: the version of Ken French's files on the download date, named by the release of the CRSP database they were built from (202607 is the July 2026 release). Provenance: the record of what was downloaded, when, with its checksum and vintage. Factor: a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones. Risk-free rate: the return on a one-month US Treasury bill, the closest thing to a return with no risk. Excess return: a return minus the risk-free rate over the same month. Estimation window: the M months of past returns a rule sees when it forms its weights, 120 here. Rolling evaluation: moving the window forward one month at a time, forming the weights, and recording the return of the month after the window. Out-of-sample: measured on months the rule had not seen when it formed its weights. In-sample: measured on the same months that were used to form the weights. Sharpe ratio: the average monthly return above the risk-free rate, divided by the standard deviation of that return; the reward earned per unit of risk taken. Turnover: the fraction of the portfolio bought and sold at a rebalance, summed over the assets. Band: the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover. Gated: said of a cell the band applies to. Verdict: pass or MISS for a gated cell.

**What this notebook does.** It downloads the six Ken French files this project uses, records what it downloaded (date, URL, SHA-256 of the zip, and the CRSP vintage French prints at the top of each file), parses each file into monthly tables, and counts what is in them against what DeMiguel, Garlappi and Uppal (2009) say they used.

**Why it comes first.** Every number in the project is computed from these files, and French revises history: a return from 1985 can differ between the file served today and the one served last year. A replication that misses a published number by 0.01 has to be able to say whether the code or the vintage moved. The provenance record written here makes that possible, and it is attached to every later output.

**What I expect to see, and where it comes from.**

- The three portfolio files (10 industries, 49 industries, 25 size-and-value portfolios) and the three-factor file run monthly from 1926-07. On the vintage I read on 10 September 2026 (CRSP 202607) that is 1,201 rows to 2026-07; a later vintage adds one row per month. The five-factor file starts in 1963-07 (757 rows on that vintage) and the momentum factor in 1927-01.
- DGU's sample is 1963-07 to 2004-11 (their Table 2), which is **497 months**. With their 120-month estimation window the out-of-sample period is 1973-07 to 2004-11, **377 months**. Both counts are asserted below.
- Their four French-sourced datasets have N = 11, 3, 21 and 24 assets (Table 2). The 21 and 24 come from 20 of the 25 size-and-value portfolios: DGU drop the five largest-size portfolios (their footnote 24), because the market, SMB and HML are almost a linear combination of all 25.
- In French's 49-industry file nine industries have gaps coded -99.99 in the early decades. All 49 are populated from **1969-07**; the extension in later notebooks starts there.
- One number that is already a replication check: DGU's Table 3 reports the Sharpe ratio of the value-weighted market, "vw", as 0.1138 in every French-sourced column. That is the monthly Sharpe ratio of French's Mkt-RF over the out-of-sample window. The same calculation on today's vintage is printed beside it. The two differ because the vintages differ, and the size of the difference shows how much revision the sample has absorbed since 2009.
"""),
    md("""
## The constants file

Every band, gate, sample boundary and design parameter the project uses lives in one module, `src/bp/constants.py`, with the source of each number beside it. The notebooks read these names and never introduce numbers of their own. The cell below writes that module into the runtime so this notebook runs from scratch; in the repository the file is the same text.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    md("""
## The loader

A French CSV holds between two and ten blocks, each announced by a title line, then a header row that starts with a comma, then rows that start with a date (six digits for months, four for years). Returns are in percent and missing values are coded -99.99 or -999. The loader splits the file into blocks, indexes each by a monthly `Period`, converts percent to decimal once, replaces the missing codes with NaN, and records provenance for the zip it read.
"""),
    writefile("french_loader.py"),
    md("""
## Download and record

Six files. The table shows what was fetched and the vintage line French prints at the top of each. The record is written to `outputs/provenance_french.json`, which later notebooks read so that every output can name the vintage it was computed on.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import pandas as pd
import numpy as np
from bp import constants as C
from bp import french_loader as fl

pd.set_option("display.width", 160)
pd.set_option("display.max_colwidth", 70)

records = [fl.download(key) for key in C.FRENCH_FILES]
path = fl.write_provenance(records)
prov = pd.DataFrame(records)[["key", "filename", "zip_bytes", "zip_sha256", "download_time_local", "vintage_line"]]
prov["zip_sha256"] = prov["zip_sha256"].str[:16] + "..."
print("provenance written to", path)
prov
"""),
    md("""
## What is in each file

One row per block. The first block of each portfolio file is the value-weighted monthly return, which is the one the project uses; the 49-industry file also carries the number of firms and the average firm size per industry per month, which is how the cap weights of the industries are derived in notebook 08.
"""),
    code("""
summaries = pd.concat([fl.block_summary(key) for key in C.FRENCH_FILES], ignore_index=True)
summaries
"""),
    md("""
## Count first

Each check below is an assertion. If a later vintage moves a count, the cell fails and names the count. A silent change in the sample would be worse than a stopped notebook.
"""),
    code("""
f3  = fl.load_monthly("factors3", 0)
f5  = fl.load_monthly("factors5", 0)
mom = fl.load_monthly("momentum", 0)
i10 = fl.load_monthly("ind10", 0)
i49 = fl.load_monthly("ind49", 0)
p25 = fl.load_monthly("size_bm25", 0)

# 1. The DGU sample window: 497 months, 377 of them out of sample.
window = slice(pd.Period(C.DGU_SAMPLE_START, "M"), pd.Period(C.DGU_SAMPLE_END, "M"))
T = len(f3.loc[window])
assert T == C.DGU_EXPECTED_T, f"DGU window holds {T} months, expected {C.DGU_EXPECTED_T}"
assert T - C.DGU_ESTIMATION_WINDOW == C.DGU_EXPECTED_OOS
print(f"DGU sample {C.DGU_SAMPLE_START} to {C.DGU_SAMPLE_END}: T = {T} months, out of sample = {T - C.DGU_ESTIMATION_WINDOW}")

# 2. No missing values inside the DGU window, in any file the replication uses.
for name, frame in [("ind10", i10), ("size_bm25", p25), ("factors3", f3), ("momentum", mom)]:
    n_missing = int(frame.loc[window].isna().sum().sum())
    assert n_missing == 0, f"{name} has {n_missing} missing values inside the DGU window"
    assert len(frame.loc[window]) == T, f"{name} has {len(frame.loc[window])} rows in the DGU window"
print("no missing values in the DGU window in ind10, size_bm25, factors3, momentum")

# 3. The 20 of 25: drop the five largest-size portfolios (DGU footnote 24).
big = [c for c in p25.columns if c.startswith("BIG") or c.startswith("ME5")]
assert len(big) == 5, big
p20 = p25.drop(columns=big)
assert p20.shape[1] == 20
print("dropped from the 25:", big)

# 4. Asset counts per DGU dataset, against Table 2.
counts = {
    "Industry":    i10.shape[1] + 1,
    "MKT/SMB/HML": 3,
    "FF-1-factor": p20.shape[1] + 1,
    "FF-4-factor": p20.shape[1] + 4,
}
for name, n in counts.items():
    assert n == C.DGU_DATASETS[name]["N"], (name, n)
print("N per dataset:", counts)

# 5. The 49 industries: which have gaps, and from when all 49 are populated.
gaps = i49.isna().sum()
gaps = gaps[gaps > 0]
first_full = i49.dropna(how="any").index[0]
assert str(first_full) == C.EXT_SAMPLE_START, f"all 49 industries populated from {first_full}, constants say {C.EXT_SAMPLE_START}"
assert not i49.loc[first_full:].isna().any().any()
print("industries with early gaps (months missing):", gaps.to_dict())
print("all 49 industries populated from", first_full, "to", i49.index[-1], "=", len(i49.loc[first_full:]), "months")

# 6. Tilt industries exist under the names the constants use.
assert all(t in i49.columns for t in C.TILT_INDUSTRIES), C.TILT_INDUSTRIES
print("tilt industries present:", C.TILT_INDUSTRIES)
"""),
    md("""
## One replication number, before any rule exists

DGU's "vw" row is the value-weighted market held without trading. Its Sharpe ratio is the mean of monthly Mkt-RF divided by its standard deviation over the out-of-sample months. DGU report 0.1138. The cell prints the same quantity on today's vintage, and for reference on the full 497-month window as well.
"""),
    code("""
oos = slice(pd.Period(C.DGU_SAMPLE_START, "M") + C.DGU_ESTIMATION_WINDOW, pd.Period(C.DGU_SAMPLE_END, "M"))
mkt_oos = f3.loc[oos, "Mkt-RF"]
mkt_full = f3.loc[window, "Mkt-RF"]
sr_oos = mkt_oos.mean() / mkt_oos.std(ddof=1)
sr_full = mkt_full.mean() / mkt_full.std(ddof=1)
print(f"out-of-sample window {oos.start} to {oos.stop}: {len(mkt_oos)} months")
print(f"Sharpe ratio of Mkt-RF, out of sample : {sr_oos:.4f}   (DGU Table 3, vw: 0.1138)")
print(f"Sharpe ratio of Mkt-RF, full DGU window: {sr_full:.4f}")
print(f"difference to the published 0.1138: {sr_oos - 0.1138:+.4f}  (band for the rules' Sharpe ratios: {C.BAND_SHARPE_ABS})")
"""),
    md("""
## What this notebook established, and what could be wrong

The six files parse, the DGU window holds 497 months with no gaps, the asset counts match Table 2, and all 49 industries are populated from 1969-07. The market Sharpe ratio on today's vintage sits within 0.0025 of the 0.1138 DGU printed, which is the size of revision to expect on the rule rows too.

Three things this does not settle. French's risk-free rate is the one-month Treasury bill; DGU describe theirs as the 90-day bill taken from French's site, and French's site only carries the one-month series, so I use that. The vintage line names the CRSP cut French built the file from and nothing else; two files with the same vintage line can still differ if French changed a method. And the checks above count rows and columns; they do not verify a single return value, which only the replication itself can do.
"""),
]


# ---------------------------------------------------------------------------
# 02: 1/N against sample-based mean-variance
# ---------------------------------------------------------------------------

NB02 = [
    md("""
# 02. 1/N against sample-based mean-variance: the rolling out-of-sample test

**Terms used in this notebook.** Risk-free rate: the return on a one-month US Treasury bill, the closest thing to a return with no risk. Excess return: a return minus the risk-free rate over the same month. Sharpe ratio: the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken. Certainty-equivalent return (CEQ): the average return minus half the variance (times a risk aversion of one); the sure monthly return an investor would accept in place of the risky one. Turnover: the fraction of the portfolio bought and sold at a rebalance, summed over the assets; a turnover of 0.02 means that 2% of the portfolio changes hands in the month. Estimation window: the M months of past returns a rule sees when it forms its weights, 120 here. Rolling evaluation: moving the window forward one month at a time, forming the weights, and recording the return of the month after the window. Out-of-sample: measured on months the rule had not seen when it formed its weights. In-sample: measured on the same months that were used to form the weights. Estimation error: the difference between a mean or covariance estimated from a window and its true value. Band: the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover. Gated: said of a cell the band applies to. Verdict: pass or MISS for a gated cell. Fragility test: adding small random noise to every return and rerunning a rule fifty times, to see how far its result can move on a slightly different version of the data. Basis point: one hundredth of a percentage point, so 10 basis points is 0.1%. Vintage: the version of Ken French's files on the download date, named by the release of the CRSP database they were built from (202607 is the July 2026 release). Provenance: the record of what was downloaded, when, with its checksum and vintage. Factor: a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones. Upper bound: the Sharpe ratio a mean-variance investor would earn with no estimation error, from a rule estimated on the whole sample and judged on the same sample. Simulated history: the 24,000 months of returns the simulation produces. Seed: the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers. Draw: one simulated history, produced from one seed. Standard error: the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M. P-value: the probability of a difference at least as large as the one observed if the two rules were equally good; below 0.05 the difference is unlikely to be chance. Jobson-Korkie: the standard test of whether two Sharpe ratios measured on the same months differ; its result is reported as a p-value. Delta method: a standard way to obtain a standard error for a quantity built from means and variances, used for the CEQ. Near-singular: said of a covariance matrix in which one asset's return is almost a combination of the others', so that the matrix carries almost no information about the difference between them; inverting it then divides by a number close to zero.

**What this notebook does.** It builds the four DGU datasets from French's files, runs the 1/N rule and the sample-based mean-variance rule through DGU's rolling 120-month window, and puts the out-of-sample Sharpe ratio, certainty-equivalent return and turnover beside Tables 3, 4 and 5 of the paper, with the verdict of the band I wrote down before the run.

**Why it comes second.** These two rules are the paper's two extremes. 1/N estimates nothing. Sample-based mean-variance estimates everything, a mean and a covariance for every asset, and plugs the estimates into Markowitz's formula as if they were true. Every other rule in the paper is an attempt to move the second toward the first, so this pair has to be right before any of them is worth running.

**The method.** At the end of each month t, from t = 120 onward, the rule sees the previous 120 months of excess returns, forms its weights, and holds them through month t + 1. Over 497 months that is 377 out-of-sample returns per rule and dataset (DGU section 2). The Sharpe ratio is the mean of those 377 returns over their standard deviation, equation (12); the CEQ return is the mean less half the variance, equation (14) with gamma = 1; turnover is the average absolute trade needed each month to move from the weights the last month's returns drifted the portfolio to and the new target, equation (15). The mean-variance weights are Sigma^-1 mu, equation (3), scaled so that they sum to one in absolute value, equation (1). The 1/N weights are 1/N.

**What I expect to see, and where it comes from.** From Table 3, monthly Sharpe ratios for 1/N of 0.1353, 0.2240, 0.1623 and 0.1753 on Industry, MKT/SMB/HML, FF-1-factor and FF-4-factor; for mean-variance out of sample 0.0679, 0.2186, 0.0128 and 0.1841; for mean-variance in sample, the upper bound estimation error costs, 0.2124, 0.2851, 0.5098 and 0.5364. From Table 5, 1/N turns over 2.2%, 2.4%, 1.6% and 2.0% of the portfolio a month, and mean-variance 606,594, 2.83, 10,466 and 3,553 times that. The band written down before the run: an out-of-sample Sharpe ratio within 0.03 of the published one passes, and turnover within 25% where the published relative turnover is below 100; above that the number is reported and not gated. The value-weighted market, "vw", is run too, as the data check from notebook 01.

**One amendment, made after the first run and dated.** On 13 September 2026, on the evidence of the fragility test at the end of this notebook, the Sharpe band was restricted to the same rows as the turnover band: rules whose published relative turnover is below 100. The unconstrained mean-variance rule on the Industry, FF-1-factor and FF-4-factor datasets is above that level and is reported with the range that noise produces, with no verdict; the in-sample row carries no verdict either, because the band was written for out-of-sample ratios. The level is the paper's own number; it was not chosen from these results. The amendment is recorded in `src/bp/constants.py` under `BAND_SHARPE_APPLIES_BELOW_RELATIVE`.
"""),
    md("""
## Modules

The first four cells are the infrastructure from notebook 01 (the constants, the loader, DGU's published tables, and the dataset builder), unchanged. The three after them are the substance of this notebook: the rules, the rolling evaluation, and the comparison against the paper.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("dgu_published.py"),
    writefile("datasets.py"),
    md("""
### The rules

`ew` is 1/N. `mv` is Sigma^-1 mu on the window's sample moments, normalised. `min` and `vw` are here because they are one line each; `min` is used in notebook 03 and `vw` is the market check. The risk aversion gamma does not appear because it cancels in the normalisation for every unconstrained rule.
"""),
    writefile("rules.py"),
    md("""
### The rolling evaluation

`rolling` walks the window forward one month at a time and records, for each out-of-sample month, the return earned, the target weights, the weights the month's returns drifted the previous portfolio to, and the trade between the two. The measures follow DGU's equations; the two p-values are the Jobson-Korkie test for Sharpe ratios and the delta-method test for CEQ returns (a standard way to obtain a standard error for a quantity built from means and variances), both against 1/N.
"""),
    writefile("backtest.py"),
    md("""
### The comparison

Replicated beside published, one row per rule and dataset, with the verdict of the pre-committed band where one applies.
"""),
    writefile("compare.py"),
    md("""
## Build the datasets

Each is monthly excess returns over French's one-month Treasury bill, 1963-07 to 2004-11, with the factor portfolios as the last columns. The 20 size-and-value portfolios are the 25 less the five with the largest firms, DGU footnote 24.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import numpy as np
import pandas as pd
from bp import constants as C
from bp import datasets as D
from bp import rules as S
from bp import backtest as B
from bp import compare as CMP
from bp import dgu_published as P

pd.set_option("display.width", 160)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

data = D.build_all()
for name, R in data.items():
    assert R.shape == (C.DGU_EXPECTED_T, C.DGU_DATASETS[name]["N"]), (name, R.shape)
    print(f"{name:12s} {R.shape[0]} months x {R.shape[1]} assets, {R.index[0]} to {R.index[-1]}, columns end with {list(R.columns[-2:])}")
"""),
    md("""
## Run the two rules, and the market

377 out-of-sample months per rule and dataset. The in-sample mean-variance Sharpe ratio, estimated once on all 497 months, is computed beside them: it is the upper bound, the Sharpe ratio a mean-variance investor would earn with no estimation error.
"""),
    code("""
results, in_sample, runs = {}, {}, {}
for name, R in data.items():
    mkt = list(R.columns).index("Mkt-RF")
    rules = {"ew": S.ew, "mv": S.mv, "vw": S.vw(mkt)}
    bts = {k: B.rolling(R, f, name=k) for k, f in rules.items()}
    assert all(len(bt.oos) == C.DGU_EXPECTED_OOS for bt in bts.values())
    runs[name] = bts
    results[name] = B.evaluate(bts)
    in_sample[name] = S.in_sample_sharpe(R.to_numpy())
    print(f"{name:12s} done: {len(bts['ew'].oos)} out-of-sample months, {bts['ew'].oos.index[0]} to {bts['ew'].oos.index[-1]}")
"""),
    md("""
## Table 3: Sharpe ratios
"""),
    code("""
sharpe_cmp = CMP.sharpe_table(results, in_sample)
sharpe_cmp
"""),
    md("""
## Table 4: certainty-equivalent returns

No band applies to the CEQ; the rows are reported beside the published ones. For the mean-variance rule the CEQ is dominated by the variance term, and the variance is dominated by the months with extreme weights (the next table shows the five largest), so its value is a statement about those months.
"""),
    code("""
CMP.ceq_table(results)
"""),
    md("""
## Table 5: turnover and return-loss

1/N's turnover is its absolute monthly figure; the other rows are relative to 1/N. Return-loss is the extra monthly return a rule would need for its Sharpe ratio net of a 50 basis point cost to equal 1/N's, equation (17).
"""),
    code("""
CMP.turnover_table(results)
"""),
    code("""
CMP.return_loss_table(results)
"""),
    md("""
## Where the mean-variance rule goes wrong, month by month

The five out-of-sample months with the largest absolute mean-variance return on the Industry dataset, with the sum of absolute weights the rule held going into each. A sum of absolute weights of 50 means the rule was 2,500% long and 2,400% short in some combination of eleven industry portfolios, on the strength of ten years of monthly data.
"""),
    code("""
mv_ind = runs["Industry"]["mv"]
worst = mv_ind.oos.abs().sort_values(ascending=False).head(5).index
pd.DataFrame({
    "mv return": mv_ind.oos.loc[worst],
    "sum |weights|": mv_ind.weights.loc[worst].abs().sum(axis=1),
    "1/N return": runs["Industry"]["ew"].oos.loc[worst],
})
"""),
    md("""
## The fragility of the mean-variance row

This test separates a miss caused by the code from a miss caused by the data. Add Gaussian noise to every return, at one basis point and at ten (a tenth of a percent, small against monthly standard deviations of four to six percent and below the size of many revisions French makes to a published month), and rerun the rule fifty times at each level with a fixed seed. If the published number sits inside the range the noise produces, no code can replicate the row to a tighter band on any vintage. The known-answer test in `tests/test_rules_backtest.py`, which recovers the tangency weights from simulated data, shows that the code is right. This cell measures how far the data can move the number. About two minutes.
"""),
    code("""
rng = np.random.default_rng(C.SIM_SEED)
rows = []
for name, R in data.items():
    j = CMP.DATASETS.index(name)
    row = {"dataset": name, "mv OOS": results[name].loc["mv", "sharpe"], "OOS published": P.SHARPE["mv"][0][j],
           "in-sample": in_sample[name], "in-sample published": P.SHARPE["mv (in sample)"][0][j]}
    for bp in (1, 10):
        oos, ins = [], []
        for _ in range(50):
            Rp = R + rng.normal(0.0, bp * 1e-4, size=R.shape)
            oos.append(B.sharpe(B.rolling(Rp, S.mv).oos))
            ins.append(S.in_sample_sharpe(Rp.to_numpy()))
        row[f"OOS min {bp}bp"], row[f"OOS max {bp}bp"] = min(oos), max(oos)
        row[f"IS min {bp}bp"], row[f"IS max {bp}bp"] = min(ins), max(ins)
    rows.append(row)
fragility = pd.DataFrame(rows).set_index("dataset")
fragility[["mv OOS", "OOS published", "OOS min 1bp", "OOS max 1bp", "OOS min 10bp", "OOS max 10bp"]]
"""),
    code("""
fragility[["in-sample", "in-sample published", "IS min 1bp", "IS max 1bp", "IS min 10bp", "IS max 10bp"]]
"""),
    md("""
## What this notebook established, and what could be wrong

On the vintage of 10 September 2026 the 1/N rows replicate to the third decimal on three datasets (0.1353 against 0.1353 on Industry) and to 0.011 on MKT/SMB/HML, whose three assets are the factors themselves and have been revised more than the portfolios. The market row is within 0.0025 everywhere. 1/N's turnover is within 2.5% of the paper on every dataset, which fixes the turnover convention: trades are measured against the weights the portfolio has drifted to after the month's returns (an asset that rose became a larger share of the portfolio, and the trade back to 1/N is the turnover), and the first purchase is not counted.

The unconstrained mean-variance rule does not replicate within the 0.03 band on Industry or FF-1-factor, and the fragility table says why it cannot: ten basis points of noise move its out-of-sample Sharpe ratio across a range of 0.14 on Industry, 0.12 on FF-1-factor and 0.25 on FF-4-factor, and the published figure lies inside that range on all three. One basis point is already enough on the two size-and-value datasets. In each of the three datasets the market return is nearly a weighted average of the other assets, so the rule sees two assets that move almost identically. The covariance matrix then has almost no information about the difference between them, and inverting it divides by a number close to zero: a tiny change in the inputs becomes a huge change in the weights, and the rule can hold an enormous long position in one and an enormous short position in the other at almost no measured risk. The January 1975 position of 4,500 times wealth is an example. On MKT/SMB/HML, three assets with no such near-duplicate among them, the same rule moves by 0.001 under the noise and passes. The band as first written did not anticipate a row that no vintage can reproduce. The amendment at the top of this notebook follows from this table.

The in-sample mean-variance Sharpe ratios on the two size-and-value datasets are 0.04 to 0.06 below the paper's, and those two numbers move by less than 0.01 under ten basis points of noise, so the difference is in the data. Two causes are possible. The first is revisions to French's 25 portfolios since the paper's 2004 download. The second is the risk-free rate, the Treasury bill return that is subtracted from each portfolio's return to make it an excess return: DGU describe a 90-day bill in one place and a one-month bill in another, and French's site carries only the one-month series, which this notebook uses. Shifting the excess returns of the long-only assets by 3 basis points (0.03 percentage points) a month moves the FF-1-factor in-sample figure by 0.004, far less than the gap of 0.04 to 0.06, so a difference between the two bill rates of that size does not explain the gap. The cause stays unresolved in this notebook.
"""),
]


# ---------------------------------------------------------------------------
# 03: the rules that try to fix mean-variance
# ---------------------------------------------------------------------------

NB03 = [
    md("""
# 03. Shrink the means, ignore the means, or impose the short-sale constraint: the rest of the paper's rules

**Terms used in this notebook.** Risk-free rate: the return on a one-month US Treasury bill, the closest thing to a return with no risk. Excess return: a return minus the risk-free rate over the same month. Sharpe ratio: the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken. Certainty-equivalent return (CEQ): the average return minus half the variance (times a risk aversion of one); the sure monthly return an investor would accept in place of the risky one. Turnover: the fraction of the portfolio bought and sold at a rebalance, summed over the assets; a turnover of 0.02 means that 2% of the portfolio changes hands in the month. Estimation window: the M months of past returns a rule sees when it forms its weights, 120 here. Rolling evaluation: moving the window forward one month at a time, forming the weights, and recording the return of the month after the window. Out-of-sample: measured on months the rule had not seen when it formed its weights. In-sample: measured on the same months that were used to form the weights. Estimation error: the difference between a mean or covariance estimated from a window and its true value. Band: the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover. Gated: said of a cell the band applies to. Verdict: pass or MISS for a gated cell. Fragility test: adding small random noise to every return and rerunning a rule fifty times, to see how far its result can move on a slightly different version of the data. Basis point: one hundredth of a percentage point, so 10 basis points is 0.1%. Factor: a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones. Bayes-Stein: the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage. Minimum variance: the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns. Short-sale constraint: no weight may be negative. Budget constraint: the weights must sum to one. Corner solution: a portfolio with all wealth in a single asset. Lagrangian: the expression an optimisation problem is written as when it has constraints. Non-negative least squares: a standard algorithm for least-squares problems whose unknowns may not be negative. Simulated history: the 24,000 months of returns the simulation produces. Seed: the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers. Draw: one simulated history, produced from one seed.

**What this notebook does.** It adds the rules DGU built to tame the estimation error that notebook 02 exposed, runs all nine rules through the same rolling test, and completes the comparison with Tables 3, 4 and 5 of the paper, including the pre-committed check that the top three rules on each dataset come out in the paper's order.

**Why it comes third.** Notebook 02 showed the two extremes: 1/N, which estimates nothing, and mean-variance, which trusts every estimate and loses most of its Sharpe ratio to estimation error. The literature's answer is to trust the estimates less. There are three ways to do that, each a rule in the paper.

- **Shrink the means toward a common value.** Bayes-Stein (`bs`, section 1.3.2, Jorion 1986) replaces each asset's estimated mean by a weighted average of that estimate and one number common to all assets, the mean return of the minimum-variance portfolio. The weight on the common number, phi, rises when the estimated means are close together relative to their estimation error. The covariance is inflated a little for the uncertainty in the mean.
- **Ignore the means altogether.** Minimum variance (`min`, section 1.4.1) uses only the covariance matrix and finds the lowest-risk fully invested portfolio. The means carry the largest estimation error, so dropping them removes most of the damage, at the cost of any information they held.
- **Impose the short-sale constraint.** The short-sale-constrained rules (`mv-c`, `bs-c`, `min-c`, section 1.5) add the condition that no weight can be negative. Jagannathan and Ma (2003) showed that this constraint acts as shrinkage: constraining an asset's weight to be non-negative is the same as raising its estimated mean, or shrinking its covariances, until the rule no longer shorts it. `g-min-c` goes one step further and requires every weight to be at least half of 1/N.

**The method** is notebook 02's: a 120-month estimation window, 377 out-of-sample months, Sharpe ratio, CEQ and turnover beside the paper's, with the band as amended on 13 September (0.03 on the Sharpe ratio for rules whose published relative turnover is below 100; the rest reported with no verdict).

**What I expect to see, from Table 3.** Minimum variance 0.1554, 0.2493, 0.2778 and -0.0183 on Industry, MKT/SMB/HML, FF-1-factor and FF-4-factor; Bayes-Stein 0.0719, 0.2536, 0.0138, 0.1791; mv-c 0.0678, 0.1084, 0.1977, 0.2024; bs-c 0.0819, 0.1514, 0.1955, 0.2062; min-c 0.1425, 0.2493, 0.1546, 0.3580; g-min-c 0.1451, 0.2467, 0.1615, 0.3028. From footnote 21, the Bayes-Stein shrinkage factor phi averages between 0.32 (FF-4-factor) and 0.66 (MKT/SMB/HML). And from Table 3 read as a whole: the constrained rules beat the unconstrained ones everywhere, and none of them beats 1/N by a statistically significant margin except on the size-and-value datasets.
"""),
    md("""
## One question the paper leaves open, settled before the run

The paper's Lagrangian for the constrained rules, equation (8) on page 1925 (the expression an optimisation problem is written as when it has constraints), shows only the condition that weights be non-negative. Read literally, the rule would find the best non-negative position at any scale and then rescale it to sum to one, exactly as the unconstrained rules do, and the risk aversion gamma would drop out. But footnote 22 on page 1934 says the constrained rules produce "corner solutions with all wealth invested in a single asset", and that only happens if the budget condition, weights summing to one, sits *inside* the optimisation with gamma = 1: the risk penalty is then small against the differences in estimated means, and the rule puts all wealth in the asset with the highest mean.

Both readings are built below. On the MKT/SMB/HML dataset the literal reading gives a Sharpe ratio of 0.238 and never holds a single asset; the budget-inside reading gives 0.109 against the paper's 0.1084 and holds a single asset in 257 of 377 months. The paper's tables match the budget-inside reading. The choice is recorded in `constants.py` as `DGU_CONSTRAINED_BUDGET_INSIDE`, with this evidence, and the literal version is kept in the code as `mv_c_cone` so the comparison can be rerun.
"""),
    md("""
## Modules

Infrastructure from notebooks 01 and 02, unchanged, then the rules module with the new rules added. The constrained rules are solved exactly by non-negative least squares (a standard algorithm for least-squares problems whose unknowns may not be negative) after a change of variables, so there is no solver setting to tune; `tests/test_rules_backtest.py` checks each against an independent solver.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("dgu_published.py"),
    writefile("datasets.py"),
    writefile("rules.py"),
    writefile("backtest.py"),
    writefile("compare.py"),
    md("""
## Build the datasets and run the nine rules
"""),
    code("""
import sys
sys.path.insert(0, "src")
import numpy as np
import pandas as pd
from bp import constants as C
from bp import datasets as D
from bp import rules as S
from bp import backtest as B
from bp import compare as CMP
from bp import dgu_published as P

pd.set_option("display.width", 160)
pd.set_option("display.max_colwidth", 60)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

ORDER = list(C.DGU_RULES)          # ew, mv, bs, min, vw, mv-c, bs-c, min-c, g-min-c
data = D.build_all()
results, in_sample, runs, phi = {}, {}, {}, {}
for name, R in data.items():
    rules = dict(S.RULES)
    rules["vw"] = S.vw(list(R.columns).index("Mkt-RF"))
    bts = {k: B.rolling(R, rules[k], name=k) for k in ORDER}
    assert all(len(bt.oos) == C.DGU_EXPECTED_OOS for bt in bts.values())
    runs[name] = bts
    results[name] = B.evaluate(bts)
    in_sample[name] = S.in_sample_sharpe(R.to_numpy())
    Rn = R.to_numpy()
    phi[name] = np.mean([S.bayes_stein_moments(Rn[t - C.DGU_ESTIMATION_WINDOW:t])[2] for t in range(C.DGU_ESTIMATION_WINDOW, len(Rn))])
    print(f"{name:12s} nine rules, {len(bts['ew'].oos)} out-of-sample months, mean Bayes-Stein phi {phi[name]:.3f}")
print("DGU footnote 21: phi ranges from a low of 0.32 (FF-4-factor) to a high of 0.66 (MKT/SMB/HML)")
"""),
    md("""
## The specification question, in numbers

The literal reading of equation (8) beside the budget-inside reading, on the dataset where they differ most, and the count of months in which the rule held a single asset.
"""),
    code("""
rows = []
for name, R in data.items():
    j = CMP.DATASETS.index(name)
    for label, rule in [("mv-c, equation (8) literal", S.mv_c_cone), ("mv-c, budget inside", S.mv_c)]:
        bt = B.rolling(R, rule)
        rows.append({"dataset": name, "variant": label, "Sharpe": B.sharpe(bt.oos), "published": P.SHARPE["mv-c"][0][j],
                     "months in a single asset": int((bt.weights.max(axis=1) > 0.999).sum())})
pd.DataFrame(rows).set_index(["dataset", "variant"])
"""),
    md("""
## Table 3: Sharpe ratios, all rules
"""),
    code("""
sharpe_cmp = CMP.sharpe_table(results, in_sample)
sharpe_cmp
"""),
    code("""
gated = sharpe_cmp[sharpe_cmp["verdict"].isin(["pass", "MISS"])]
print(f"gated cells: {len(gated)}, pass: {(gated['verdict'] == 'pass').sum()}, MISS: {(gated['verdict'] == 'MISS').sum()}")
gated[gated["verdict"] == "MISS"]
"""),
    md("""
## The ranking check

Pre-committed: the top three rules by out-of-sample Sharpe ratio on each dataset, among the gated rules, come out in the paper's order. The check is strict, and the numbers beside the verdict show how far apart the exchanged rules are: where the published Sharpe ratios of the top rules differ by less than the 0.03 band, an exchange of places is inside the range the band allows.
"""),
    code("""
top3 = CMP.top3_preserved(results, ORDER)
top3[["replicated_top3", "published_top3", "verdict"]]
"""),
    code("""
detail = []
for name in data:
    j = CMP.DATASETS.index(name)
    for rule in sorted(set(top3.loc[name, "replicated_top3"]) | set(top3.loc[name, "published_top3"])):
        detail.append({"dataset": name, "rule": rule, "replicated": results[name].loc[rule, "sharpe"], "published": P.SHARPE[rule][0][j]})
pd.DataFrame(detail).set_index(["dataset", "rule"])
"""),
    md("""
## Table 4: certainty-equivalent returns
"""),
    code("""
CMP.ceq_table(results)
"""),
    md("""
## Table 5: turnover and return-loss
"""),
    code("""
turn = CMP.turnover_table(results)
print(f"gated turnover cells: {turn['verdict'].isin(['pass', 'MISS']).sum()}, MISS: {(turn['verdict'] == 'MISS').sum()}")
turn
"""),
    code("""
CMP.return_loss_table(results)
"""),
    md("""
## Fragility of the two rules that are reported or missed

The fragility test from notebook 02, ten basis points and fifty draws, for Bayes-Stein on the three datasets where it is reported without a verdict, and for minimum variance on FF-4-factor, the one gated cell that misses. About a minute.
"""),
    code("""
rng = np.random.default_rng(C.SIM_SEED)
rows = []
for rule_name, rule, datasets_ in [("bs", S.bs, ["Industry", "FF-1-factor", "FF-4-factor"]), ("min", S.min_variance, ["FF-1-factor", "FF-4-factor"])]:
    for name in datasets_:
        R = data[name]
        j = CMP.DATASETS.index(name)
        vals = [B.sharpe(B.rolling(R + rng.normal(0.0, 1e-3, size=R.shape), rule).oos) for _ in range(50)]
        rows.append({"rule": rule_name, "dataset": name, "replicated": results[name].loc[rule_name, "sharpe"],
                     "published": P.SHARPE[rule_name][0][j], "min under 10 bp noise": min(vals), "max under 10 bp noise": max(vals),
                     "published inside range": bool(min(vals) <= P.SHARPE[rule_name][0][j] <= max(vals))})
pd.DataFrame(rows).set_index(["rule", "dataset"])
"""),
    md("""
## What this notebook established, and what could be wrong

Twenty-nine of the thirty gated Sharpe cells are within 0.03 of the paper, most within 0.01, and every gated turnover cell is within 25%. The CEQ returns of the constrained rules match to the fourth decimal on most cells. The Bayes-Stein shrinkage factor averages 0.33 on FF-4-factor and 0.68 on MKT/SMB/HML against the paper's 0.32 and 0.66, so the shrinkage is implemented as Jorion specified it. The paper's reading of Table 3 reproduces: the constrained rules beat their unconstrained versions on every dataset, minimum variance with constraints is the best of the optimising rules on three of four, and 1/N is beaten by a statistically significant margin only on the size-and-value datasets, where the assets are the portfolios the factors are built from.

One gated cell misses: minimum variance on FF-4-factor, 0.033 against the paper's -0.018. Ten basis points of noise move it across 0.08 and the published value lies outside that range, so fragility alone does not explain the miss; the data differ, as the in-sample rows on the size-and-value datasets showed in notebook 02. It is reported as a miss.

The ranking check passes on Industry and FF-4-factor and fails strictly on the other two, where the rules that change places have published Sharpe ratios 0.002 to 0.007 apart, below the band. The check as written cannot distinguish an exchange of places at that resolution from a replication error, so the numbers beside it are reported.

The specification question matters beyond these numbers. The equation in a paper and the code behind its tables can differ, and when they do, a footnote about the results is better evidence of what was run than the equation is. Choosing the reading that reproduces the tables is a choice between two readings of the text, made once and recorded with its evidence; it is not tuning.
"""),
]


# ---------------------------------------------------------------------------
# 04: the amount of data mean-variance needs; the analytical result and the simulation
# ---------------------------------------------------------------------------

NB04 = [
    md("""
# 04. The amount of data mean-variance needs: DGU's analytical result and their simulation

**Terms used in this notebook.** Risk-free rate: the return on a one-month US Treasury bill, the closest thing to a return with no risk. Excess return: a return minus the risk-free rate over the same month. Sharpe ratio: the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken. Estimation window: the M months of past returns a rule sees when it forms its weights, 120 here. Rolling evaluation: moving the window forward one month at a time, forming the weights, and recording the return of the month after the window. Out-of-sample: measured on months the rule had not seen when it formed its weights. In-sample: measured on the same months that were used to form the weights. Estimation error: the difference between a mean or covariance estimated from a window and its true value. Tangency portfolio: the mix of risky assets with the highest Sharpe ratio when the true means and covariances are known. Critical window: the window length at which sample-based mean-variance starts to beat 1/N on average. Factor: a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones. Beta: how much an asset moves with the factor. Alpha: the part of an asset's expected return that its beta on the factor does not explain, zero in this simulation. Idiosyncratic: an asset's own noise, unrelated to the factor. Simulated history: the 24,000 months of returns the simulation produces. Seed: the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers. Draw: one simulated history, produced from one seed. Turnover: the fraction of the portfolio bought and sold at a rebalance, summed over the assets. Band: the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover. Gated: said of a cell the band applies to. Verdict: pass or MISS for a gated cell. Standard error: the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M. P-value: the probability of a difference at least as large as the one observed if the two rules were equally good; below 0.05 the difference is unlikely to be chance. Bayes-Stein: the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage. Minimum variance: the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns. Short-sale constraint: no weight may be negative. Budget constraint: the weights must sum to one. Corner solution: a portfolio with all wealth in a single asset. Lagrangian: the expression an optimisation problem is written as when it has constraints. Non-negative least squares: a standard algorithm for least-squares problems whose unknowns may not be negative.

**What this notebook does.** The paper does two things after its empirical tables, both with known answers. The first is Proposition 1: a formula for the number of months of data the sample-based mean-variance rule needs before it beats 1/N on average, as a function of the number of assets and of how much better the tangency portfolio is than 1/N. The paper states thirteen values of that formula in its text, and this notebook checks each of them. The second is Table 6: one simulated history of 24,000 months from a one-factor model, with the rules of notebooks 02 and 03 run through windows of 120, 360 and 6,000 months on universes of 10, 25 and 50 assets. In the simulation the true means and covariances are known, so the effect of the window length and of the number of assets can be measured against the true answer.

**Why it comes fourth.** Notebooks 02 and 03 showed on real data that estimation error erases the gain from optimising. Real data cannot say how long a window would repair that, because no longer window exists. The formula and the simulation can, because the window in a simulation can be as long as one likes.

**The formula.** An investor who knew the true means and covariances would hold the tangency portfolio, whose Sharpe ratio is S*. Holding 1/N instead costs a fixed amount that depends on the gap between S* and the Sharpe ratio of 1/N, S_ew. Estimating the moments from M months and plugging them in costs an amount that grows with the number of assets N and shrinks with M. The critical window is the M at which the second cost drops below the first. The three cases of the proposition separate the cost of estimating the means (case 1), the covariances (case 2), and both (case 3). In the paper's calibration the means account for most of the cost.

**What I expect to see.** For the six panels of the paper's Figure 1 the text states values: panel B gives 270, 530 and 1,060 months for 25, 50 and 100 assets; panel E, the one calibrated to US stocks (S* = 0.15, S_ew = 0.12), gives more than 3,000 months for 25 assets and more than 6,000 for 50, the two numbers the abstract quotes. All thirteen stated values are checked. For Table 6, the paper's Sharpe ratios per rule, N and M are in `dgu_published.py`; the band written down before the run is 0.03 per cell (`BAND_SIM_SHARPE_ABS`), and in addition the sign of mean-variance minus 1/N must match the paper in every cell. A single simulated history is one draw, so a second check reruns every rule on eight alternative draws and asks whether the paper's value lies inside the range they produce. Running time: the nine rolling evaluations take about two minutes and the eight-draw check about twenty-five more; on Google Colab expect roughly double.
"""),
    md("""
## Modules

Infrastructure from the earlier notebooks, then two new modules: `critical_window`, the proposition's formulas, and `simulate`, the one-factor market. `rules` and `backtest` gain moment-based versions of the rules and a rolling evaluation that keeps running sums, so that 24,000-month simulated histories run in seconds; the tests check that they return exactly what the window-based versions return.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("dgu_published.py"),
    writefile("rules.py"),
    writefile("backtest.py"),
    writefile("critical_window.py"),
    writefile("simulate.py"),
    md("""
## Proposition 1: the thirteen values the paper states

Each row is one value the text gives for Figure 1, beside the value the formula produces. "about" and "more than" are the paper's own qualifiers; where it prints an exact figure (panel B) the check is within 10 months, because the figure was read off a plot.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import time
import numpy as np
import pandas as pd
from bp import constants as C
from bp import critical_window as CW
from bp import simulate as SIM
from bp import rules as S
from bp import backtest as B
from bp import dgu_published as P

pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 200)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

fig1 = CW.figure_1_table()
print(f"{(fig1['verdict'] == 'pass').sum()} of {len(fig1)} stated values reproduced")
fig1
"""),
    md("""
## The three cases on the US calibration

Panel E, S* = 0.15 and S_ew = 0.12, the calibration the abstract's numbers come from. Case 1 estimates only the means, case 2 only the covariances, case 3 both.
"""),
    code("""
rows = []
for N in (10, 25, 50, 100):
    rows.append({"N": N, **{f"case {c}": CW.critical_window(N, C.ANALYTIC_SHARPE_TANGENCY, C.ANALYTIC_SHARPE_1N, case=c) for c in (1, 2, 3)}})
cases = pd.DataFrame(rows).set_index("N")
for N, floor in C.EXPECT_CRITICAL_M_LOWER.items():
    assert cases.loc[N, "case 3"] > floor, (N, cases.loc[N, "case 3"], floor)
print("months of data needed before sample-based mean-variance beats 1/N on average")
cases
"""),
    md("""
## The simulated market

One factor with an annual excess mean of 8% and standard deviation of 16%; N - 1 assets with betas evenly spread from 0.5 to 1.5, no alpha, and idiosyncratic volatility drawn once per asset between 10% and 30% a year. The factor's own returns are shared across the three universes; Table 6's identical "mv (true)" column across N implies that the paper did the same. With no alpha the true tangency portfolio is the factor, so its Sharpe ratio is 0.08 / 0.16 a year, 0.144 a month; the realised value in one 24,000-month simulated history lands within a standard error, about 0.0065, of that.
"""),
    code("""
markets = {N: SIM.build_market(N) for N in C.SIM_N}
for N, mkt in markets.items():
    w = mkt.true_tangency_weights
    r_true = mkt.returns @ w
    print(f"N={N:2d}: {mkt.returns.shape[0]:,} months; population tangency Sharpe {mkt.mu @ w / np.sqrt(w @ mkt.Sigma @ w):.4f}; "
          f"realised in this history {r_true.mean() / r_true.std(ddof=1):.4f}; mean idiosyncratic vol {np.sqrt(mkt.idio_var[1:] * 12).mean():.3f}")
"""),
    md("""
## Table 6: the rules through 120, 360 and 6,000-month windows

Nine rolling evaluations. 1/N and the true tangency portfolio are full-sample Sharpe ratios, as the paper's constant values across M imply; the estimated rules are out of sample from month M + 1. Progress is printed per cell.
"""),
    code("""
sim_results = {}
t_all = time.time()
for N, mkt in markets.items():
    w_true = mkt.true_tangency_weights
    r_true, r_ew = mkt.returns @ w_true, mkt.returns.mean(axis=1)
    for M in C.SIM_M:
        t0 = time.time()
        bts = B.rolling_moments(mkt.returns, S.MOMENT_RULES, window=M)
        row = {"mv (true)": B.sharpe(pd.Series(r_true)), "ew": B.sharpe(pd.Series(r_ew))}
        row.update({k: B.sharpe(bt.oos) for k, bt in bts.items() if k != "ew"})
        sim_results[(N, M)] = row
        print(f"N={N:2d} M={M:5d}: {len(bts['mv'].oos):,} out-of-sample months, {time.time() - t0:5.1f}s")
print(f"total {time.time() - t_all:.0f}s")
ours = pd.DataFrame(sim_results).T
ours.index.names = ["N", "M"]
ours
"""),
    md("""
## Beside the paper, cell by cell
"""),
    code("""
pub = P.table("sim_sharpe").T[ours.columns]
diff = ours - pub
verdict = diff.abs().le(C.BAND_SIM_SHARPE_ABS).replace({True: "pass", False: "MISS"})
print(f"cells within {C.BAND_SIM_SHARPE_ABS}: {(verdict == 'pass').values.sum()} of {verdict.size}; largest absolute difference {diff.abs().values.max():.4f}")
sign_match = (np.sign(ours["mv"] - ours["ew"]) == np.sign(pub["mv"] - pub["ew"]))
print(f"sign of (mean-variance minus 1/N) matches the paper in {int(sign_match.sum())} of {len(sign_match)} cells")
print("published, DGU Table 6")
pub
"""),
    code("""
print("ours minus published, with the verdict of the 0.03 band")
pd.concat({"difference": diff.round(4), "verdict": verdict}, axis=1).swaplevel(axis=1).sort_index(axis=1, level=0, sort_remaining=False)[ours.columns]
"""),
    code("""
misses = verdict[verdict == "MISS"].dropna(how="all").dropna(axis=1, how="all")
misses if not misses.empty else "no cell outside the band"
"""),
    code("""
print("where mean-variance and 1/N rank differently from the paper:")
pd.DataFrame({"ours mv - 1/N": (ours["mv"] - ours["ew"]).round(4), "published mv - 1/N": (pub["mv"] - pub["ew"]).round(4), "sign matches": sign_match})
"""),
    md("""
## One simulated history is one draw

The paper ran one 24,000-month simulated history and so did the cell above, with a different random seed. A difference between the two tables mixes two things: any difference in the code, and the ordinary variation between two draws of the same market, whose idiosyncratic volatilities are themselves drawn at random. To separate them, every rule is rerun on eight alternative draws (seeds 1 to 8) for every N and M, and the paper's value is checked against the range they produce. A published value inside the range is a difference between draws; one outside it needs another explanation. About twenty-five minutes, most of it the four constrained rules, which solve a small optimisation every month.
"""),
    code("""
spread_rules = S.MOMENT_RULES
spread_rows = []
t0 = time.time()
for N in C.SIM_N:
    for M in C.SIM_M:
        vals = {k: [] for k in spread_rules}
        for seed in range(1, C.SIM_SPREAD_DRAWS + 1):
            mkt_s = SIM.build_market(N, seed=seed)
            bts = B.rolling_moments(mkt_s.returns, spread_rules, window=M)
            for k in spread_rules:
                vals[k].append(B.sharpe(pd.Series(mkt_s.returns.mean(axis=1))) if k == "ew" else B.sharpe(bts[k].oos))
        wins = int(sum(m > e for m, e in zip(vals["mv"], vals["ew"])))
        for k in spread_rules:
            lo, hi = min(vals[k]), max(vals[k])
            spread_rows.append({"N": N, "M": M, "rule": k, "ours": ours.loc[(N, M), k], "published": pub.loc[(N, M), k],
                                "min over draws": lo, "max over draws": hi, "published inside": bool(lo <= pub.loc[(N, M), k] <= hi),
                                "draws where mv beats 1/N": wins})
print(f"{time.time() - t0:.0f}s")
spread = pd.DataFrame(spread_rows).set_index(["rule", "N", "M"]).sort_index()
print(f"published value inside the eight-draw range in {int(spread['published inside'].sum())} of {len(spread)} cells")
spread
"""),
    code("""
print("cells where the published value lies outside the eight-draw range")
spread[~spread["published inside"]]
"""),
    code("""
print("draws (of eight) in which sample-based mean-variance beat 1/N, by N and window; the paper's single draw has it winning only at N = 10, M = 6000")
spread.xs("mv", level="rule")["draws where mv beats 1/N"].unstack("M")
"""),
    md("""
## What this notebook established, and what could be wrong

The formula reproduces all thirteen values the paper states for Figure 1, including the two the abstract quotes: on the calibration to US stocks, sample-based mean-variance needs more than 3,000 months of data to beat 1/N on average with 25 assets and more than 6,000 with 50. Case 2, where only the covariances are estimated, needs 152 months for 25 assets and 294 for 50 on the same calibration. Most of the cost of estimation is in the means.

The simulated market repeats the result from the real data, with the true answer known. With 120 or 360 months of data, sample-based mean-variance earns a Sharpe ratio near zero on every universe while 1/N earns 0.13 to 0.14; only with 6,000 months does it come close, and it draws level with 1/N at 10 assets and stays below at 25 and 50, so the critical window grows with N, as the paper finds. 77 of the 81 cells sit within 0.03 of Table 6, and the sign of mean-variance minus 1/N matches the paper in eight cells of nine; the ninth is the 10-asset, 6,000-month cell, where the paper has mean-variance ahead by 0.006 and this draw has it behind by 0.0004. A Sharpe ratio measured on 24,000 months has a sampling error of about 0.0065, so the gap between the two draws is smaller than the uncertainty of either number. Across eight alternative draws, mean-variance beats 1/N in that cell in seven of the eight, and in no other cell in any draw. The paper's single draw has the same pattern.

The four cells outside the band all belong to the minimum-variance rule and its constrained version, three of them on the 10-asset universe. Minimum variance puts most of its weight on the assets with the least noise of their own. Which assets those are, and how little noise they have, depends on the draw of the idiosyncratic volatilities, and with only nine such assets the draw changes the result by more than for any other rule. The eight-draw ranges for minimum variance are the widest in the table; this draw's own values sit at the low end of them, and the paper's sit at the high end. Across all 72 cells of rule, N and M, the paper's value lies inside the eight-draw range in 65; the seven outside it miss the edge of the range by 0.0001 to 0.004, less than one standard error of a Sharpe ratio on these samples, and three of them are the minimum-variance cells just named. Nothing in the comparison points to a difference in the code.

One thing this notebook does not settle. The formula and the simulation both assume two things about returns: that each month's return follows a normal distribution (the bell curve, under which a month more than five standard deviations from its mean happens about once in two million months), and that each month is independent of the one before (a turbulent month says nothing about the next). The paper chooses these assumptions on purpose. Most portfolio rules, mean-variance among them, are derived under them, so a market that satisfies them should favour mean-variance; if the rule cannot beat 1/N in that market, the paper argues, it should not do so in real markets, where the tails are fatter and volatility comes in waves. The paper argues this direction and does not test it. Its section of robustness checks changes the design of the empirical test (a 60-month window in place of 120, a window that grows over time in place of one that rolls, a holding period of a year in place of a month, other levels of risk aversion) and keeps both assumptions, and a footnote notes that the paper's own p-values assume them and that real data violate them. Notebooks 05 and 06 test the two assumptions one at a time, by rerunning this simulation first with fat-tailed shocks and then with volatility that clusters, with nothing else changed.
"""),
]


# ---------------------------------------------------------------------------
# 05: beyond the paper, the same market with fat tails
# ---------------------------------------------------------------------------

NB05 = [
    md("""
# 05. Beyond the paper: the same simulated market with fat tails

**Terms used in this notebook.** Risk-free rate: the return on a one-month US Treasury bill. Excess return: a return minus the risk-free rate over the same month. Sharpe ratio: the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken. Estimation window: the M months of past returns a rule sees when it forms its weights, 120 here. Rolling evaluation: moving the window forward one month at a time, forming the weights, and recording the return of the month after the window. Out-of-sample: measured on months the rule had not seen when it formed its weights. In-sample: measured on the same months that were used to form the weights. Estimation error: the difference between a mean or covariance estimated from a window and its true value. Tangency portfolio: the mix of risky assets with the highest Sharpe ratio when the true means and covariances are known. Critical window: the window length at which sample-based mean-variance starts to beat 1/N on average. Factor: a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones. Beta: how much an asset moves with the factor. Alpha: the part of an asset's expected return that its beta on the factor does not explain, zero in this simulation. Idiosyncratic: an asset's own noise, unrelated to the factor. Simulated history: the 24,000 months of returns the simulation produces. Seed: the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers. Draw: one simulated history, produced from one seed. Standard error: the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M. Fat tails: extreme months more frequent and more extreme than a normal distribution allows. Kurtosis: a measure of how heavy the tails of a distribution are; excess kurtosis is zero for the normal distribution. Student-t: a fat-tailed relative of the normal distribution. Degrees of freedom: the Student-t's tail parameter, fewer meaning fatter tails. Scale mixture: a fat-tailed variable built by multiplying a normal one by a random scale. Crossing: in the simulation, the first window tested at which mean-variance's out-of-sample Sharpe ratio reaches 1/N's. Slack: the allowance of 0.01 within which a comparison still counts as in the expected direction. Bayes-Stein: the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage. Minimum variance: the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns.

**What this notebook does.** The formula and the simulation of notebook 04 assume that returns are normally distributed and independent from month to month. The paper chose that setting because most portfolio rules are derived in it and it should favour mean-variance. This notebook reruns the Table 6 simulation with fat-tailed shocks and nothing else changed, and measures what the normality assumption is worth. The paper has no table for this, so the pre-committed statements are three expectations, written in `constants.py` before the run and each reported as a count of cells.

**Fat tails.** A normal distribution says a month more than three standard deviations below the mean happens about once in 370 months, once in a working life. On French's US market series from 1926 to 2026 (1,202 months), months more than three standard deviations below the mean occurred 11 times, against 1.6 expected under a normal distribution, about seven times more often. Fat tails means that extreme months are more frequent and more extreme than a normal distribution allows. Fat tails matter for estimation because the extreme months pull the sample mean and the sample covariance around: one crash month inside a 120-month window changes every covariance in the window and stays in it for ten years. For the same window, estimation error is larger under fat tails, and a rule that trusts its estimates should lose more.

**How the fat tails are built.** The Student-t distribution is the standard fat-tailed relative of the normal: the same bell shape in the middle, more weight in the tails, and one parameter, the degrees of freedom, that sets how much; the smaller it is, the fatter the tails. Two levels are run: 10 degrees of freedom, whose excess kurtosis of 1 is about that of a broad index's monthly returns, and 5, whose excess kurtosis of 6 is about that of an industry portfolio's. The construction is a scale mixture: each month's normal shocks, the same draws as notebook 04 from the same seed, are multiplied by one random scale factor for that month, drawn so that the variance is unchanged. Because one scale applies to every asset in the month, an extreme month hits all of them together, as crashes do. The means and covariances of the fat-tailed market are exactly those of notebook 04's, so the tangency portfolio, S*, S_ew and the formula's critical window are the same numbers, and only the rules' estimates of them change.

**What I expect to see, written before the run.** First, a construction check: 1/N and the tangency portfolio, which estimate nothing, keep their full-sample Sharpe ratios to within two standard errors (0.013). Second, the direction: in every cell of the Table 6 grid, every estimated rule's Sharpe ratio is no higher under fat tails than under normal shocks, allowing a slack of 0.01 for noise, and the loss grows as the tails fatten and as the window shortens. Third, the crossing: for 10 assets, the window at which mean-variance draws level with 1/N comes later under fat tails; for 25 and 50 assets, 1/N is so close to the tangency portfolio in this market that no crossing is expected within 12,000 months under any distribution, and the formula says so. Running time: three runs of the Table 6 grid, about six minutes, and the crossing table, about five.
"""),
    md("""
## Modules

The modules of notebook 04; `simulate` gains the fat-tailed option and a kurtosis function.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("dgu_published.py"),
    writefile("rules.py"),
    writefile("backtest.py"),
    writefile("critical_window.py"),
    writefile("simulate.py"),
    md("""
## What fat tails look like

The factor's monthly return under the three distributions, from the same seed. Excess kurtosis is zero for a normal distribution, 1 for a t with 10 degrees of freedom and 6 for one with 5. The share of months beyond three standard deviations is 0.27% under a normal distribution. The last two columns check that the scaling left the mean and the variance where they were.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import time
import numpy as np
import pandas as pd
from bp import constants as C
from bp import critical_window as CW
from bp import simulate as SIM
from bp import rules as S
from bp import backtest as B
from bp import dgu_published as P

pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 200)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

DISTS = [("normal", None)] + [(f"t, {d} d.o.f.", d) for d in C.SIM_T_DOF]
markets = {(N, label): SIM.build_market(N, dof=dof) for N in C.SIM_N for label, dof in DISTS}

rows = []
for label, dof in DISTS:
    f = markets[(10, label)].returns[:, 0]
    z = (f - f.mean()) / f.std(ddof=1)
    rows.append({"shocks": label, "excess kurtosis": SIM.excess_kurtosis(f), "months beyond 3 sd (%)": 100 * np.mean(np.abs(z) > 3),
                 "worst month": f.min(), "best month": f.max(),
                 "mean (true 0.0067)": f.mean(), "sd (true 0.0462)": f.std(ddof=1)})
pd.DataFrame(rows).set_index("shocks")
"""),
    md("""
## Expectation 1: the rules that estimate nothing

1/N and the tangency portfolio held on the full 24,000 months, under each distribution and for each universe. They use no estimates, so the fat tails can only move them through sampling error, and the check is that they stay within two standard errors of their normal-shock values.
"""),
    code("""
rows = []
for N in C.SIM_N:
    ref = {}
    for label, dof in DISTS:
        mkt = markets[(N, label)]
        w = mkt.true_tangency_weights
        sr = {"ew": B.sharpe(pd.Series(mkt.returns.mean(axis=1))), "mv (true)": B.sharpe(pd.Series(mkt.returns @ w))}
        if dof is None:
            ref = sr
        for k, v in sr.items():
            rows.append({"N": N, "rule": k, "shocks": label, "Sharpe": v, "minus normal": v - ref[k],
                         "within check": bool(abs(v - ref[k]) <= C.FAT_TAIL_MOMENT_CHECK_ABS)})
check1 = pd.DataFrame(rows).set_index(["N", "rule", "shocks"])
print(f"expectation 1: {int(check1['within check'].sum())} of {len(check1)} within {C.FAT_TAIL_MOMENT_CHECK_ABS} of the normal-shock value")
check1
"""),
    md("""
## Table 6 under each distribution

The nine cells of notebook 04, run three times: normal shocks (the same table as notebook 04), then 10 and 5 degrees of freedom. About two minutes per run.
"""),
    code("""
grid = {}
t_all = time.time()
for label, dof in DISTS:
    for N in C.SIM_N:
        mkt = markets[(N, label)]
        w_true = mkt.true_tangency_weights
        r_true, r_ew = mkt.returns @ w_true, mkt.returns.mean(axis=1)
        for M in C.SIM_M:
            bts = B.rolling_moments(mkt.returns, S.MOMENT_RULES, window=M)
            row = {"mv (true)": B.sharpe(pd.Series(r_true)), "ew": B.sharpe(pd.Series(r_ew))}
            row.update({k: B.sharpe(bt.oos) for k, bt in bts.items() if k != "ew"})
            grid[(label, N, M)] = row
    print(f"{label:14s} done, {time.time() - t_all:.0f}s so far")
tables = pd.DataFrame(grid).T
tables.index.names = ["shocks", "N", "M"]
for label, _ in DISTS:
    print(label)
    print(tables.loc[label].to_string())
    print()
"""),
    md("""
## Expectation 2: every estimated rule, every cell, fat-tailed minus normal

A negative number is the direction expected. The count is over the seven estimated rules, nine cells and two fat-tailed distributions, 126 comparisons.
"""),
    code("""
estimated = [k for k in tables.columns if k not in ("ew", "mv (true)")]
normal = tables.loc["normal"]
diffs = {}
for label, dof in DISTS[1:]:
    d = (tables.loc[label] - normal)[estimated]
    diffs[label] = d
    in_dir = (d <= C.FAT_TAIL_DIRECTION_SLACK)
    print(f"{label}: {int(in_dir.values.sum())} of {in_dir.size} cells in the expected direction; mean change {d.values.mean():+.4f}; largest fall {d.values.min():+.4f}")
    print(d.round(4).to_string())
    print()
"""),
    code("""
print("mean change in Sharpe ratio by window, averaged over rules and N: the loss should be largest at M = 120 and shrink as the window grows")
pd.DataFrame({label: d.groupby(level="M").mean().mean(axis=1) for label, d in diffs.items()})
"""),
    code("""
print("mean change by rule, averaged over cells: which rules fat tails hurt most")
pd.DataFrame({label: d.mean(axis=0) for label, d in diffs.items()})
"""),
    md("""
## Expectation 3: the crossing

Sample-based mean-variance against 1/N, both measured on the same out-of-sample months, over a grid of windows from 120 to 12,000 months. The gap is mean-variance's Sharpe ratio minus 1/N's; the crossing is the first window at which it is not negative. Beside it, the formula's critical window for this market's own S* and S_ew (notebook 04, case 3), which is the same number under every distribution because the moments are the same. About five minutes.
"""),
    code("""
pair = {k: S.MOMENT_RULES[k] for k in ("ew", "mv")}
gap_rows, cross_rows = [], []
t0 = time.time()
for N in C.SIM_N:
    mkt = markets[(N, "normal")]
    w = mkt.true_tangency_weights
    s_star = float(mkt.mu @ w / np.sqrt(w @ mkt.Sigma @ w))
    w_ew = np.full(N, 1.0 / N)
    s_ew = float(mkt.mu @ w_ew / np.sqrt(w_ew @ mkt.Sigma @ w_ew))
    formula = CW.critical_window(N, s_star, s_ew, case=3, m_max=C.SIM_T)
    for label, dof in DISTS:
        R = markets[(N, label)].returns
        gaps = {}
        for M in C.SIM_CROSSING_WINDOWS:
            bts = B.rolling_moments(R, pair, window=M)
            gaps[M] = B.sharpe(bts["mv"].oos) - B.sharpe(bts["ew"].oos)
            gap_rows.append({"N": N, "shocks": label, "M": M, "gap": gaps[M]})
        crossing = next((M for M in C.SIM_CROSSING_WINDOWS if gaps[M] >= 0), None)
        cross_rows.append({"N": N, "shocks": label, "S*": s_star, "S_ew": s_ew, "formula (months)": formula if formula is not None else f"none up to {C.SIM_T:,}",
                           "first window with mv >= 1/N": crossing if crossing is not None else f"none up to {C.SIM_CROSSING_WINDOWS[-1]:,}"})
    print(f"N={N:2d} done, {time.time() - t0:.0f}s so far")
crossing_table = pd.DataFrame(cross_rows).set_index(["N", "shocks"])
crossing_table
"""),
    code("""
print("the gap, mean-variance minus 1/N, by window: negative means 1/N is ahead")
pd.DataFrame(gap_rows).set_index(["N", "shocks", "M"])["gap"].unstack("M").round(4)
"""),
    md("""
## What this notebook established, and what could be wrong

All three expectations are met, and the effect is small. Expectation 1: 18 of 18, so the fat-tailed markets are the same market with different tails. Expectation 2: 125 of 126 comparisons inside the slack, and the changes are small. With 5 degrees of freedom the estimated rules lose 0.002 in Sharpe ratio on average, 0.004 at the 120-month window and nothing at 6,000, and the largest single fall is 0.015; with 10 degrees of freedom the average change is +0.002, inside sampling error, so no effect is detectable. Expectation 3: for 10 assets the crossing moves from 3,000 months under normal shocks to 4,000 under both fat-tailed markets, against the formula's 4,536. The crossing is known only to the nearest window tested (the windows were 120, 240, 360, 600, 1,000, 2,000, 3,000, 4,000, 6,000, 9,000 and 12,000 months), and the gap between mean-variance and 1/N at 3,000 months under normal shocks is 0.0003, so the move is one step of that list and inside sampling error. For 25 and 50 assets no crossing occurs within 12,000 months under any distribution, as the formula says (17,753 months and none).

The effect is small for two reasons, one about the estimated means and one about the estimated covariances.

The means. Every rule that uses expected returns estimates them as the average return of each asset over the 120 months in the window. An average computed from 120 months is itself uncertain, because a different 120 months would give a different average. The size of that uncertainty is called the standard error, and it equals the standard deviation of the monthly returns divided by the square root of the number of months. For an asset whose monthly returns have a standard deviation of 5%, the standard error of its 120-month average is 5% divided by the square root of 120, about 0.46% a month. This formula contains only the standard deviation and the number of months; the shape of the distribution does not enter it. The fat-tailed market was built with the same standard deviations as the normal market, so every estimated mean in it is exactly as uncertain as under normal shocks: 0.46% a month in the example, under both distributions. Notebook 04 showed that the uncertainty in the means accounts for nearly all of the cost of estimation (3,087 of the 3,239 months of the critical window for 25 assets). The part of the problem that matters most is therefore untouched by the fat tails. In the proposition this is the case-1 term, N divided by M, which holds for any distribution with a finite variance; only the two covariance terms, k and h, were derived under normality.

The covariances. The sample covariance between two assets is the average, over the window, of the product of their two deviations from their means. A month in which both assets move five standard deviations contributes 25 times as much to that average as a month in which both move one standard deviation, so fat tails do make the sample covariance noisier. In this market, however, one scale factor multiplies every asset's shock in a given month. An extreme month therefore multiplies every entry of that month's contribution by the same number. This raises or lowers the whole estimated covariance matrix together and leaves the ratios between its entries almost unchanged, and the rules use only those ratios. The mean-variance weights, for example, are the inverse of the covariance matrix times the vector of means, rescaled so that the weights sum to one: if every entry of the covariance matrix is doubled, the product is halved and the rescaling undoes the halving, so the weights do not change. The minimum-variance weights behave the same way. For the constrained mean-variance rules the level of the covariance enters through the risk penalty, and the table shows that the effect is small there too. Fat tails of this kind therefore change the estimated level of risk and leave the estimated weights almost where they were, and the Sharpe ratio of a rule depends on its weights.

Together: the inputs that carry most of the cost, the means, are exactly as uncertain as under normal shocks, and the inputs that became noisier, the covariances, became noisier in a way the weights hardly respond to. The paper's conclusion therefore does not depend on the normality assumption.

What this notebook does not settle. Four limits remain.

First, the months in this market are still independent of one another: the volatility of one month says nothing about the next. In real markets volatility comes in waves, and turbulent months follow turbulent months. Under that pattern a covariance estimated from the last 120 months is wrong in a known direction for the month ahead, because the window averages over calm and stormy months while the next month belongs to whichever regime the market is in now. Notebook 06 builds a market with that pattern and repeats this notebook's three expectations on it.

Second, in this market the same scale factor multiplies every asset's shock in a given month, so an extreme month moves all assets together. A covariance matrix carries two kinds of information: the overall level of risk (how large the variances are) and the pattern of relative risk (which assets are more volatile than which others, and how strongly each pair moves together). A common scale changes the level and leaves the pattern almost intact, and the previous paragraph showed that the rules' weights depend only on the pattern. A market in which each asset had its own scale factor each month would change the pattern as well: in a month where one asset's scale is large and another's is small, their estimated variances and their estimated correlations with the other assets move apart. Fat tails of that kind would move the estimated weights, and the loss for the rules would be larger than the loss measured here. This notebook does not test that kind.

Third, the fat tails here are symmetric. The scale factor multiplies the shock whatever its sign, so an extreme month is as likely to be an extreme gain as an extreme loss. In real markets extreme losses are more common than extreme gains of the same size. A one-sided version would need a different construction and is not run.

Fourth, every number in this notebook comes from one draw of each market, that is, from one 24,000-month simulated history per distribution, all built from the same seed. A different seed would give slightly different Sharpe ratios for every rule with nothing else changed. Notebook 04 measured how much a Sharpe ratio moves between draws by building its market eight more times: for a rule with a Sharpe ratio near 0.13, the eight values spread over a range of about 0.01 to 0.02. That repetition was not done here, because it would cost eight further runs of the whole grid. A difference of about 0.005 between two cells of the tables above is therefore of the size that a change of seed alone produces, and it should not be read as an effect of the tails. The averages over many cells, and the counts in the three expectations, are the informative numbers.
"""),
]

# ---------------------------------------------------------------------------
# 06: beyond the paper, volatility that changes through time
# ---------------------------------------------------------------------------

NB06 = [
    md("""
# 06. Beyond the paper: volatility that changes through time

**Terms used in this notebook.** Risk-free rate: the return on a one-month US Treasury bill. Excess return: a return minus the risk-free rate over the same month. Sharpe ratio: the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken. Estimation window: the M months of past returns a rule sees when it forms its weights, 120 here. Rolling evaluation: moving the window forward one month at a time, forming the weights, and recording the return of the month after the window. Out-of-sample: measured on months the rule had not seen when it formed its weights. In-sample: measured on the same months that were used to form the weights. Estimation error: the difference between a mean or covariance estimated from a window and its true value. Tangency portfolio: the mix of risky assets with the highest Sharpe ratio when the true means and covariances are known. Critical window: the window length at which sample-based mean-variance starts to beat 1/N on average. Factor: a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones. Beta: how much an asset moves with the factor. Alpha: the part of an asset's expected return that its beta on the factor does not explain, zero in this simulation. Idiosyncratic: an asset's own noise, unrelated to the factor. Simulated history: the 24,000 months of returns the simulation produces. Seed: the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers. Draw: one simulated history, produced from one seed. Standard error: the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M. Fat tails: extreme months more frequent and more extreme than a normal distribution allows. Kurtosis: a measure of how heavy the tails of a distribution are; excess kurtosis is zero for the normal distribution. Student-t: a fat-tailed relative of the normal distribution. Degrees of freedom: the Student-t's tail parameter, fewer meaning fatter tails. Crossing: in the simulation, the first window tested at which mean-variance's out-of-sample Sharpe ratio reaches 1/N's. Slack: the allowance of 0.01 within which a comparison still counts as in the expected direction. Volatility clustering: volatility that persists from month to month, so that a turbulent month is usually followed by another. GARCH(1,1): the standard model of volatility clustering, in which next month's variance is a constant plus a weight times this month's squared shock plus a weight times this month's variance. Persistence: the sum of the two GARCH weights, which sets how slowly a volatility shock fades. Autocorrelation: the correlation of a series with its own value one month earlier. Regime: a stretch of months with a similar level of volatility. Leverage effect: volatility rising more after a fall than after a rise of the same size. Oracle: a rule given the truth it could never know in practice, run to find the ceiling on what knowing it would be worth. Unconditional: the long-run average of a variance or correlation. Conditional: its value in a given month, given what is known then. Bayes-Stein: the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage. Minimum variance: the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns.

**What this notebook does.** The formula and the simulation of notebook 04 assume normally distributed returns and independent months. Notebook 05 relaxed the first assumption and found that it changes little. This notebook relaxes the second. It reruns the Table 6 simulation with volatility that clusters through time, with the unconditional means and covariances held exactly where they were, the same seed, and nothing else changed. The paper has no table for this, so three expectations were written in `constants.py` before the run, and each is reported as a count of cells.

**Volatility clustering.** In real markets volatility comes in waves. A turbulent month is usually followed by another turbulent month, calm stretches last for years, and after a crash the daily swings stay about twice their usual size for a year. Mandelbrot described it in 1963: large changes tend to be followed by large changes, of either sign. The paper's simulated market has no such memory; every month's volatility is the same as every other's. Clustering affects estimation differently from fat tails: fat tails make an estimate noisy, and clustering makes it wrong in a known direction. A 120-month average of a volatility that moves is the average of the regimes inside the window, and the month ahead belongs to the current regime. If the market has just turned turbulent, every covariance in the window understates next month's risk. If the market factor's volatility rises while the assets' own noise does not, the correlations between assets rise with it, as they do in a crisis, so the window's correlations are also too low, and the minimum-variance portfolio built from them is the wrong portfolio for the month ahead.

**How the clustering is built.** The standard model is GARCH(1,1) (Bollerslev 1986). Next month's variance is a constant, plus alpha times this month's squared shock, plus beta times this month's variance. The two weights are called alpha and beta in the GARCH literature, and they have nothing to do with the alpha and beta of the factor model. Alpha, here 0.10, sets how much a surprise raises volatility; beta, here 0.85, sets how slowly the rise fades; their sum, 0.95, is the persistence, and half of a volatility shock is still present thirteen months later. The constant is chosen so that the long-run variance is exactly the normal market's. The factor's shock and each asset's own shock follow separate processes driven by their own past, so the factor can be turbulent while an asset's own noise is quiet, and the correlations move. The normal shocks are the same draws as notebook 04's from the same seed, each multiplied by its month's volatility multiplier, so the two markets are paired shock for shock. Clustering produces an excess kurtosis of about 0.8, between the two levels of notebook 05; the shocks are otherwise normal.

**What I expect to see, written before the run.** First, the construction check: 1/N and the tangency portfolio, which estimate nothing, keep their full-sample Sharpe ratios to within 0.013. Second, the direction: in every cell of the Table 6 grid, every estimated rule's Sharpe ratio is no higher under clustering than in the normal market, with a slack of 0.01; this time the loss is expected to be visible, and largest for the rules whose weights depend on the shape of the covariance, minimum variance and its constrained versions, because the shape now moves. Third, the crossing: for 10 assets, the window at which mean-variance draws level with 1/N comes later than in the normal market; for 25 and 50, none within 12,000 months under either market. Two descriptive checks sit beside them: the autocorrelation of the factor's squared return, which the GARCH formula puts at 0.18 and which is zero in the normal market, and the true correlation between assets in the calmest and the stormiest months. Running time: about eight minutes.
"""),
    md("""
## Modules

The modules of notebook 05; `simulate` gains the GARCH option, the volatility recursion and an autocorrelation function.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("dgu_published.py"),
    writefile("rules.py"),
    writefile("backtest.py"),
    writefile("critical_window.py"),
    writefile("simulate.py"),
    md("""
## What volatility clustering looks like

The factor's monthly return under both markets, from the same seed. The autocorrelation of squared returns is the standard measure of clustering: a large squared return this month predicts a large one next month. The last two columns are the construction check on the mean and the standard deviation.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import time
import numpy as np
import pandas as pd
from bp import constants as C
from bp import critical_window as CW
from bp import simulate as SIM
from bp import rules as S
from bp import backtest as B
from bp import dgu_published as P

pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 200)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

MARKETS = [("normal", False), ("clustered volatility", True)]
markets = {(N, label): SIM.build_market(N, garch=g) for N in C.SIM_N for label, g in MARKETS}
a, b = C.SIM_GARCH_ALPHA, C.SIM_GARCH_BETA
print(f"GARCH(1,1) with alpha {a}, beta {b}: persistence {a + b:.2f}, half-life of a volatility shock {np.log(0.5) / np.log(a + b):.1f} months, "
      f"autocorrelation of squared shocks {a * (1 - a * b - b**2) / (1 - 2 * a * b - b**2):.3f}, excess kurtosis {6 * a**2 / (1 - b**2 - 2 * a * b - 3 * a**2):.2f}")

rows = []
for label, g in MARKETS:
    f = markets[(10, label)].returns[:, 0]
    d = f - f.mean()
    z = d / f.std(ddof=1)
    rows.append({"market": label, "autocorrelation of squared return, lag 1": SIM.autocorrelation(d**2, 1),
                 "lag 12": SIM.autocorrelation(d**2, 12), "excess kurtosis": SIM.excess_kurtosis(f),
                 "months beyond 3 sd (%)": 100 * np.mean(np.abs(z) > 3),
                 "mean (true 0.0067)": f.mean(), "sd (true 0.0462)": f.std(ddof=1)})
pd.DataFrame(rows).set_index("market")
"""),
    md("""
## The target moves

In the clustered market the true covariance of any month is known, because the volatility multipliers are. The table takes the 10-asset universe and compares the calmest tenth of months (lowest factor volatility) with the stormiest tenth: the factor's annualised volatility, the true average correlation between the nine assets, and the true minimum-variance weight on the factor asset. In the normal market all three are constant. A rule that averages 120 months of history estimates the middle row while the market is in the first or the last.
"""),
    code("""
def true_sigma(mkt, t):
    sf2 = (C.SIM_FACTOR_SD_ANNUAL**2 / 12.0) * (mkt.scales[t, 0] ** 2 if mkt.scales is not None else 1.0)
    idio = mkt.idio_var * (mkt.scales[t] ** 2 if mkt.scales is not None else 1.0)
    return sf2 * np.outer(mkt.betas, mkt.betas) + np.diag(idio)

def describe(mkt, months):
    corrs, w_factor, vol = [], [], []
    for t in months:
        Sg = true_sigma(mkt, t)
        sd = np.sqrt(np.diag(Sg))
        R = Sg / np.outer(sd, sd)
        off = R[1:, 1:][~np.eye(mkt.N - 1, dtype=bool)]
        corrs.append(off.mean())
        w = np.linalg.solve(Sg, np.ones(mkt.N)); w = w / w.sum()
        w_factor.append(w[0])
        vol.append(np.sqrt(Sg[0, 0] * 12))
    return {"factor volatility, annualised": np.mean(vol), "true average correlation between assets": np.mean(corrs), "true minimum-variance weight on the factor": np.mean(w_factor)}

g10 = markets[(10, "clustered volatility")]
order = np.argsort(g10.scales[:, 0])
tenth = len(order) // 10
rows = {"normal market, every month": describe(markets[(10, "normal")], [0]),
        "clustered, calmest tenth of months": describe(g10, order[:tenth]),
        "clustered, all months (average)": describe(g10, np.arange(0, len(order), 10)),
        "clustered, stormiest tenth of months": describe(g10, order[-tenth:])}
pd.DataFrame(rows).T
"""),
    md("""
## Expectation 1: the rules that estimate nothing
"""),
    code("""
rows = []
for N in C.SIM_N:
    ref = {}
    for label, g in MARKETS:
        mkt = markets[(N, label)]
        w = mkt.true_tangency_weights
        sr = {"ew": B.sharpe(pd.Series(mkt.returns.mean(axis=1))), "mv (true)": B.sharpe(pd.Series(mkt.returns @ w))}
        if not g:
            ref = sr
        for k, v in sr.items():
            rows.append({"N": N, "rule": k, "market": label, "Sharpe": v, "minus normal": v - ref[k],
                         "within check": bool(abs(v - ref[k]) <= C.FAT_TAIL_MOMENT_CHECK_ABS)})
check1 = pd.DataFrame(rows).set_index(["N", "rule", "market"])
print(f"expectation 1: {int(check1['within check'].sum())} of {len(check1)} within {C.FAT_TAIL_MOMENT_CHECK_ABS} of the normal-market value")
check1
"""),
    md("""
## Table 6 under both markets

About two minutes each.
"""),
    code("""
grid = {}
t_all = time.time()
for label, g in MARKETS:
    for N in C.SIM_N:
        mkt = markets[(N, label)]
        w_true = mkt.true_tangency_weights
        r_true, r_ew = mkt.returns @ w_true, mkt.returns.mean(axis=1)
        for M in C.SIM_M:
            bts = B.rolling_moments(mkt.returns, S.MOMENT_RULES, window=M)
            row = {"mv (true)": B.sharpe(pd.Series(r_true)), "ew": B.sharpe(pd.Series(r_ew))}
            row.update({k: B.sharpe(bt.oos) for k, bt in bts.items() if k != "ew"})
            grid[(label, N, M)] = row
    print(f"{label:22s} done, {time.time() - t_all:.0f}s so far")
tables = pd.DataFrame(grid).T
tables.index.names = ["market", "N", "M"]
for label, _ in MARKETS:
    print(label)
    print(tables.loc[label].to_string())
    print()
"""),
    md("""
## Expectation 2: every estimated rule, every cell, clustered minus normal

A negative number is the direction expected. 63 comparisons: seven estimated rules, nine cells.
"""),
    code("""
estimated = [k for k in tables.columns if k not in ("ew", "mv (true)")]
d = (tables.loc["clustered volatility"] - tables.loc["normal"])[estimated]
in_dir = (d <= C.FAT_TAIL_DIRECTION_SLACK)
print(f"{int(in_dir.values.sum())} of {in_dir.size} cells in the expected direction; mean change {d.values.mean():+.4f}; largest fall {d.values.min():+.4f}; largest rise {d.values.max():+.4f}")
d.round(4)
"""),
    code("""
print("mean change by window, averaged over rules and N")
print(d.groupby(level="M").mean().mean(axis=1).round(4).to_string())
print()
print("mean change by rule, averaged over cells")
print(d.mean(axis=0).round(4).to_string())
"""),
    md("""
## Expectation 3: the crossing

As in notebook 05: mean-variance against 1/N on the same out-of-sample months over a grid of windows, with the formula's critical window for this market's S* and S_ew beside it. About three minutes.
"""),
    code("""
pair = {k: S.MOMENT_RULES[k] for k in ("ew", "mv")}
gap_rows, cross_rows = [], []
t0 = time.time()
for N in C.SIM_N:
    mkt = markets[(N, "normal")]
    w = mkt.true_tangency_weights
    s_star = float(mkt.mu @ w / np.sqrt(w @ mkt.Sigma @ w))
    w_ew = np.full(N, 1.0 / N)
    s_ew = float(mkt.mu @ w_ew / np.sqrt(w_ew @ mkt.Sigma @ w_ew))
    formula = CW.critical_window(N, s_star, s_ew, case=3, m_max=C.SIM_T)
    for label, g in MARKETS:
        R = markets[(N, label)].returns
        gaps = {}
        for M in C.SIM_CROSSING_WINDOWS:
            bts = B.rolling_moments(R, pair, window=M)
            gaps[M] = B.sharpe(bts["mv"].oos) - B.sharpe(bts["ew"].oos)
            gap_rows.append({"N": N, "market": label, "M": M, "gap": gaps[M]})
        crossing = next((M for M in C.SIM_CROSSING_WINDOWS if gaps[M] >= 0), None)
        cross_rows.append({"N": N, "market": label, "S*": s_star, "S_ew": s_ew,
                           "formula (months)": formula if formula is not None else f"none up to {C.SIM_T:,}",
                           "first window with mv >= 1/N": crossing if crossing is not None else f"none up to {C.SIM_CROSSING_WINDOWS[-1]:,}"})
    print(f"N={N:2d} done, {time.time() - t0:.0f}s so far")
pd.DataFrame(cross_rows).set_index(["N", "market"])
"""),
    code("""
print("the gap, mean-variance minus 1/N, by window: negative means 1/N is ahead")
pd.DataFrame(gap_rows).set_index(["N", "market", "M"])["gap"].unstack("M").round(4)
"""),
    md("""
## Why the effect is small: what perfect knowledge would be worth

This check was added after the run to explain the result; it is not one of the pre-registered expectations. In the clustered market the true covariance of every month is known, so two ceilings can be computed. First, a minimum-variance rule that knew the current covariance exactly and re-solved its weights every month, against the same rule holding the fixed weights of the unconditional covariance: the most that any relative-weight rule could gain from tracking the regime. Second, the factor itself scaled up and down by the inverse of its current variance, normalised to the same average exposure, against the factor held fixed: the gain from changing the size of the whole position while its composition stays fixed. The paper's rules are all of the first kind; they decide how to split wealth between assets and stay fully invested.
"""),
    code("""
def sr(x):
    return float(np.mean(x) / np.std(x, ddof=1))

sf2 = C.SIM_FACTOR_SD_ANNUAL**2 / 12.0
rows = []
for N in C.SIM_N:
    g = markets[(N, "clustered volatility")]
    w_fixed = np.linalg.solve(g.Sigma, np.ones(N)); w_fixed = w_fixed / w_fixed.sum()
    r_fixed = g.returns @ w_fixed
    r_oracle = np.empty(len(g.returns)); moved = np.empty(len(g.returns))
    for t in range(len(g.returns)):
        w = np.linalg.solve(true_sigma(g, t), np.ones(N)); w = w / w.sum()
        r_oracle[t] = w @ g.returns[t]
        moved[t] = np.abs(w - w_fixed).sum()
    f = g.returns[:, 0]
    cond_var = sf2 * g.scales[:, 0] ** 2
    lev = 1.0 / cond_var; lev = lev / lev.mean()
    rows.append({"N": N, "min-var, fixed weights from the unconditional covariance": sr(r_fixed),
                 "min-var, weights from the true covariance of each month": sr(r_oracle),
                 "average total weight change between the two": moved.mean(),
                 "factor held fixed": sr(f), "factor scaled by 1 / its current variance": sr(lev * f)})
pd.DataFrame(rows).set_index("N")
"""),
    md("""
## What this notebook established, and what could be wrong

The three expectations are met as written. The second one predicted a visible loss, and no loss appears. The construction check: 12 of 12. The direction: 63 of 63 comparisons inside the slack, but the average change is +0.0015, the rules that depend on the shape of the covariance (minimum variance and its constrained versions) change by +0.001 to +0.002, and the only falls beyond noise are mean-variance and Bayes-Stein at the 120-month window on 10 and 50 assets (0.007 and 0.016), set against a rise of 0.005 on 25. The crossing for 10 assets moves from 3,000 to 4,000 months, as in notebook 05: one step of the grid, with the gap at 3,000 months within 0.001 of zero either way. Volatility that clusters at textbook strength, with the true correlation between assets moving from 0.31 in the calmest tenth of months to 0.59 in the stormiest, does not change the paper's comparison.

The oracle table explains the result. The paper's rules decide how to split a fixed sum between the assets, with all of it invested at every date. Two investors run minimum variance in the clustered market. The first holds one set of weights for all 2,000 years, the weights that are best on average. The second knows each month's true covariance in advance, recomputes the weights every month and moves 0.6 to 0.8 of the portfolio to follow them. The second earns a Sharpe ratio 0.003 to 0.005 higher, about 0.014 a year, which on a portfolio with 15% annual volatility is about 0.2% of extra return a year. This is the most that perfect knowledge of changing risk can be worth to a rule that only decides the split. A rule that estimates the covariance from 120 noisy months cannot come near that ceiling, so no loss could show. The ceiling is low because the Sharpe ratio changes very little when the weights move a little away from the best ones; the loss grows with the square of the error in the weights. A two-asset example shows the size of the effect. Two assets have the same expected return, the same volatility and no correlation, so the best split is 50/50. A 60/40 split has a Sharpe ratio 2% lower than the best one, a 70/30 split 7% lower, and a 90/10 split 22% lower. Being ten points off costs almost nothing, and only a large error costs much. The same fact lets 1/N do well throughout this project: its weights are wrong, and they are not wrong enough to matter.

A third investor holds only the factor and changes how much of it she holds: half the usual position in the stormiest months, more than usual in the calmest, so that the risk she carries is the same from month to month. In this market the factor's expected return does not change with its volatility, so she keeps the return and sheds the risk. She earns 0.010 more than holding the factor fixed, about 0.035 a year, or half a percent of return a year on the same portfolio, two to three times the second investor's gain, with no change in what she holds. Predictable volatility pays in the size of the whole position. None of the paper's rules can collect this gain, because all of them are fully invested at every date and decide only how to divide the money. The second study in this series, volatility-managed portfolios, is about the rule that does.

The paper's conclusion therefore depends on neither assumption of notebook 04. Fat tails of the same variance leave the means exactly as noisy as under normal shocks (notebook 05); volatility clustering moves the best weights, and the Sharpe ratio is insensitive to the move (this notebook). What this notebook does not settle. Three limits remain, and a fourth carries over from notebook 05. First, the clustering here is symmetric: a large gain raises next month's volatility exactly as much as a large loss of the same size, because the GARCH recursion uses the squared shock and the square has no sign. In real markets a loss raises volatility more than a gain does (the leverage effect), so turbulent periods follow falls more than rises; this market has no such asymmetry. Second, in this market the correlations between assets move for one reason only: when the factor's volatility rises relative to the assets' own volatility, more of each asset's movement is the common movement, so the correlations rise. In real markets correlations also change for reasons that have nothing to do with the factor's volatility, for example when investors sell many assets at once in a crisis. Third, the GARCH parameters, alpha 0.10 and beta 0.85, were fixed before the run and no others were tried, so the result holds for clustering of textbook strength and says nothing about stronger or weaker clustering. Fourth, every number comes from one draw of each market, as in notebook 05, so a difference of about 0.005 between two cells is of the size that a change of seed alone produces.
"""),
]

# ---------------------------------------------------------------------------
# 07: the replication extended to the latest month
# ---------------------------------------------------------------------------

NB07 = [
    md("""
# 07. The same test on twenty-one more years of data

**Terms used in this notebook.** Risk-free rate: the return on a one-month US Treasury bill, the closest thing to a return with no risk. Excess return: a return minus the risk-free rate over the same month. Sharpe ratio: the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken. Certainty-equivalent return (CEQ): the average return minus half the variance (times a risk aversion of one); the sure monthly return an investor would accept in place of the risky one. Turnover: the fraction of the portfolio bought and sold at a rebalance, summed over the assets; a turnover of 0.02 means that 2% of the portfolio changes hands in the month. Estimation window: the M months of past returns a rule sees when it forms its weights, 120 here. Rolling evaluation: moving the window forward one month at a time, forming the weights, and recording the return of the month after the window. Out-of-sample: measured on months the rule had not seen when it formed its weights. In-sample: measured on the same months that were used to form the weights. Estimation error: the difference between a mean or covariance estimated from a window and its true value. Band: the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover. Gated: said of a cell the band applies to. Verdict: pass or MISS for a gated cell. Vintage: the version of Ken French's files on the download date, named by the release of the CRSP database they were built from (202607 is the July 2026 release). Provenance: the record of what was downloaded, when, with its checksum and vintage. Factor: a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones. Upper bound: the Sharpe ratio a mean-variance investor would earn with no estimation error, from a rule estimated on the whole sample and judged on the same sample. Standard error: the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M. P-value: the probability of a difference at least as large as the one observed if the two rules were equally good; below 0.05 the difference is unlikely to be chance. Jobson-Korkie: the standard test of whether two Sharpe ratios measured on the same months differ; its result is reported as a p-value. Delta method: a standard way to obtain a standard error for a quantity built from means and variances, used for the CEQ. Sub-period: a slice of the out-of-sample months of one rolling evaluation; the weights at each date are the same whichever period they are reported in. Bayes-Stein: the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage. Minimum variance: the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns. Tangency portfolio: the mix of risky assets with the highest Sharpe ratio when the true means and covariances are known. Critical window: the window length at which sample-based mean-variance starts to beat 1/N on average.

**What this notebook does.** The paper's sample ends in November 2004. French's files run to the present, so the nine rules of notebooks 02 and 03 can be run through the same rolling evaluation on every month the vintage carries, from July 1963 to its last month, and the measures reported for three periods: the paper's own out-of-sample period (1973-07 to 2004-11, which reproduces notebooks 02 and 03), the months since the paper (from 2004-12, every one of them out of sample for a window that began 120 months earlier), and the whole period. No published number exists for the new months, so four expectations were written in `constants.py` before the run, each reported as a count.

**Why it comes seventh.** A replication that matches the paper's numbers on the paper's sample shows that the code is right. It does not show that the paper's conclusion holds beyond its sample, and the twenty-one years since 2004 include 2008 and 2020. Notebooks 04 to 06 say what to expect. The formula puts the critical window for the US calibration in the thousands of months, and the new period adds about 260. The simulations say the ranking does not depend on normal returns or on independent months. The expectation is therefore no change, and this notebook checks it on the data.

**What I expect to see, written before the run.** First, count first: every dataset has a return for every month from 1963-07 to the vintage's last month, the four datasets end in the same month, and the number of months is printed and recorded. Second, the paper's reading of Table 3 holds on the whole period: each short-sale-constrained rule has a higher out-of-sample Sharpe ratio than its unconstrained version on every dataset, twelve comparisons. Third, sample-based mean-variance is below 1/N on every dataset in the new period and in the whole period, eight cells. Fourth, the number of cells in the new period in which a rule beats 1/N with a Jobson-Korkie p-value below 0.05 is reported; on about 260 months the standard error of a Sharpe-ratio difference is about 0.06, so few or none are expected, and none would be claimed as a finding. Running time: about four minutes.
"""),
    md("""
## Modules

The modules of notebooks 02 and 03, unchanged except that `backtest` gains `subperiod`, which restricts a finished rolling evaluation to a range of out-of-sample months.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("dgu_published.py"),
    writefile("datasets.py"),
    writefile("rules.py"),
    writefile("backtest.py"),
    writefile("compare.py"),
    md("""
## Count first: the extended sample on today's vintage

The datasets are built with no end date, so they run to the last month every file carries. The first cell asserts the counts in expectation 1 and prints them, and records the vintage.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import numpy as np
import pandas as pd
from bp import constants as C
from bp import french_loader as fl
from bp import datasets as D
from bp import rules as S
from bp import backtest as B
from bp import compare as CMP
from bp import dgu_published as P

pd.set_option("display.width", 180)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

data = D.build_all(start=C.DGU_SAMPLE_START, end=None)
ends = {name: R.index[-1] for name, R in data.items()}
lengths = {name: len(R) for name, R in data.items()}
assert len(set(ends.values())) == 1, f"the datasets end in different months: {ends}"
assert len(set(lengths.values())) == 1, f"the datasets have different lengths: {lengths}"
for name, R in data.items():
    full = pd.period_range(R.index[0], R.index[-1], freq="M")
    assert len(R) == len(full), f"{name}: {len(full) - len(R)} months missing inside the sample"
    assert not R.isna().any().any()
    assert R.shape[1] == C.DGU_DATASETS[name]["N"]
LAST = next(iter(ends.values()))
T = next(iter(lengths.values()))
records = [fl.download(key) for key in ("factors3", "momentum", "ind10", "size_bm25")]
fl.write_provenance(records)
print(f"sample {C.DGU_SAMPLE_START} to {LAST}: {T} months per dataset, {T - C.DGU_ESTIMATION_WINDOW} out of sample")
print(f"paper's out-of-sample period: {pd.Period(C.DGU_SAMPLE_START, 'M') + C.DGU_ESTIMATION_WINDOW} to {C.DGU_SAMPLE_END}, {C.DGU_EXPECTED_OOS} months")
new_months = (LAST - pd.Period(C.EXTENDED_NEW_PERIOD_START, "M")).n + 1
print(f"new period: {C.EXTENDED_NEW_PERIOD_START} to {LAST}, {new_months} months")
print("vintage:", "; ".join(sorted({r["vintage_line"] for r in records})), "(provenance written to", C.PROVENANCE_FILE + ")")
"""),
    md("""
## Run the nine rules once, over the whole sample

One rolling evaluation per rule and dataset; the three periods are slices of the same out-of-sample series, so the paper's period reproduces notebooks 02 and 03 exactly.
"""),
    code("""
import time
ORDER = list(C.DGU_RULES)
PERIODS = {
    "paper (1973-07 to 2004-11)": (str(pd.Period(C.DGU_SAMPLE_START, "M") + C.DGU_ESTIMATION_WINDOW), C.DGU_SAMPLE_END),
    f"new ({C.EXTENDED_NEW_PERIOD_START} to {LAST})": (C.EXTENDED_NEW_PERIOD_START, str(LAST)),
    f"whole (1973-07 to {LAST})": (None, None),
}
runs, results, in_sample = {}, {}, {}
t0 = time.time()
for name, R in data.items():
    rules = dict(S.RULES)
    rules["vw"] = S.vw(list(R.columns).index("Mkt-RF"))
    bts = {k: B.rolling(R, rules[k], name=k) for k in ORDER}
    runs[name] = bts
    in_sample[name] = S.in_sample_sharpe(R.to_numpy())
    for period, (lo, hi) in PERIODS.items():
        results[(period, name)] = B.evaluate({k: B.subperiod(bt, lo, hi) for k, bt in bts.items()})
    print(f"{name:12s} done, {len(bts['ew'].oos)} out-of-sample months, {time.time() - t0:.0f}s so far")
"""),
    md("""
## The paper's period, on today's vintage

The first slice is the replication of notebooks 02 and 03 rerun on whatever vintage French serves today, with the same bands and the same gates. French revises history, so the pass count can move between vintages; this cell is the replication's own measure of how much the data have moved since the notebooks were first run.
"""),
    code("""
def table(measure, period):
    return pd.DataFrame({name: results[(period, name)][measure] for name in data}).loc[ORDER]

paper_period = list(PERIODS)[0]
res_paper = {name: results[(paper_period, name)] for name in data}
ins_paper = {name: S.in_sample_sharpe(R.loc[:pd.Period(C.DGU_SAMPLE_END, "M")].to_numpy()) for name, R in data.items()}
sh = CMP.sharpe_table(res_paper, ins_paper)
gated = sh[sh["verdict"].isin(["pass", "MISS"])]
turn = CMP.turnover_table(res_paper)
tg = turn[turn["verdict"].isin(["pass", "MISS"])]
print(f"paper's period on this vintage: gated Sharpe cells {len(gated)}, pass {int((gated['verdict'] == 'pass').sum())}, MISS {int((gated['verdict'] == 'MISS').sum())}; "
      f"gated turnover cells {len(tg)}, pass {int((tg['verdict'] == 'pass').sum())}, MISS {int((tg['verdict'] == 'MISS').sum())}")
print("Sharpe cells outside the band:")
print(gated[gated["verdict"] == "MISS"].to_string() if (gated["verdict"] == "MISS").any() else "  none")
print("turnover cells outside the band:")
print(tg[tg["verdict"] == "MISS"].to_string() if (tg["verdict"] == "MISS").any() else "  none")
"""),
    md("""
## Sharpe ratios by period

Monthly out-of-sample Sharpe ratios, one table per period, rules in rows and datasets in columns.
"""),
    code("""
for period in PERIODS:
    print(period)
    print(table("sharpe", period).round(4).to_string())
    print()
"""),
    md("""
## Expectations 2 and 3: the paper's two readings, on the new data
"""),
    code("""
whole = list(PERIODS)[2]
new = list(PERIODS)[1]
pairs = [("mv-c", "mv"), ("bs-c", "bs"), ("min-c", "min")]
rows = []
for name in data:
    sr = results[(whole, name)]["sharpe"]
    for c, u in pairs:
        rows.append({"dataset": name, "constrained": c, "unconstrained": u, "constrained Sharpe": sr[c], "unconstrained Sharpe": sr[u], "constrained higher": bool(sr[c] > sr[u])})
e2 = pd.DataFrame(rows).set_index(["dataset", "constrained"])
print(f"expectation 2: constrained beats unconstrained in {int(e2['constrained higher'].sum())} of {len(e2)} comparisons on the whole period")
print(e2.to_string())
print()
rows = []
for period in (new, whole):
    for name in data:
        sr = results[(period, name)]["sharpe"]
        rows.append({"period": period, "dataset": name, "mean-variance": sr["mv"], "1/N": sr["ew"], "1/N higher": bool(sr["ew"] > sr["mv"])})
e3 = pd.DataFrame(rows).set_index(["period", "dataset"])
print(f"expectation 3: 1/N above sample-based mean-variance in {int(e3['1/N higher'].sum())} of {len(e3)} cells")
e3
"""),
    md("""
## Expectation 4: who beats 1/N in the new period, and whether the data can tell

Every rule against 1/N on the months since the paper: the difference in Sharpe ratio and the Jobson-Korkie p-value. A rule counts as beating 1/N only if the difference is positive and the p-value below 0.05.
"""),
    code("""
rows = []
for name in data:
    fr = results[(new, name)]
    for rule in ORDER:
        if rule == "ew":
            continue
        rows.append({"dataset": name, "rule": rule, "Sharpe": fr.loc[rule, "sharpe"], "1/N": fr.loc["ew", "sharpe"],
                     "difference": fr.loc[rule, "sharpe"] - fr.loc["ew", "sharpe"], "p-value": fr.loc[rule, "sharpe_p"],
                     "beats 1/N at 5%": bool(fr.loc[rule, "sharpe"] > fr.loc["ew", "sharpe"] and fr.loc[rule, "sharpe_p"] < 0.05)})
e4 = pd.DataFrame(rows).set_index(["dataset", "rule"])
print(f"expectation 4: {int(e4['beats 1/N at 5%'].sum())} of {len(e4)} cells beat 1/N at the 5% level in the new period; "
      f"{int((e4['p-value'] < 0.05).sum())} cells differ from 1/N at the 5% level in either direction")
e4
"""),
    md("""
## Certainty-equivalent returns and turnover by period

CEQ with gamma = 1, and turnover: 1/N's own monthly turnover, every other rule relative to 1/N, as in the paper's Table 5.
"""),
    code("""
for period in PERIODS:
    print(period, ": CEQ")
    print(table("ceq", period).round(4).to_string())
    print()
"""),
    code("""
for period in PERIODS:
    t = table("turnover_rel", period)
    t.loc["ew"] = table("turnover", period).loc["ew"]
    print(period, ": turnover (1/N absolute, others relative to 1/N)")
    print(t.round(2).to_string())
    print()
"""),
    md("""
## The in-sample upper bound on the whole sample

Sample-based mean-variance estimated once on all the months, the Sharpe ratio a mean-variance investor would earn with no estimation error, beside the out-of-sample figure on the whole period. The gap between the two columns is the cost of estimation on sixty-three years of data.
"""),
    code("""
pd.DataFrame({"in sample, whole sample": pd.Series(in_sample), "out of sample, whole period": table("sharpe", whole).loc["mv"],
              "1/N, whole period": table("sharpe", whole).loc["ew"]})
"""),
    md("""
## What this notebook established, and what could be wrong

Expectation 1 holds. On the 202608 vintage every dataset runs without a gap from 1963-07 to 2026-08: 758 months, 638 of them out of sample, 261 since the paper. The paper's own period, rerun on this vintage, gives 29 of 30 gated Sharpe cells and 30 of 30 turnover cells inside the bands, the same counts as notebooks 02 and 03 found on the 202607 vintage, with the same single miss, minimum variance on FF-4-factor. One month of revisions changed no verdict.

Expectation 2 holds in 11 of 12 comparisons: over the whole period each short-sale-constrained rule beats its unconstrained version, except minimum variance on FF-1-factor, where the unconstrained rule (0.236) beats the constrained one (0.166) and is the best rule on that dataset over fifty-three years of out-of-sample months. Expectation 3 holds in 6 of 8 cells: 1/N is above sample-based mean-variance on every dataset over the whole period, and in the new period on Industry and FF-4-factor; on MKT/SMB/HML and FF-1-factor mean-variance is ahead in the new period by 0.06 and 0.03, with p-values of 0.46 and 0.72, so the data cannot tell the two apart. Expectation 4: one of 32 cells beats 1/N at the 5% level in the new period, and it is the market itself, vw, on MKT/SMB/HML. No optimising rule beats 1/N significantly on any dataset in the 261 new months. mv-c and bs-c sit within 0.02 of 1/N on Industry, FF-1-factor and FF-4-factor and 0.08 above it on MKT/SMB/HML with p-values above 0.10; the unconstrained mean-variance rule on Industry earns 0.04 against 1/N's 0.19.

The new period adds one thing the paper's period did not show. Minimum variance and its constrained versions, the best of the optimising rules in the paper, collapse on the two datasets whose assets include the factor portfolios: on MKT/SMB/HML they earn -0.015, -0.009 and 0.042 against 1/N's 0.113, and on FF-4-factor -0.034 and 0.038 against 0.148, each significantly worse at the 5% level. Minimum variance ignores expected returns and holds the lowest-variance assets; on MKT/SMB/HML it held, on average over the new period, 50% in SMB, 42% in HML and 9% in the market. SMB and HML earned 3.3% and 6.0% a year in the paper's period and -0.5% and -0.3% a year from 2004 to 2026, while the market earned 10.1%. A rule that ignores means pays nothing for estimation error in the means, and this is why it did well in the paper's period; it loses when the low-variance assets stop earning, and this is what happened after 2004. 1/N, which also ignores means, held a third in each and fell from 0.235 to 0.113; the market alone earned 0.191. Which of the two rules does better depends on which assets pay, and neither rule can know that in advance.

The in-sample upper bound on the whole sample, 0.19 to 0.42 across the datasets, against out-of-sample mean-variance of -0.01 to 0.13, shows the cost of estimation on sixty-three years of data. Twenty-one more years did not shrink it, as the formula of notebook 04 predicts.

What this notebook does not settle. The new period is 261 months, and 261 months is a short sample for comparing Sharpe ratios. A monthly Sharpe ratio measured on 261 months has a standard error of about 0.06, so the difference between two rules has to reach about 0.12 before its p-value falls below 0.05, that is, before it would arise by chance less than one time in twenty if the two rules were equally good. Most of the differences in the new-period table are smaller than that, so they cannot be told from chance, and the ranking of two rules 0.03 apart could reverse in another 261 months. The three periods were fixed before the run: the paper's own period, the months since, and the whole. A sub-period chosen after looking at the results could be made to favour almost any rule, and none was chosen. The last limit is the data vintage. French rebuilds his files every month from the latest CRSP database, and each rebuild revises some past returns slightly. This notebook ran on the 202608 vintage and notebooks 02 and 03 on the 202607 vintage, so the numbers for the paper's period differ in the third or fourth decimal between them; the provenance file written by each run records which vintage it used.
"""),
]


if __name__ == "__main__":
    for name, cells in [("01_french_loader.ipynb", NB01), ("02_1N_vs_mean_variance.ipynb", NB02), ("03_shrinkage_and_constraints.ipynb", NB03), ("04_critical_window_and_simulation.ipynb", NB04), ("05_fat_tails.ipynb", NB05), ("06_volatility_clustering.ipynb", NB06), ("07_extended_sample.ipynb", NB07)]:
        p = write(name, cells)
        print("wrote", p.relative_to(ROOT))
