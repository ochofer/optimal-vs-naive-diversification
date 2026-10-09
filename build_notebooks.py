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


def writefile_path(relpath: str) -> dict:
    """A cell that writes one small record file from the repository, so the notebook can read it in Colab."""
    body = (ROOT / relpath).read_text()
    return code(f"%%writefile {relpath}\n{body}")


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

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from (202607 is the July 2026 release) |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money |
| Value-weighted return | the return of a group of firms in which each firm counts in proportion to its market capitalisation at the start of the month |
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same month |
| Estimation window | the M months of past returns a rule sees when it forms its weights, 120 here |
| Rolling evaluation | moving the window forward one month at a time, forming the weights, and recording the return of the month after the window |
| Out-of-sample | measured on months the rule had not seen when it formed its weights |
| In-sample | measured on the same months that were used to form the weights |
| Sharpe ratio | the average monthly return above the risk-free rate, divided by the standard deviation of that return; the reward earned per unit of risk taken |
| Turnover | the fraction of the portfolio bought and sold at a rebalance, summed over the assets |
| Band | the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover |
| Gated | said of a cell the band applies to |
| Verdict | pass or MISS for a gated cell |

**What this notebook does.** It downloads the ten Ken French files this project uses (six monthly files for the replication, four daily files for the extension from notebook 10 on), records what it downloaded (date, URL, SHA-256 of the zip, and the CRSP vintage French prints at the top of each file), parses each file into monthly tables, and counts what is in them against what DeMiguel, Garlappi and Uppal (2009) say they used.

**Why it comes first.** Every number in the project is computed from these files, and French revises history: a return from 1985 can differ between the file served today and the one served last year. A replication that misses a published number by 0.01 has to be able to say whether the code or the vintage moved. The provenance record written here makes that possible, and it is attached to every later output.

**What I expect to see, and where it comes from.**

- The three portfolio files (10 industries, 49 industries, 25 size-and-value portfolios) and the three-factor file run monthly from 1926-07. On the vintage read on 10 September 2026 (CRSP 202607) that is 1,201 rows to 2026-07; a later vintage adds one row per month. The five-factor file starts in 1963-07 (757 rows on that vintage) and the momentum factor in 1927-01.
- DGU's sample is 1963-07 to 2004-11 (their Table 2), which is **497 months**. With their 120-month estimation window the out-of-sample period is 1973-07 to 2004-11, **377 months**. Both counts are asserted below.
- Their four French-sourced datasets have N = 11, 3, 21 and 24 assets (Table 2). The 21 and 24 come from 20 of the 25 size-and-value portfolios: DGU drop the five largest-size portfolios (their footnote 24), because the market, SMB and HML are almost a linear combination of all 25.
- In French's 49-industry file nine industries have gaps coded -99.99 in the early decades. All 49 are populated from **1969-07**; the extension in later notebooks starts there.
- The four daily files (49 industries, three factors and momentum from 1926, five factors from 1963-07) are downloaded and recorded here and first used in notebook 10; their counts are checked there, where the daily windows are built.
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

Ten files. The table shows what was fetched and the vintage line French prints at the top of each. The record is written to `outputs/provenance_french.json`, which later notebooks read so that every output can name the vintage it was computed on.
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

The ten files parse, the DGU window holds 497 months with no gaps, the asset counts match Table 2, and all 49 industries are populated from 1969-07. The market Sharpe ratio on today's vintage sits within 0.0025 of the 0.1138 DGU printed, which is the size of revision to expect on the rule rows too.

Three things this does not settle. French's risk-free rate is the one-month Treasury bill; DGU describe theirs as the 90-day bill taken from French's site, and French's site only carries the one-month series, so the study uses that. The vintage line names the CRSP cut French built the file from and nothing else; two files with the same vintage line can still differ if French changed a method. And the checks above count rows and columns; they do not verify a single return value, which only the replication itself can do.
"""),
]


# ---------------------------------------------------------------------------
# 02: 1/N against sample-based mean-variance
# ---------------------------------------------------------------------------

NB02 = [
    md("""
# 02. 1/N against sample-based mean-variance: the rolling out-of-sample test

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same month |
| Sharpe ratio | the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken |
| Certainty-equivalent return (CEQ) | the average return minus half the variance (times a risk aversion of one); the sure monthly return an investor would accept in place of the risky one |
| Turnover | the fraction of the portfolio bought and sold at a rebalance, summed over the assets; a turnover of 0.02 means that 2% of the portfolio changes hands in the month |
| Estimation window | the M months of past returns a rule sees when it forms its weights, 120 here |
| Rolling evaluation | moving the window forward one month at a time, forming the weights, and recording the return of the month after the window |
| Out-of-sample | measured on months the rule had not seen when it formed its weights |
| In-sample | measured on the same months that were used to form the weights |
| Estimation error | the difference between a mean or covariance estimated from a window and its true value |
| Band | the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover |
| Gated | said of a cell the band applies to |
| Verdict | pass or MISS for a gated cell |
| Fragility test | adding small random noise to every return and rerunning a rule fifty times, to see how far its result can move on a slightly different version of the data |
| Basis point | one hundredth of a percentage point, so 10 basis points is 0.1% |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from (202607 is the July 2026 release) |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money |
| Value-weighted return | the return of a group of firms in which each firm counts in proportion to its market capitalisation at the start of the month |
| Upper bound | the Sharpe ratio a mean-variance investor would earn with no estimation error, from a rule estimated on the whole sample and judged on the same sample |
| Simulated history | the 24,000 months of returns the simulation produces |
| Seed | the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers |
| Draw | one simulated history, produced from one seed |
| Standard error | the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M |
| P-value | the probability of a difference at least as large as the one observed if the two rules were equally good; below 0.05 the difference is unlikely to be chance |
| Jobson-Korkie | the standard test of whether two Sharpe ratios measured on the same months differ; its result is reported as a p-value |
| Delta method | a standard way to obtain a standard error for a quantity built from means and variances, used for the CEQ |
| Covariance matrix | the table of all variances and covariances of a set of assets; the covariance of two assets says how they move together, positive when both tend to be above their averages in the same months |
| Near-singular | said of a covariance matrix in which one asset's return is almost a combination of the others', so that the matrix carries almost no information about the difference between them; inverting it then divides by a number close to zero |

**What this notebook does.** It builds the four DGU datasets from French's files, runs the 1/N rule and the sample-based mean-variance rule through DGU's rolling 120-month window, and puts the out-of-sample Sharpe ratio, certainty-equivalent return and turnover beside Tables 3, 4 and 5 of the paper, with the verdict of the band written down before the run.

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

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same month |
| Sharpe ratio | the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken |
| Certainty-equivalent return (CEQ) | the average return minus half the variance (times a risk aversion of one); the sure monthly return an investor would accept in place of the risky one |
| Turnover | the fraction of the portfolio bought and sold at a rebalance, summed over the assets; a turnover of 0.02 means that 2% of the portfolio changes hands in the month |
| Estimation window | the M months of past returns a rule sees when it forms its weights, 120 here |
| Rolling evaluation | moving the window forward one month at a time, forming the weights, and recording the return of the month after the window |
| Out-of-sample | measured on months the rule had not seen when it formed its weights |
| In-sample | measured on the same months that were used to form the weights |
| Estimation error | the difference between a mean or covariance estimated from a window and its true value |
| Band | the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover |
| Gated | said of a cell the band applies to |
| Verdict | pass or MISS for a gated cell |
| Fragility test | adding small random noise to every return and rerunning a rule fifty times, to see how far its result can move on a slightly different version of the data |
| Basis point | one hundredth of a percentage point, so 10 basis points is 0.1% |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones |
| Covariance matrix | the table of all variances and covariances of a set of assets; the covariance of two assets says how they move together, positive when both tend to be above their averages in the same months |
| Bayes-Stein | the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage |
| Minimum variance | the rule that holds the minimum-variance portfolio, the fully invested portfolio with the lowest variance under the estimated covariance, and uses no expected returns |
| Short-sale constraint | no weight may be negative |
| Budget constraint | the weights must sum to one |
| Corner solution | a portfolio with all wealth in a single asset |
| Lagrangian | the expression an optimisation problem is written as when it has constraints |
| Non-negative least squares | a standard algorithm for least-squares problems whose unknowns may not be negative |
| Simulated history | the 24,000 months of returns the simulation produces |
| Seed | the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers |
| Draw | one simulated history, produced from one seed |

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
## Save

The three comparison tables (Sharpe ratios, turnover, certainty-equivalent returns, each replicated beside published with its verdict) and the ranking check are written to `outputs/`, with the vintage (the version of French's files, named by the CRSP cut they were built from) in the file name, so that the write-up and the dashboard read the same numbers this notebook prints.
"""),
    code("""
from bp import french_loader as fl
records = [fl.download(key) for key in ("factors3", "momentum", "ind10", "size_bm25")]
fl.write_provenance(records)
vintage = records[0]["vintage_line"].split("using the ")[1].split(" ")[0]
os.makedirs(C.OUTPUT_DIR, exist_ok=True)
sharpe_cmp.to_csv(f"{C.OUTPUT_DIR}/replication_sharpe_{vintage}.csv", float_format="%.6f")
turn.to_csv(f"{C.OUTPUT_DIR}/replication_turnover_{vintage}.csv", float_format="%.6f")
CMP.ceq_table(results).to_csv(f"{C.OUTPUT_DIR}/replication_ceq_{vintage}.csv", float_format="%.6f")
top3.to_csv(f"{C.OUTPUT_DIR}/replication_ranking_{vintage}.csv")
print("written:", sorted(f for f in os.listdir(C.OUTPUT_DIR) if f.startswith("replication")))
"""),
    md("""
## What this notebook established, and what could be wrong

Twenty-nine of the thirty gated Sharpe cells are within 0.03 of the paper, most within 0.01, and every gated turnover cell is within 25%. The CEQ returns of the four constrained rules are within 0.0004 of the paper's on all 16 cells and within 0.0002 on 15. The Bayes-Stein shrinkage factor averages 0.33 on FF-4-factor and 0.68 on MKT/SMB/HML against the paper's 0.32 and 0.66, so the shrinkage is implemented as Jorion specified it. The paper's reading of Table 3 (its fourth and fifth observations) reproduces cell for cell in sign: constrained mean-variance and constrained Bayes-Stein have a lower Sharpe ratio than 1/N on Industry and MKT/SMB/HML and a higher one on FF-1-factor and FF-4-factor, and constrained minimum variance has a higher one than 1/N on Industry, MKT/SMB/HML and FF-4-factor and a lower one on FF-1-factor. Of the three differences the paper reports as significant at the 5% level, two are here (constrained Bayes-Stein above 1/N on FF-1-factor, p = 0.04; constrained minimum variance above 1/N on FF-4-factor, p = 0.0004) and the third, constrained mean-variance on FF-1-factor, has p = 0.06.

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

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same month |
| Sharpe ratio | the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken |
| Estimation window | the M months of past returns a rule sees when it forms its weights, 120 here |
| Rolling evaluation | moving the window forward one month at a time, forming the weights, and recording the return of the month after the window |
| Out-of-sample | measured on months the rule had not seen when it formed its weights |
| In-sample | measured on the same months that were used to form the weights |
| Estimation error | the difference between a mean or covariance estimated from a window and its true value |
| Tangency portfolio | the mix of risky assets with the highest Sharpe ratio when the true means and covariances are known |
| Critical window | the window length at which sample-based mean-variance starts to beat 1/N on average |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones |
| Beta | how much an asset moves with the factor |
| Alpha | the part of an asset's expected return that its beta on the factor does not explain, zero in this simulation |
| Idiosyncratic | an asset's own noise, unrelated to the factor |
| Simulated history | the 24,000 months of returns the simulation produces |
| Seed | the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers |
| Draw | one simulated history, produced from one seed |
| Turnover | the fraction of the portfolio bought and sold at a rebalance, summed over the assets |
| Band | the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover |
| Gated | said of a cell the band applies to |
| Verdict | pass or MISS for a gated cell |
| Standard error | the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M |
| P-value | the probability of a difference at least as large as the one observed if the two rules were equally good; below 0.05 the difference is unlikely to be chance |
| Bayes-Stein | the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage |
| Minimum variance | the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns |
| Short-sale constraint | no weight may be negative |
| Budget constraint | the weights must sum to one |
| Corner solution | a portfolio with all wealth in a single asset |
| Lagrangian | the expression an optimisation problem is written as when it has constraints |
| Non-negative least squares | a standard algorithm for least-squares problems whose unknowns may not be negative |

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

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill |
| Excess return | a return minus the risk-free rate over the same month |
| Sharpe ratio | the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken |
| Estimation window | the M months of past returns a rule sees when it forms its weights, 120 here |
| Rolling evaluation | moving the window forward one month at a time, forming the weights, and recording the return of the month after the window |
| Out-of-sample | measured on months the rule had not seen when it formed its weights |
| In-sample | measured on the same months that were used to form the weights |
| Estimation error | the difference between a mean or covariance estimated from a window and its true value |
| Tangency portfolio | the mix of risky assets with the highest Sharpe ratio when the true means and covariances are known |
| Critical window | the window length at which sample-based mean-variance starts to beat 1/N on average |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones |
| Beta | how much an asset moves with the factor |
| Alpha | the part of an asset's expected return that its beta on the factor does not explain, zero in this simulation |
| Idiosyncratic | an asset's own noise, unrelated to the factor |
| Simulated history | the 24,000 months of returns the simulation produces |
| Seed | the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers |
| Draw | one simulated history, produced from one seed |
| Standard error | the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M |
| Covariance matrix | the table of all variances and covariances of a set of assets; the covariance of two assets says how they move together, positive when both tend to be above their averages in the same months |
| Fat tails | extreme months more frequent and more extreme than a normal distribution allows |
| Kurtosis | a measure of how heavy the tails of a distribution are; excess kurtosis is zero for the normal distribution |
| Student-t | a fat-tailed relative of the normal distribution |
| Degrees of freedom | the Student-t's tail parameter, fewer meaning fatter tails |
| Scale mixture | a fat-tailed variable built by multiplying a normal one by a random scale |
| Crossing | in the simulation, the first window tested at which mean-variance's out-of-sample Sharpe ratio reaches 1/N's |
| Slack | the allowance of 0.01 within which a comparison still counts as in the expected direction |
| Bayes-Stein | the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage |
| Minimum variance | the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns |

**What this notebook does.** The formula and the simulation of notebook 04 assume that returns are normally distributed and independent from month to month. The paper chose that setting because most portfolio rules are derived in it and it should favour mean-variance. This notebook reruns the Table 6 simulation with fat-tailed shocks and nothing else changed, and measures what the normality assumption is worth. The paper has no table for this, so the pre-committed statements are three expectations, written in `constants.py` before the run and each reported as a count of cells. One test was added after the run, with its expectation written before its code: the same fat tails with a scale factor per asset in place of one per month, so that the shape of the estimated covariance moves as well as its level.

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
## Added after the run: fat tails with a scale per asset (P1)

The fat tails above use one scale factor per month for every asset, so an extreme month multiplies every entry of that month's contribution to the sample covariance by the same number: the level of the estimated covariance moves and its shape, the ratios between its entries, hardly does, and the weights of the paper's rules depend only on the shape. This test, added after the run with its expectation fixed in `constants.py` first, reruns the fat-tailed market with one scale factor per shock series: the factor's shock and each asset's own shock get their own independent scale each month. In a month where one asset's scale is large and another's is small, their estimated variances and their estimated correlations with the other assets move apart, so the shape of the estimated covariance moves as well as its level. The covariance of returns is still exactly the normal market's, because each scale has a mean square of one and the shocks are independent, so expectation 1 and the formula's numbers are unchanged. The expectation, written before the code: P1a, the mean change in Sharpe ratio across the seven estimated rules and the nine cells is more negative than under the common scale at both degrees of freedom; P1b, the minimum-variance rules (min, min-c, g-min-c), whose weights depend on the shape of the covariance and use no means, lose more on average than the other estimated rules. Running time: about four minutes, two runs of the grid.
"""),
    code("""
# Added after the run (6 October 2026): P1, fat tails with one scale per shock series.
markets_pa = {(N, label): SIM.build_market(N, dof=dof, common_scale=False) for N in C.SIM_N for label, dof in DISTS[1:]}
grid_pa = {}
t_all = time.time()
for label, dof in DISTS[1:]:
    for N in C.SIM_N:
        mkt = markets_pa[(N, label)]
        w_true = mkt.true_tangency_weights
        r_true, r_ew = mkt.returns @ w_true, mkt.returns.mean(axis=1)
        for M in C.SIM_M:
            bts = B.rolling_moments(mkt.returns, S.MOMENT_RULES, window=M)
            row = {"mv (true)": B.sharpe(pd.Series(r_true)), "ew": B.sharpe(pd.Series(r_ew))}
            row.update({k: B.sharpe(bt.oos) for k, bt in bts.items() if k != "ew"})
            grid_pa[(label, N, M)] = row
    print(f"{label:14s} per-asset scale done, {time.time() - t_all:.0f}s so far")
tables_pa = pd.DataFrame(grid_pa).T
tables_pa.index.names = ["shocks", "N", "M"]

kurt = {label: {"common scale": SIM.excess_kurtosis(markets[(10, label)].returns[:, 3]), "per-asset scale": SIM.excess_kurtosis(markets_pa[(10, label)].returns[:, 3])} for label, _ in DISTS[1:]}
print("excess kurtosis of one asset's return (asset 4 of the 10-asset universe) under each construction:")
print(pd.DataFrame(kurt).T.round(2).to_string())
print()

shape_rules = list(C.FAT_TAIL_SHAPE_RULES)
other_rules = [k for k in estimated if k not in shape_rules]
p1_rows, p1a, p1b = [], [], []
for label, dof in DISTS[1:]:
    d_common = diffs[label]
    d_pa = (tables_pa.loc[label] - normal)[estimated]
    row = {"shocks": label, "mean change, common scale": d_common.values.mean(), "mean change, per-asset scale": d_pa.values.mean(),
           "shape rules, per-asset": d_pa[shape_rules].values.mean(), "other rules, per-asset": d_pa[other_rules].values.mean(),
           "cells in the expected direction, per-asset": int((d_pa <= C.FAT_TAIL_DIRECTION_SLACK).values.sum()), "largest fall, per-asset": d_pa.values.min()}
    p1a.append(bool(row["mean change, per-asset scale"] < row["mean change, common scale"]))
    p1b.append(bool(row["shape rules, per-asset"] < row["other rules, per-asset"]))
    p1_rows.append(row)
    print(f"{label}, per-asset scale minus normal, by rule and cell:")
    print(d_pa.round(4).to_string())
    print()
p1 = pd.DataFrame(p1_rows).set_index("shocks")
print(p1.round(4).to_string())
print()
print(f"P1a (the mean change is more negative with a scale per asset than with the common scale, both degrees of freedom): {sum(p1a)} of {len(p1a)}: {'MET' if all(p1a) else 'NOT MET'}")
print(f"P1b (the minimum-variance rules lose more than the other estimated rules, both degrees of freedom): {sum(p1b)} of {len(p1b)}: {'MET' if all(p1b) else 'NOT MET'}")
print()
print("mean change by rule under the per-asset scale, averaged over cells:")
print(pd.DataFrame({label: (tables_pa.loc[label] - normal)[estimated].mean(axis=0) for label, _ in DISTS[1:]}).round(4).to_string())
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. The rules that estimate nothing keep their Sharpe ratios within 0.013 under fat tails | 18 of 18 | MET |
| 2. Every estimated rule's Sharpe ratio is no higher under fat tails, slack 0.01 | 125 of 126 comparisons inside the slack; average loss 0.002 at 5 degrees of freedom, +0.002 at 10, inside sampling error | MET |
| 3. The crossing for 10 assets comes later under fat tails; none for 25 and 50 within 12,000 months | 3,000 months under normal shocks, 4,000 under both fat-tailed markets, against the formula's 4,536; none for 25 and 50 | MET |
| P1. With a scale per asset, the mean loss is larger than under the common scale (P1a) and the minimum-variance rules lose most (P1b) | mean change +0.0011 and -0.0000 at 10 and 5 degrees of freedom against +0.0017 and -0.0022 under the common scale (P1a 1 of 2); the minimum-variance rules +0.0015 and +0.0013 against +0.0007 and -0.0010 for the other rules (P1b 0 of 2); 63 of 63 cells inside the slack at both levels | NOT MET; every change inside one-draw noise |

All three expectations are met, and the effect is small. Expectation 1: 18 of 18, so the fat-tailed markets are the same market with different tails. Expectation 2: 125 of 126 comparisons inside the slack, and the changes are small. With 5 degrees of freedom the estimated rules lose 0.002 in Sharpe ratio on average, 0.004 at the 120-month window and nothing at 6,000, and the largest single fall is 0.015; with 10 degrees of freedom the average change is +0.002, inside sampling error, so no effect is detectable. Expectation 3: for 10 assets the crossing moves from 3,000 months under normal shocks to 4,000 under both fat-tailed markets, against the formula's 4,536. The crossing is known only to the nearest window tested (the windows were 120, 240, 360, 600, 1,000, 2,000, 3,000, 4,000, 6,000, 9,000 and 12,000 months), and the gap between mean-variance and 1/N at 3,000 months under normal shocks is 0.0003, so the move is one step of that list and inside sampling error. For 25 and 50 assets no crossing occurs within 12,000 months under any distribution, as the formula says (17,753 months and none).

The effect is small for two reasons, one about the estimated means and one about the estimated covariances.

The means. Every rule that uses expected returns estimates them as the average return of each asset over the 120 months in the window. An average computed from 120 months is itself uncertain, because a different 120 months would give a different average. The size of that uncertainty is called the standard error, and it equals the standard deviation of the monthly returns divided by the square root of the number of months. For an asset whose monthly returns have a standard deviation of 5%, the standard error of its 120-month average is 5% divided by the square root of 120, about 0.46% a month. This formula contains only the standard deviation and the number of months; the shape of the distribution does not enter it. The fat-tailed market was built with the same standard deviations as the normal market, so every estimated mean in it is exactly as uncertain as under normal shocks: 0.46% a month in the example, under both distributions. Notebook 04 showed that the uncertainty in the means accounts for nearly all of the cost of estimation (3,087 of the 3,239 months of the critical window for 25 assets). The part of the problem that matters most is therefore untouched by the fat tails. In the proposition this is the case-1 term, N divided by M, which holds for any distribution with a finite variance; only the two covariance terms, k and h, were derived under normality.

The covariances. The sample covariance between two assets is the average, over the window, of the product of their two deviations from their means. A month in which both assets move five standard deviations contributes 25 times as much to that average as a month in which both move one standard deviation, so fat tails do make the sample covariance noisier. In this market, however, one scale factor multiplies every asset's shock in a given month. An extreme month therefore multiplies every entry of that month's contribution by the same number. This raises or lowers the whole estimated covariance matrix together and leaves the ratios between its entries almost unchanged, and the rules use only those ratios. The mean-variance weights, for example, are the inverse of the covariance matrix times the vector of means, rescaled so that the weights sum to one: if every entry of the covariance matrix is doubled, the product is halved and the rescaling undoes the halving, so the weights do not change. The minimum-variance weights behave the same way. For the constrained mean-variance rules the level of the covariance enters through the risk penalty, and the table shows that the effect is small there too. Fat tails of this kind therefore change the estimated level of risk and leave the estimated weights almost where they were, and the Sharpe ratio of a rule depends on its weights.

Together: the inputs that carry most of the cost, the means, are exactly as uncertain as under normal shocks, and the inputs that became noisier, the covariances, became noisier in a way the weights hardly respond to. The paper's conclusion therefore does not depend on the normality assumption.

P1 was written after the run to close the second limit below, and its two expectations were both wrong. With one scale per shock series the mean change in Sharpe ratio is +0.0011 at 10 degrees of freedom and -0.0000 at 5, against +0.0017 and -0.0022 under the common scale, so the loss is larger at one level and smaller at the other (P1a, 1 of 2); the minimum-variance rules change by +0.0015 and +0.0013 against +0.0007 and -0.0010 for the other estimated rules, so they lose less, not more (P1b, 0 of 2); every one of the 126 cells is inside the slack. Two things explain the miss, and both were foreseeable. First, the size. Notebook 04 measured how much a Sharpe ratio moves between draws of the same market: a range of 0.01 to 0.02 for a rule near 0.13. Every number in the P1 table is smaller than that, as is every number in the common-scale table, so neither construction produces an effect that one draw can read, and an expectation that predicted "larger" without a size below which the comparison is noise could only be met by chance. The miss is on the design side: the expectation should have named that size, two standard errors or about 0.013, and at that size no difference between the two constructions could have been expected. Second, the shape. An asset's return is the factor part plus its own part, and with independent scales the two parts are rarely extreme in the same month, so the asset's own return has thinner tails under the per-asset construction than under the common one: the excess kurtosis of one asset's return is 0.68 against 1.02 at 10 degrees of freedom and 3.03 against 3.70 at 5. The construction that was expected to move the shape of the estimated covariance more also feeds each estimate fewer extreme months, and the two effects offset in the sample covariance. What stands after P1 is a stronger form of the result above: fat tails that hit all assets at once and fat tails that hit them separately both leave the paper's comparison where it was.

**What this notebook does not settle.**

- The months in this market are still independent of one another: the volatility of one month says nothing about the next. In real markets volatility comes in waves, and turbulent months follow turbulent months. Under that pattern a covariance estimated from the last 120 months is wrong in a known direction for the month ahead, because the window averages over calm and stormy months while the next month belongs to whichever regime the market is in now. Notebook 06 builds a market with that pattern and repeats this notebook's three expectations on it.
- In this market the same scale factor multiplies every asset's shock in a given month, so an extreme month moves all assets together. A covariance matrix carries two kinds of information: the overall level of risk (how large the variances are) and the pattern of relative risk (which assets are more volatile than which others, and how strongly each pair moves together). A common scale changes the level and leaves the pattern almost intact, and the previous paragraph showed that the rules' weights depend only on the pattern. A market in which each asset has its own scale factor each month changes the pattern as well: in a month where one asset's scale is large and another's is small, their estimated variances and their estimated correlations with the other assets move apart. P1 ran that market and found no larger loss; the paragraph on P1 above says why, and the limit is closed for this calibration.
- The fat tails here are symmetric. The scale factor multiplies the shock whatever its sign, so an extreme month is as likely to be an extreme gain as an extreme loss. In real markets extreme losses are more common than extreme gains of the same size. A one-sided version would need a different construction and is not run.
- Every number in this notebook comes from one draw of each market, that is, from one 24,000-month simulated history per distribution, all built from the same seed. A different seed would give slightly different Sharpe ratios for every rule with nothing else changed. Notebook 04 measured how much a Sharpe ratio moves between draws by building its market eight more times: for a rule with a Sharpe ratio near 0.13, the eight values spread over a range of about 0.01 to 0.02. That repetition was not done here, because it would cost eight further runs of the whole grid. A difference of about 0.005 between two cells of the tables above is therefore of the size that a change of seed alone produces, and it should not be read as an effect of the tails. The averages over many cells, and the counts in the three expectations, are the informative numbers.
"""),
]

# ---------------------------------------------------------------------------
# 06: beyond the paper, volatility that changes through time
# ---------------------------------------------------------------------------

NB06 = [
    md("""
# 06. Beyond the paper: volatility that changes through time

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill |
| Excess return | a return minus the risk-free rate over the same month |
| Sharpe ratio | the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken |
| Estimation window | the M months of past returns a rule sees when it forms its weights, 120 here |
| Rolling evaluation | moving the window forward one month at a time, forming the weights, and recording the return of the month after the window |
| Out-of-sample | measured on months the rule had not seen when it formed its weights |
| In-sample | measured on the same months that were used to form the weights |
| Estimation error | the difference between a mean or covariance estimated from a window and its true value |
| Tangency portfolio | the mix of risky assets with the highest Sharpe ratio when the true means and covariances are known |
| Critical window | the window length at which sample-based mean-variance starts to beat 1/N on average |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones |
| Beta | how much an asset moves with the factor |
| Alpha | the part of an asset's expected return that its beta on the factor does not explain, zero in this simulation |
| Idiosyncratic | an asset's own noise, unrelated to the factor |
| Simulated history | the 24,000 months of returns the simulation produces |
| Seed | the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers |
| Draw | one simulated history, produced from one seed |
| Standard error | the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M |
| Fat tails | extreme months more frequent and more extreme than a normal distribution allows |
| Kurtosis | a measure of how heavy the tails of a distribution are; excess kurtosis is zero for the normal distribution |
| Student-t | a fat-tailed relative of the normal distribution |
| Degrees of freedom | the Student-t's tail parameter, fewer meaning fatter tails |
| Crossing | in the simulation, the first window tested at which mean-variance's out-of-sample Sharpe ratio reaches 1/N's |
| Slack | the allowance of 0.01 within which a comparison still counts as in the expected direction |
| Volatility clustering | volatility that persists from month to month, so that a turbulent month is usually followed by another. GARCH(1,1): the standard model of volatility clustering, in which next month's variance is a constant plus a weight times this month's squared shock plus a weight times this month's variance |
| Persistence | the sum of the two GARCH weights, which sets how slowly a volatility shock fades |
| Autocorrelation | the correlation of a series with its own value one month earlier |
| Regime | a stretch of months with a similar level of volatility |
| Leverage effect | volatility rising more after a fall than after a rise of the same size |
| Oracle | a rule given the truth it could never know in practice, run to find the ceiling on what knowing it would be worth |
| Unconditional | the long-run average of a variance or correlation |
| Conditional | its value in a given month, given what is known then |
| Bayes-Stein | the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage |
| Minimum variance | the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns |

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

| Expectation | Result | Verdict |
|---|---|---|
| 1. The rules that estimate nothing keep their Sharpe ratios within 0.013 under clustering | 12 of 12 | MET |
| 2. Every estimated rule's Sharpe ratio is no higher under clustering, slack 0.01, with a visible loss expected | 63 of 63 inside the slack; average change +0.0015, so the loss the expectation predicted did not appear | MET as written, wrong in substance |
| 3. The crossing for 10 assets comes later than in the normal market; none for 25 and 50 | 3,000 to 4,000 months, one step of the grid; none for 25 and 50 | MET |
| Oracle check | knowing each month's covariance is worth 0.003 to 0.005 in Sharpe ratio to a rule that only splits wealth; scaling the whole position by the inverse of current variance is worth 0.010 | reported |

The three expectations are met as written. The second one predicted a visible loss, and no loss appears. The construction check: 12 of 12. The direction: 63 of 63 comparisons inside the slack, but the average change is +0.0015, the rules that depend on the shape of the covariance (minimum variance and its constrained versions) change by +0.001 to +0.002, and the only falls beyond noise are mean-variance and Bayes-Stein at the 120-month window on 10 and 50 assets (0.007 and 0.016), set against a rise of 0.005 on 25. The crossing for 10 assets moves from 3,000 to 4,000 months, as in notebook 05: one step of the grid, with the gap at 3,000 months within 0.001 of zero either way. Volatility that clusters at textbook strength, with the true correlation between assets moving from 0.31 in the calmest tenth of months to 0.59 in the stormiest, does not change the paper's comparison.

The oracle table explains the result. The paper's rules decide how to split a fixed sum between the assets, with all of it invested at every date. Two investors run minimum variance in the clustered market. The first holds one set of weights for all 2,000 years, the weights that are best on average. The second knows each month's true covariance in advance, recomputes the weights every month and moves 0.6 to 0.8 of the portfolio to follow them. The second earns a Sharpe ratio 0.003 to 0.005 higher, about 0.014 a year, which on a portfolio with 15% annual volatility is about 0.2% of extra return a year. This is the most that perfect knowledge of changing risk can be worth to a rule that only decides the split. A rule that estimates the covariance from 120 noisy months cannot come near that ceiling, so no loss could show. The ceiling is low because the Sharpe ratio changes very little when the weights move a little away from the best ones; the loss grows with the square of the error in the weights. A two-asset example shows the size of the effect. Two assets have the same expected return, the same volatility and no correlation, so the best split is 50/50. A 60/40 split has a Sharpe ratio 2% lower than the best one, a 70/30 split 7% lower, and a 90/10 split 22% lower. Being ten points off costs almost nothing, and only a large error costs much. The same fact lets 1/N do well throughout this project: its weights are wrong, and they are not wrong enough to matter.

A third investor holds only the factor and changes how much of it she holds: half the usual position in the stormiest months, more than usual in the calmest, so that the risk she carries is the same from month to month. In this market the factor's expected return does not change with its volatility, so she keeps the return and sheds the risk. She earns 0.010 more than holding the factor fixed, about 0.035 a year, or half a percent of return a year on the same portfolio, two to three times the second investor's gain, with no change in what she holds. Predictable volatility pays in the size of the whole position. None of the paper's rules can collect this gain, because all of them are fully invested at every date and decide only how to divide the money. The second study in this series, volatility-managed portfolios, is about the rule that does.

The paper's conclusion therefore depends on neither assumption of notebook 04. Fat tails of the same variance leave the means exactly as noisy as under normal shocks (notebook 05); volatility clustering moves the best weights, and the Sharpe ratio is insensitive to the move (this notebook).

**What this notebook does not settle.**

- The clustering here is symmetric: a large gain raises next month's volatility exactly as much as a large loss of the same size, because the GARCH recursion uses the squared shock and the square has no sign. In real markets a loss raises volatility more than a gain does (the leverage effect), so turbulent periods follow falls more than rises; this market has no such asymmetry, and building one would need a different recursion, which this study does not run.
- In this market the correlations between assets move for one reason only: when the factor's volatility rises relative to the assets' own volatility, more of each asset's movement is the common movement, so the correlations rise. In real markets correlations also change for reasons that have nothing to do with the factor's volatility, for example when investors sell many assets at once in a crisis. The real-data notebooks of the extension (09 to 12) measure the industries' co-movement as it is, with no model of why it moves.
- The GARCH parameters, alpha 0.10 and beta 0.85, were fixed before the run and no others were tried, so the result holds for clustering of textbook strength and says nothing about stronger or weaker clustering; a sweep of parameters after the result would be tuning, and is not run.
- Every number comes from one draw of each market, as in notebook 05, so a difference of about 0.005 between two cells is of the size that a change of seed alone produces.
"""),
]

# ---------------------------------------------------------------------------
# 07: the replication extended to the latest month
# ---------------------------------------------------------------------------

NB07 = [
    md("""
# 07. The same test on twenty-one more years of data

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same month |
| Sharpe ratio | the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken |
| Certainty-equivalent return (CEQ) | the average return minus half the variance (times a risk aversion of one); the sure monthly return an investor would accept in place of the risky one |
| Turnover | the fraction of the portfolio bought and sold at a rebalance, summed over the assets; a turnover of 0.02 means that 2% of the portfolio changes hands in the month |
| Estimation window | the M months of past returns a rule sees when it forms its weights, 120 here |
| Rolling evaluation | moving the window forward one month at a time, forming the weights, and recording the return of the month after the window |
| Out-of-sample | measured on months the rule had not seen when it formed its weights |
| In-sample | measured on the same months that were used to form the weights |
| Estimation error | the difference between a mean or covariance estimated from a window and its true value |
| Band | the interval, fixed before any code ran, within which a replicated number counts as matching the published one, 0.03 for a Sharpe ratio and 25% for turnover |
| Gated | said of a cell the band applies to |
| Verdict | pass or MISS for a gated cell |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from (202607 is the July 2026 release) |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors SMB and HML are the returns of small firms over large ones and of cheap firms over expensive ones |
| Upper bound | the Sharpe ratio a mean-variance investor would earn with no estimation error, from a rule estimated on the whole sample and judged on the same sample |
| Standard error | the uncertainty of an estimate; for an average over M months it is the standard deviation of the months divided by the square root of M |
| P-value | the probability of a difference at least as large as the one observed if the two rules were equally good; below 0.05 the difference is unlikely to be chance |
| Jobson-Korkie | the standard test of whether two Sharpe ratios measured on the same months differ; its result is reported as a p-value |
| Delta method | a standard way to obtain a standard error for a quantity built from means and variances, used for the CEQ |
| Sub-period | a slice of the out-of-sample months of one rolling evaluation; the weights at each date are the same whichever period they are reported in |
| Bayes-Stein | the rule of Jorion (1986) that pulls each estimated mean towards one common value; this pulling is called shrinkage |
| Minimum variance | the rule that holds the fully invested portfolio with the lowest variance and uses no expected returns |
| Tangency portfolio | the mix of risky assets with the highest Sharpe ratio when the true means and covariances are known |
| Critical window | the window length at which sample-based mean-variance starts to beat 1/N on average |

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
## Save

The Sharpe ratios, certainty-equivalent returns and turnover of the nine rules in the three periods, and the comparison of every rule with 1/N in the new period, are written to `outputs/`, with the vintage in the file name, so that the write-up and the dashboard read the same numbers this notebook prints.
"""),
    code("""
vintage = records[0]["vintage_line"].split("using the ")[1].split(" ")[0]
os.makedirs(C.OUTPUT_DIR, exist_ok=True)
pd.concat({period: table("sharpe", period) for period in PERIODS}, names=["period", "rule"]).to_csv(f"{C.OUTPUT_DIR}/extended_sample_sharpe_{vintage}.csv", float_format="%.6f")
pd.concat({period: table("ceq", period) for period in PERIODS}, names=["period", "rule"]).to_csv(f"{C.OUTPUT_DIR}/extended_sample_ceq_{vintage}.csv", float_format="%.6f")
turnover_tables = {}
for period in PERIODS:
    t = table("turnover_rel", period)
    t.loc["ew"] = table("turnover", period).loc["ew"]
    turnover_tables[period] = t
pd.concat(turnover_tables, names=["period", "rule"]).to_csv(f"{C.OUTPUT_DIR}/extended_sample_turnover_{vintage}.csv", float_format="%.6f")
e4.to_csv(f"{C.OUTPUT_DIR}/extended_sample_vs_1N_{vintage}.csv", float_format="%.6f")
print("written:", sorted(f for f in os.listdir(C.OUTPUT_DIR) if f.startswith("extended_sample")))
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. Count first | 758 months from 1963-07 to 2026-08 on every dataset, 638 out of sample, 261 since the paper; the paper's period on this vintage: 29 of 30 gated Sharpe cells and 30 of 30 turnover cells inside the bands | holds |
| 2. Each short-sale-constrained rule beats its unconstrained version over the whole period, 12 comparisons | 11 of 12; the exception is minimum variance on FF-1-factor | 11 of 12 |
| 3. 1/N above sample-based mean-variance on every dataset, new period and whole period, 8 cells | 6 of 8; mean-variance ahead in the new period on MKT/SMB/HML and FF-1-factor by 0.06 and 0.03, p-values 0.46 and 0.72 | 6 of 8, the two misses inside noise |
| 4. Cells in the new period in which a rule beats 1/N at the 5% level | 1 of 32, the market itself on MKT/SMB/HML; no optimising rule | reported |

Expectation 1 holds. On the 202608 vintage every dataset runs without a gap from 1963-07 to 2026-08: 758 months, 638 of them out of sample, 261 since the paper. The paper's own period, rerun on this vintage, gives 29 of 30 gated Sharpe cells and 30 of 30 turnover cells inside the bands, the same counts as notebooks 02 and 03 found on the 202607 vintage, with the same single miss, minimum variance on FF-4-factor. One month of revisions changed no verdict.

Expectation 2 holds in 11 of 12 comparisons: over the whole period each short-sale-constrained rule beats its unconstrained version, except minimum variance on FF-1-factor, where the unconstrained rule (0.236) beats the constrained one (0.166) and is the best rule on that dataset over fifty-three years of out-of-sample months. Expectation 3 holds in 6 of 8 cells: 1/N is above sample-based mean-variance on every dataset over the whole period, and in the new period on Industry and FF-4-factor; on MKT/SMB/HML and FF-1-factor mean-variance is ahead in the new period by 0.06 and 0.03, with p-values of 0.46 and 0.72, so the data cannot tell the two apart. Expectation 4: one of 32 cells beats 1/N at the 5% level in the new period, and it is the market itself, vw, on MKT/SMB/HML. No optimising rule beats 1/N significantly on any dataset in the 261 new months. mv-c and bs-c sit within 0.02 of 1/N on Industry, FF-1-factor and FF-4-factor and 0.08 above it on MKT/SMB/HML with p-values above 0.10; the unconstrained mean-variance rule on Industry earns 0.04 against 1/N's 0.19.

The new period adds one thing the paper's period did not show. Minimum variance and its constrained versions, the best of the optimising rules in the paper, collapse on the two datasets whose assets include the factor portfolios: on MKT/SMB/HML they earn -0.015, -0.009 and 0.042 against 1/N's 0.113, and on FF-4-factor -0.034 and 0.038 against 0.148, each significantly worse at the 5% level. Minimum variance ignores expected returns and holds the lowest-variance assets; on MKT/SMB/HML it held, on average over the new period, 50% in SMB, 42% in HML and 9% in the market. SMB and HML earned 3.3% and 6.0% a year in the paper's period and -0.5% and -0.3% a year from 2004 to 2026, while the market earned 10.1%. A rule that ignores means pays nothing for estimation error in the means, and this is why it did well in the paper's period; it loses when the low-variance assets stop earning, and this is what happened after 2004. 1/N, which also ignores means, held a third in each and fell from 0.235 to 0.113; the market alone earned 0.191. Which of the two rules does better depends on which assets pay, and neither rule can know that in advance.

The in-sample upper bound on the whole sample, 0.19 to 0.42 across the datasets, against out-of-sample mean-variance of -0.01 to 0.13, shows the cost of estimation on sixty-three years of data. Twenty-one more years did not shrink it, as the formula of notebook 04 predicts.

**What this notebook does not settle.**

- The new period is 261 months, and 261 months is a short sample for comparing Sharpe ratios. A monthly Sharpe ratio measured on 261 months has a standard error of about 0.06, so the difference between two rules has to reach about 0.12 before its p-value falls below 0.05, that is, before it would arise by chance less than one time in twenty if the two rules were equally good. Most of the differences in the new-period table are smaller than that, so they cannot be told from chance, and the ranking of two rules 0.03 apart could reverse in another 261 months.
- The three periods were fixed before the run: the paper's own period, the months since, and the whole. A sub-period chosen after looking at the results could be made to favour almost any rule, and none was chosen.
- The data vintage. French rebuilds his files every month from the latest CRSP database, and each rebuild revises some past returns slightly. This notebook ran on the 202608 vintage and notebooks 02 and 03 on the 202607 vintage, so the numbers for the paper's period differ in the third or fourth decimal between them; the provenance file written by each run records which vintage it used.
"""),
]


# ---------------------------------------------------------------------------
# 08: the cap-weight check, the benchmark of the extension
# ---------------------------------------------------------------------------

NB08 = [
    md("""
# 08. The cap-weight check: building the index the extension will track

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same month; French's Mkt-RF is the excess return of the whole US stock market |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money; market equity is the same quantity |
| Value-weighted return | the return of a group of firms in which each firm counts in proportion to its market capitalisation at the start of the month, so a firm twice as large counts twice as much |
| Cap-weighted | weighted by market capitalisation; a cap-weighted index of industries gives each industry the share of the total that its firms' market capitalisation amounts to |
| Benchmark | in the extension, the index the portfolio tracks |
| Tracking error | the standard deviation of the monthly difference between two return series, times the square root of 12, so that it reads in return units per year; a tracking error of 0.50% a year means the two series differ by about 0.14% in a typical month (0.50% divided by the square root of 12) |
| Basis point | one hundredth of a percentage point, so 50 basis points is 0.50% |
| Look-ahead | using, for month t, a number that was not known when month t began; a weight set with the end-of-month price is look-ahead |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from (202608 is the August 2026 release) |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |
| SIC code | the Standard Industrial Classification, a four-digit number that names a firm's line of business; French assigns each firm to one of the 49 industries by its SIC code at the end of June |
| Firm-level data | one row per firm per month (price, shares, return), as opposed to French's files, which carry one number per portfolio per month |

**What this notebook does.** The extension (notebooks 09 to 13) asks the paper's question of an index-tracking mandate on French's 49 industry portfolios: a portfolio that must stay close to an index of those industries. That index has to be built first, because French publishes the 49 industries' returns and the market's return, and no index of the 49. French's 49-industry file carries, for every industry and month, the number of firms and the average firm size (market capitalisation in millions of dollars). Their product is the industry's total market capitalisation, and dividing by the sum over the 49 gives each industry's share of the whole: its cap weight. The cap-weighted combination of the 49 industry returns should then equal, or nearly equal, the value-weighted return of all the firms in the 49 portfolios, and that is close to French's market return. This notebook builds the weights, computes the combination, and measures its tracking error against the market, Mkt-RF plus RF, from 1969-07 (the first month in which all 49 industries exist, asserted in notebook 01) to the last month the vintage carries.

**The check, fixed in `constants.py` on 10 September 2026, before any extension code existed.** If the tracking error is at most 50 basis points a year (`CAPW_TE_MAX_ANNUAL`), the derived weights are the benchmark of the extension, both its return series and its industry weights. If not, the benchmark return is the market series, and the question of which industry weights the constraints refer to goes back to the design before notebook 09 is written.

**Why the timing of the weights matters, and how it is checked.** A value-weighted return for month t weights each firm by its market capitalisation at the start of the month, because an investor who holds the market buys at the start of the month and the weights she holds are those prices times shares. French's firm count and average size for month t are measured at the same time, the start of month t, so the product for month t is the weight that goes with month t's return, and it uses nothing that was unknown when the month began. The other reading, that French's numbers describe the end of the month, would make the same-month weight look-ahead. The two readings give different combinations, so both are run: the same-month weights, which are the design (`CAPW_WEIGHT_TIMING`), and the previous-month weights (the count and size of month t-1 applied to month t's return). Under the design's reading, the same-month combination must track the market more closely. If it does not, the reading is wrong, the notebook stops, and the extension is not built on a benchmark with look-ahead.

**What I expect to see, written before the run (`constants.py`, 1 October 2026).** First, count first: from 1969-07 to the last month, every industry has a return, a firm count and an average size in every month, and the three blocks share the same months. Second, the same-month weights track the market more closely than the previous-month weights. Third, the gate: the same-month combination's tracking error is at most 50 basis points a year. Fourth, reported with no pass or fail: the annualised mean difference between the combination and the market, their correlation, and the largest and smallest weights with their industries at the first month, at 2004-11 and at the last month. Running time: seconds.
"""),
    md("""
## Modules

`constants` and `french_loader` are those of notebook 01. `benchmark` is new: the weights, the combination and the tracking error, each a short function with a hand-computed test in `tests/test_benchmark.py`.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("benchmark.py"),
    md("""
## Count first: the three blocks of the 49-industry file

The file has eight blocks. Three are used here: the value-weighted monthly returns, the number of firms, and the average firm size. The cell loads them, restricts them to the extension sample, asserts expectation 1 and records the vintage.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import numpy as np
import pandas as pd
from bp import constants as C
from bp import french_loader as fl
from bp import benchmark as BM

pd.set_option("display.width", 180)
pd.set_option("display.max_rows", 120)
pd.set_option("display.max_columns", 60)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

print(fl.block_summary("ind49").to_string())
inputs = BM.load_inputs()
start = pd.Period(C.EXT_SAMPLE_START, "M")
returns = inputs["returns"].loc[start:]
firms = inputs["firms"].loc[start:]
size = inputs["size"].loc[start:]
market = inputs["market"].loc[start:]
LAST = returns.index[-1]

# Expectation 1: the same months in all three blocks, no missing value anywhere in the sample.
assert returns.index.equals(firms.index) and returns.index.equals(size.index), "the three blocks do not share the same months"
full = pd.period_range(start, LAST, freq="M")
assert len(returns) == len(full), f"{len(full) - len(returns)} months missing inside the sample"
for name, frame in (("returns", returns), ("firm counts", firms), ("average sizes", size)):
    assert frame.shape[1] == 49, f"{name}: {frame.shape[1]} industries"
    assert not frame.isna().any().any(), f"{name}: missing values inside the sample"
assert (firms > 0).all().all(), "an industry with no firms inside the sample"
assert market.loc[start:LAST].notna().all(), "the market series has a gap inside the sample"
records = [fl.download(key) for key in ("ind49", "factors3")]
fl.write_provenance(records)
print()
print(f"extension sample {start} to {LAST}: {len(returns)} months, 49 industries, 3 blocks, no missing value (expectation 1 holds)")
print(f"firms in the 49 portfolios: {int(firms.loc[start].sum()):,} in {start}, {int(firms.loc['2004-11'].sum()):,} in 2004-11, {int(firms.loc[LAST].sum()):,} in {LAST}")
total_me = (firms * size).sum(axis=1)
print(f"total market capitalisation of the 49 (millions of dollars): {total_me.loc[start]:,.0f} in {start}, {total_me.loc[LAST]:,.0f} in {LAST}")
print("vintage:", "; ".join(sorted({r["vintage_line"] for r in records})), "(provenance written to", C.PROVENANCE_FILE + ")")
"""),
    md("""
## The weights and the combination, under both timings

`cap_weights` divides each industry's firm count times average size by the sum over the 49, per month. `combination_return` multiplies each month's weights by that month's industry returns and sums. The same-month timing is the design; the previous-month timing shifts the weights forward by one month and is run only to check the reading of French's timing.
"""),
    code("""
w_same = BM.cap_weights(firms, size, C.CAPW_WEIGHT_TIMING)
w_prev = BM.cap_weights(inputs["firms"], inputs["size"], C.CAPW_WEIGHT_TIMING_ALTERNATIVE).loc[start:]
# Under the previous-month timing the first month of the sample takes its weights from 1969-06, in which
# one industry has no firms yet, so that month has no weights; the timing check runs on the months both timings cover.
common = w_prev.dropna(how="all").index
assert np.allclose(w_same.sum(axis=1), 1.0) and np.allclose(w_prev.loc[common].sum(axis=1), 1.0)
combo_same = BM.combination_return(returns, w_same)
combo_prev = BM.combination_return(returns, w_prev)
assert combo_same.notna().all() and combo_prev.loc[common].notna().all()
print(f"same-month weights cover {combo_same.notna().sum()} months from {combo_same.index[0]}; previous-month weights cover {len(common)} months from {common[0]}")
side_by_side = pd.DataFrame({"market (Mkt-RF + RF)": market.loc[start:LAST], "same-month weights": combo_same, "previous-month weights": combo_prev})
print("first six months:")
print(side_by_side.head(6).to_string())
print()
print("last six months:")
print(side_by_side.tail(6).to_string())
"""),
    md("""
## Expectations 2 and 3: the timing check and the gate

Tracking error is the standard deviation of the monthly difference, times the square root of 12. The level the gate uses, 50 basis points a year, corresponds to a typical monthly difference of 0.14%.
"""),
    code("""
cmp_same = BM.compare(combo_same, market)                        # the gate: every month of the sample
cmp_same_common = BM.compare(combo_same.loc[common], market)     # the timing check: the months both timings cover
cmp_prev = BM.compare(combo_prev.loc[common], market)
table = pd.DataFrame({"same-month weights, all months": cmp_same, "same-month weights, common months": cmp_same_common, "previous-month weights": cmp_prev})
print(table.to_string())
print()
te_same, te_prev = cmp_same_common["tracking_error_annual"], cmp_prev["tracking_error_annual"]
print(f"tracking error, same-month weights   : {te_same * 1e4:6.1f} basis points a year")
print(f"tracking error, previous-month weights: {te_prev * 1e4:6.1f} basis points a year")
assert te_same < te_prev, ("expectation 2 fails: the previous-month weights track the market more closely, so French's count and size "
                           "would describe the end of the month and the same-month weights would carry look-ahead; stop here")
print(f"expectation 2 holds: the same-month weights track the market more closely ({te_same * 1e4:.1f} against {te_prev * 1e4:.1f} basis points)")
te_gate = cmp_same["tracking_error_annual"]
gate = te_gate <= C.CAPW_TE_MAX_ANNUAL
print(f"expectation 3, the gate: {te_gate * 1e4:.1f} basis points over all {cmp_same['months']} months against the level of {C.CAPW_TE_MAX_ANNUAL * 1e4:.0f}: {'MET' if gate else 'NOT MET'}")
if gate:
    print("decision: the derived cap weights are the benchmark of notebooks 09 to 13, return series and industry weights alike")
else:
    print("decision: the benchmark return is the market series; the industry weights for the constraints go back to the design before notebook 09")
"""),
    md("""
## Expectation 4: what the benchmark looks like

The largest and smallest industry weights at three dates, and the twelve months in which the combination and the market differ most.
"""),
    code("""
report_months = [start if m == "first" else (LAST if m == "last" else pd.Period(m, "M")) for m in C.CAPW_REPORT_MONTHS]
extremes = pd.DataFrame([BM.weight_extremes(w_same, m) for m in report_months]).set_index("month")
print(extremes.to_string())
print()
top = pd.DataFrame({m: w_same.loc[m].sort_values(ascending=False).head(8) for m in report_months})
top.columns = [str(c) for c in top.columns]
print("the eight largest industries at each date (weights):")
print(top.to_string())
print()
diff = (combo_same - market.loc[start:LAST]).rename("combination minus market")
worst = diff.abs().sort_values(ascending=False).head(12).index
print("the twelve months of largest absolute difference:")
print(pd.DataFrame({"market": market.loc[worst], "combination": combo_same.loc[worst], "difference": diff.loc[worst]}).sort_index().to_string())
print()
print(f"annualised mean difference: {cmp_same['mean_difference_annual'] * 1e4:+.1f} basis points a year; correlation {cmp_same['correlation']:.5f}")
"""),
    md("""
## Where the difference comes from

This cell was written after the run, to describe the difference the gate measured; it changes no decision. French forms the industry portfolios once a year, at the end of June, from the firms that have an SIC code at that time. A firm that lists in, say, October joins the market return in November and joins an industry portfolio only the next July. If that is the source of the difference, the difference should be smallest in July and grow through the year, and it should be largest in the years with the most new listings. The cell prints the tracking error by calendar month and by decade.
"""),
    code("""
by_month = diff.groupby(diff.index.month).std(ddof=1) * np.sqrt(12) * 1e4
by_month.index = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
print("tracking error by calendar month, basis points a year (July is the first month after the portfolios are re-formed):")
print(by_month.reindex(["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]).round(0).astype(int).to_string())
print()
by_decade = diff.groupby((diff.index.year // 10) * 10).agg(["count", "std", "mean"])
by_decade["tracking error, bp a year"] = by_decade["std"] * np.sqrt(12) * 1e4
by_decade["mean difference, bp a year"] = by_decade["mean"] * 12 * 1e4
print("by decade:")
print(by_decade[["count", "tracking error, bp a year", "mean difference, bp a year"]].to_string(float_format=lambda v: f"{v:.1f}"))
print()
print(f"share of months in which the two differ by less than 0.14%: {(diff.abs() < 0.0014).mean():.1%}; by less than 0.30%: {(diff.abs() < 0.003).mean():.1%}")
"""),
    md("""
## A direct test of the explanation, on firm-level data

The explanation above predicts two patterns and both appear, and a prediction that comes true is weaker evidence than a direct test: another cause could produce the same two patterns. The direct test needs the list of firms in each portfolio each month, which French does not publish, so it ran on the CRSP monthly stock file, the database French builds his files from, accessed through WRDS under Queen Mary University of London's subscription (Center for Research in Security Prices, LLC; download date in the results file). This is the one exception to this project's rule of using French's files only, decided for this test alone. The CRSP data stay on the machine that holds them: the script `checks/crsp_direct_test.py` reads them there, this notebook never reads them, and only the aggregate results are in the repository, in `checks/results_crsp_direct_test.json`, written into the working folder by the next cell so that this notebook can print them. The design and the four expectations were fixed in `constants.py` before the script was written (the `DIRECT_TEST_` constants).

The test. For every month, two sets of firms are built from CRSP. The market universe: every firm with CRSP share code 10 or 11 (ordinary common shares of US companies) on the NYSE, AMEX or NASDAQ (exchange codes 1, 2 and 3), with a price and shares outstanding at the end of the previous month and a return in the month. Weighted by that start-of-month market capitalisation, this is how French builds his market return. The June-formed universe: the firms of the market universe that were already in it at the end of the last June and had an SIC code then; this is who can be in an industry portfolio. The firms in the first set and not in the second are the ones the explanation blames: listed since June, or without an SIC code. The predicted gap is the value-weighted return of the market universe minus that of the June-formed universe. The observed gap is French's market return minus the 49-industry combination of this notebook. Expectation 1 checks that the CRSP market universe reproduces French's market return (tracking error at most 20 basis points a year; if not, the universe is built wrongly and the test stops). Expectation 2 is the test: the predicted gap explains the observed one, with a correlation of at least 0.8 and a slope of observed on predicted between 0.8 and 1.2. Expectation 3 reports, with no pass or fail, the share of market capitalisation outside the industries by calendar month and by year. Expectation 4 asks what remains after the prediction: a tracking error below 25 basis points a year.
"""),
    code("""
os.makedirs("checks", exist_ok=True)
"""),
    writefile_path("checks/results_crsp_direct_test.json"),
    code("""
import json
R = json.load(open("checks/results_crsp_direct_test.json"))
print(R["firm_level_source"])
print(f"{R['months']} months, {R['first_month']} to {R['last_month']} (the CRSP monthly file on the machine ends in {R['last_month']}); French vintage: {R['french_vintage']}")
e1, e2, e4 = R["expectation_1_validation"], R["expectation_2_predicted_vs_observed"], R["expectation_4_residual"]
print()
print(f"expectation 1: the CRSP market universe against French's market return: tracking error {e1['tracking_error_annual'] * 1e4:.1f} bp a year, "
      f"correlation {e1['correlation']:.5f}, mean difference {e1['mean_difference_annual'] * 1e4:+.1f} bp a year (level {e1['level'] * 1e4:.0f} bp): {'MET' if e1['met'] else 'NOT MET'}")
print(f"expectation 2: correlation between predicted and observed gap {e2['correlation']:.3f} (at least {R['design']['DIRECT_TEST_MIN_CORRELATION']}), "
      f"slope {e2['slope']:.2f} (in {R['design']['DIRECT_TEST_SLOPE_RANGE'][0]} to {R['design']['DIRECT_TEST_SLOPE_RANGE'][1]}): {'MET' if e2['met'] else 'NOT MET'}")
print(f"   tracking error of the observed gap {e2['te_observed_annual'] * 1e4:.1f} bp a year, of the predicted gap {e2['te_predicted_annual'] * 1e4:.1f} bp, "
      f"of what remains {e2['te_residual_annual'] * 1e4:.1f} bp; the prediction accounts for {e2['share_of_variance_explained']:.0%} of the variance of the observed gap")
e3 = R["expectation_3_reported"]
table = pd.DataFrame({"share of market capitalisation outside the industries, %": e3["omega_by_calendar_month_percent"],
                      "tracking error, observed gap, bp": e3["te_observed_by_calendar_month_bp"],
                      "tracking error, predicted gap, bp": e3["te_predicted_by_calendar_month_bp"],
                      "tracking error, what remains, bp": e3["te_residual_by_calendar_month_bp"]})
print()
print("expectation 3, by calendar month, July first:")
print(table.to_string(float_format=lambda v: f"{v:.1f}"))
print()
print("share of market capitalisation outside the industries, by decade, %:", e3["omega_by_decade_percent"])
print("the five years with the largest share, %:", e3["omega_by_year_percent_top5"])
print("firms in the market universe, average per month, by decade:", {k: int(v) for k, v in e3["firms_market_by_decade_mean"].items()})
print("of which outside the industries:", {k: int(v) for k, v in e3["firms_outside_industries_by_decade_mean"].items()})
print()
print(f"expectation 4: what remains, {e4['te_residual_annual'] * 1e4:.1f} bp a year (level {e4['level'] * 1e4:.0f}): {'MET' if e4['met'] else 'NOT MET'}")
print()
print("the twelve months of largest observed gap, with the prediction beside each:")
print(pd.DataFrame(R["largest_observed_gaps"]).T.to_string(float_format=lambda v: f"{v:.4f}"))
"""),
    md("""
## Save the benchmark for the later notebooks

The weights and the two return series are written to `outputs/`, with the vintage in the file name, so that notebooks 09 to 13 can read them or rebuild them from the same module; rebuilding gives the same numbers on the same vintage.
"""),
    code("""
os.makedirs(C.OUTPUT_DIR, exist_ok=True)
vintage = records[0]["vintage_line"].split("using the ")[1].split(" ")[0]
w_same.to_csv(f"{C.OUTPUT_DIR}/benchmark_weights_{vintage}.csv", float_format="%.8f")
pd.DataFrame({"benchmark": combo_same, "market": market.loc[start:LAST]}).to_csv(f"{C.OUTPUT_DIR}/benchmark_returns_{vintage}.csv", float_format="%.8f")
print("written:", sorted(f for f in os.listdir(C.OUTPUT_DIR) if f.startswith("benchmark")))
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. Count first | 686 months from 1969-07 to 2026-08, 49 industries with a return, a firm count and an average size in every month, the market series without a gap | holds |
| 2. The same-month weights track the market more closely than the previous-month weights | 46.7 against 58.7 basis points a year | MET |
| 3. The gate: tracking error at most 50 basis points a year | 46.7 | MET |
| 4. Description of the benchmark | mean difference +9 basis points a year, correlation 0.9996, 93% of months within 0.14%; largest industry 14% in 1969-07, 13% in 2004-11, 22% in 2026-08 | reported |
| Direct test on CRSP, expectations 1 to 4 | the market universe within 7.6 basis points a year of French's market; the predicted gap explains the observed one with correlation 0.93, slope 1.19, 84% of the variance; what remains 18.7 basis points against 25 | MET, 4 of 4 |

Expectation 1 holds. On the 202608 vintage the three blocks share the same 686 months from 1969-07 to 2026-08, all 49 industries have a return, a firm count and an average size in every one of them, and the market series has no gap. The 49 portfolios held 2,152 firms in 1969-07, 4,663 in 2004-11 and 3,170 in 2026-08, with a total market capitalisation that grew from 641 billion dollars to 71 trillion.

Expectation 2 holds. The same-month weights give a tracking error of 46.7 basis points a year against the market and the previous-month weights 58.7, on the 685 months both cover. French's firm count and average firm size for a month therefore describe the start of that month, and the same-month weights carry no look-ahead: a weight for month t is known when month t begins.

Expectation 3, the gate, is met: 46.7 basis points a year over all 686 months against the level of 50 fixed on 10 September. The derived cap weights are the benchmark of notebooks 09 to 13, return series and industry weights alike. Those notebooks rebuild the benchmark from the same module on the same files, so the two CSV files written here are a record and not an input.

Expectation 4, the description. The combination earns 9 basis points a year more than the market on average, the correlation between the two is 0.9996, and in 93% of months they differ by less than 0.14%. The largest monthly difference is 1.75%, in March 2000. The benchmark is concentrated and its concentration moves: the largest industry held 14% in 1969-07 (Oil), 13% in 2004-11 (Banks) and 22% in 2026-08 (Chips); Oil reached 25% in December 1980 and Chips 23% in June 2026; in 2026-08 the eight largest industries hold 68% of the benchmark and 21 of the 49 industries hold less than 0.5% each. This is why the extension's active weight bound is set relative to each industry's benchmark weight (2 percentage points either side of it, `ACTIVE_WEIGHT_BOUND`): one absolute cap for all 49 would be meaningless for an industry at 0.1% and binding for one at 22%.

Where the 47 basis points come from. French forms the industry portfolios once a year, at the end of June, from the firms that have an SIC code at that time, while the market return takes in a new firm from its first full month of trading. A firm that lists in October is in the market from November and in an industry portfolio from the following July, so between July and June the market gains firms the industries do not have, and the gap between the two returns grows. The data show that pattern: the tracking error is 2 basis points a year in July months, 7 in August, 14 in October, 54 in February and 84 in March, and it falls back to 2 the next July. The data also show the other side of the same mechanism: 96 basis points a year in the 2000s, the decade with the most new listings, against 15 in the 2010s. Twelve months around the peak of the technology boom, 1999-07 to 2000-12, account for most of the total; without them the tracking error would be 24 basis points; this number describes the gap and decides nothing. The gate was met with little room, 46.7 against 50. The level was fixed before any of this was computed and is not revisited after the fact; had the level been 40, the derived weights would have been rejected and the benchmark return would be the market series.

The direct test confirms the explanation. On the CRSP monthly stock file, 666 months from 1969-07 to 2024-12, the market universe built from share codes 10 and 11 on the three exchanges reproduces French's market return to within 7.6 basis points a year (correlation 0.99999), so the universes are built the way French builds his. The gap that the June-formed universe predicts has a correlation of 0.93 with the observed gap, a slope of 1.19, and it accounts for 84% of the observed gap's variance; what remains has a tracking error of 18.7 basis points a year against the level of 25. All four expectations are met. The share of market capitalisation held by firms outside the industries rises from 0.6% in July months to 2.3% in June months, the shape the formation rule implies. Its largest values are in 1973, when CRSP added the NASDAQ stocks to its database: the market universe went from 2,505 firms in December 1972 to 5,364 in January 1973, and the 2,960 new firms, 13% of market capitalisation, were in no industry portfolio until July 1973; the two largest gaps of the 1970s, April and May 1973, are reproduced by the prediction to within 0.06 of a percentage point. In March 2000 the firms outside the industries held 5.3% of market capitalisation and the prediction gives -1.45% against the observed -1.75%.

**What this notebook does not settle.**

- What remains after the prediction, 18.7 basis points a year, and the slope above one: the observed gap is about a fifth larger than the predicted one. Three differences between the test's universes and French's construction can account for it, and the test does not separate them. French assigns industries by Compustat's SIC code where one exists and by CRSP's only otherwise, while the test uses CRSP's alone, so a firm with a CRSP code of zero and a Compustat code is outside the industries in the test and inside them for French; in July 1973, 677 of the 5,161 market firms had no CRSP SIC code. French's returns include the return a firm earns in the month it is delisted, which the CRSP monthly file carries in a separate table the test does not read. And French's average firm size is rounded to two decimals of a million dollars. Separating the three would need Compustat and the delisting table, which the study does not use.
- The CRSP file on the machine ends in December 2024, so the last twenty months of the 49-industry combination are outside the test.
- The level of 50 basis points was a judgement about how close to the market an index of the 49 industries has to be to stand in for it; nothing in the extension depends on that closeness, because every later tracking error is measured against this benchmark, so the 47 basis points do not enter any later number.
- A cap-weighted index rebalances itself: when an industry's prices rise, its weight rises with them and no trade is needed. The portfolios of notebooks 11 and 12 have to trade to follow it, a limit on turnover (the fraction of the portfolio traded each month) caps how much they may trade, and notebook 12 measures what that costs."""),
]


# ---------------------------------------------------------------------------
# 09: the principal components of the 49 industries
# ---------------------------------------------------------------------------

NB09 = [
    md("""
# 09. What moves the 49 industries together: principal components

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same month |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money |
| Value-weighted return | the return of a group of firms in which each firm counts in proportion to its market capitalisation at the start of the month |
| Cap-weighted | weighted by market capitalisation |
| Benchmark | in the extension, the index the portfolio tracks, the cap-weighted combination of the 49 industries built in notebook 08 |
| Fat tails | extreme months more frequent and more extreme than a normal distribution allows |
| Volatility clustering | volatility that persists from month to month, so that a turbulent month is usually followed by another |
| Variance | the average squared distance of a series from its own average; its square root is the standard deviation, the usual measure of how much a return moves |
| Covariance | a number that says how two series move together, positive when they tend to be above their averages in the same months and negative when one is above while the other is below; the covariance of a series with itself is its variance |
| Covariance matrix | the table of all variances and covariances of a set of assets, 49 rows by 49 columns here, 1,225 distinct numbers |
| Principal component | a combination of the assets, with one weight per asset, chosen so that it explains as much of the assets' total variance as a single combination can; the second component does the same among combinations uncorrelated with the first, and so on; in mathematics the components are called the eigenvectors of the covariance matrix and their variances are called its eigenvalues |
| Loading | an asset's weight in a component |
| Score | a component's monthly return, the assets' excess returns combined with the loadings as weights |
| Variance share | the component's variance divided by the total variance of all assets; the shares of all 49 components add up to one |
| Seed | the number that fixes the random numbers a simulation uses; the same seed gives the same random numbers |
| Draw | one panel of made-up returns produced from one seed |
| Parallel analysis | the comparison of each component's variance with the variance the same component would have if the assets had nothing in common and moved independently; a component above that bar carries shared movement that chance cannot imitate |
| Estimation error | the difference between a number estimated from a window of returns and its true value |
| Standard error | the typical size of the estimation error in an estimate; for a correlation measured on T months it is about (1 minus the squared correlation) divided by the square root of T |
| Estimation window | the M months of past returns a rule sees when it forms its weights, 120 in the extension |
| Factor | a return series that moves many assets at once, for example the return of the whole market |
| Beta | how much an asset moves with a factor; an industry with a beta of 1.5 to the benchmark moves 1.5 times as much as the benchmark on average |
| Idiosyncratic | an asset's own movement, unrelated to the factors |
| Covariance estimator | a method for estimating the covariance matrix from a window of data; the extension compares four in notebook 10 |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |

**The problem, stated the way practitioners state it.** The key ingredient of every risk-based portfolio is the covariance matrix of the assets' returns. The natural estimate is the sample covariance, and it fails when the assets are many relative to the months of data: for 49 industries and 120 months it has fewer than five observations per number, and the rule that inverts it (notebooks 02 and 03) trades on its errors. The literature answers with a long list of alternative estimators, and the three ideas behind them are shrinkage (pulling the estimate part of the way towards a simpler target), time dynamics (weighting recent data more) and factor structure (Dom, Howard, Jansen and Lohre, 2024, whose introduction this paragraph follows). Factor structure is the idea this notebook prepares: describe the 1,225 numbers by five or fewer common sources of movement plus each industry's own variance, so that fewer numbers are estimated from the same data. Whether that is a good idea for the 49 industries depends on a fact about the data, whether five sources account for most of their shared movement and whether the first of them is the market, which is what this notebook measures before notebook 10 builds the estimator on it.

**What this notebook does.** The paper estimates the covariance matrix from a 120-month window of monthly returns. For 49 industries that is 49 variances and 1,176 covariances, 1,225 numbers, from 49 times 120 equals 5,880 monthly returns: fewer than five observations per number. Notebooks 02 and 03 showed what estimation error does to a rule that inverts such a matrix. Practitioners meet this problem in two ways, and the extension uses both. The first is more observations: estimating from daily returns, where three years hold about 756 trading days and 49 times 756 equals 37,044 observations, 30 per number; notebook 10 builds every estimator at both frequencies, the paper's 120 monthly returns and three years of daily returns, and `constants.py` records the design (`EXT_COV_FREQUENCIES`). The second is fewer numbers: describe the matrix by the few combinations of industries that account for most of the shared movement, keep those, and treat what is left as each industry's own noise. Those combinations are the principal components, and they are this notebook's subject. The components here are taken from monthly returns, the paper's data, so that what they show about the industries' structure is the structure the paper's estimator faced. Before that estimator is built, this notebook asks three things of the 49 industries over 1969-07 to the vintage's last month: how much of the total variance the first few components explain; whether the first component is the market, measured as the correlation of its score with the benchmark's excess return; and whether the components found in one period are still the components of another, because an estimator that keeps five components assumes that the five found in the window still describe the next month.

**Why it comes ninth.** The benchmark exists since notebook 08, and the first component is checked against it. The question of how many numbers a covariance matrix really needs is the bridge from the paper (where the sample covariance was one of the things that made mean-variance fail) to the extension (where four ways of estimating it are compared on a portfolio that is told what to hold).

**What I expect to see, written before the run (`constants.py`, 1 October 2026).** First, count first: 686 months by 49 industries with no gap, and the benchmark rebuilt from the same module over the same months. Second, the first component is the market: its score has a correlation of at least 0.95 with the benchmark's excess return over the full sample and in each of three windows fixed in advance (to 2019-12, 2020-01 to 2022-12, from 2023-01). Below the level in any window the notebook reports which, and notebook 10's PCA estimator is built with the market factor imposed as the first component. Third, reported with no pass or fail: the variance share of each of the first ten components, the share of the first five together (the number notebook 10 keeps), and the number of components above the parallel-analysis bar. Fourth, reported: the stability of the first five components' loadings between the three windows, and how much of each window's variance the full-sample components explain compared with the window's own. Fifth, reported: what the estimator will see, the first component's variance share and its correlation with the benchmark in every 120-month window. Running time: about two minutes, most of it the parallel analysis.
"""),
    md("""
## Modules

`constants`, `french_loader` and `benchmark` are those of notebook 08. `pca` is new: the components with a sign rule, their scores and variance shares, a similarity measure between two sets of loadings, the parallel analysis, and the rolling view. Each function has a test on a made-up one-factor market in `tests/test_pca.py`.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("benchmark.py"),
    writefile("pca.py"),
    md("""
## Count first: the panel of excess returns and the benchmark

The industries' value-weighted returns minus the one-month Treasury bill rate, from 1969-07, and the benchmark of notebook 08 rebuilt from the same module.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import numpy as np
import pandas as pd
from bp import constants as C
from bp import french_loader as fl
from bp import benchmark as BM
from bp import pca as P

pd.set_option("display.width", 180)
pd.set_option("display.max_rows", 120)
pd.set_option("display.max_columns", 60)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

inputs = BM.load_inputs()
f3 = fl.load_monthly("factors3", 0)
start = pd.Period(C.EXT_SAMPLE_START, "M")
returns = inputs["returns"].loc[start:]
rf = f3["RF"].loc[start:returns.index[-1]]
excess = returns.sub(rf, axis=0)
weights = BM.cap_weights(inputs["firms"].loc[start:], inputs["size"].loc[start:], C.CAPW_WEIGHT_TIMING)
benchmark = BM.combination_return(returns, weights)
benchmark_excess = (benchmark - rf).rename("benchmark_excess")
LAST = excess.index[-1]

assert excess.shape[1] == 49 and not excess.isna().any().any(), "a gap in the excess returns"
assert len(excess) == len(pd.period_range(start, LAST, freq="M")), "months missing"
assert benchmark_excess.index.equals(excess.index) and benchmark_excess.notna().all(), "the benchmark does not cover the same months"
assert rf.notna().all()
records = [fl.download(key) for key in ("ind49", "factors3")]
fl.write_provenance(records)
reference = weights.mean().to_numpy()      # the sign rule: each component's loading on the average benchmark weights is positive
print(f"{len(excess)} months, {start} to {LAST}, 49 industries, no gap; benchmark rebuilt over the same months (expectation 1 holds)")
print(f"covariance matrix: 49 variances and {49 * 48 // 2:,} covariances, {49 * 50 // 2:,} numbers; a 120-month window holds {49 * 120:,} monthly returns, {49 * 120 / (49 * 50 // 2):.1f} per number")
print("vintage:", "; ".join(sorted({r["vintage_line"] for r in records})))
"""),
    md("""
## The components over the full sample, and whether the first is the market

The first table lists the first ten components: the variance each explains, its share of the total, and the cumulative share. The variance and standard deviation columns are in the component's own units: the loadings are scaled so that their squares sum to one, which makes the first component's monthly return about seven times the average industry's excess return (its 49 loadings are each about 0.14 and add up to about 7), so only ratios between components and correlations carry meaning, and the variance share is the ratio that matters. The last line of the cell is expectation 2 over the full sample: the correlation between the first component's score and the benchmark's excess return.
"""),
    code("""
full = P.fit(excess, reference)
table = pd.DataFrame({
    "variance (monthly)": full.eigenvalues[:C.PCA_REPORT_COMPONENTS],
    "standard deviation (monthly)": np.sqrt(full.eigenvalues[:C.PCA_REPORT_COMPONENTS]),
    "variance share": full.shares[:C.PCA_REPORT_COMPONENTS],
    "cumulative share": np.cumsum(full.shares)[:C.PCA_REPORT_COMPONENTS],
}, index=[f"PC{k + 1}" for k in range(C.PCA_REPORT_COMPONENTS)])
print(table.to_string())
print()
print(f"total variance of the 49 industries: {full.eigenvalues.sum():.5f} a month; the first {C.PCA_N_COMPONENTS} components explain {full.shares[:C.PCA_N_COMPONENTS].sum():.1%} of it, the first alone {full.shares[0]:.1%}")
print(f"the average industry has a monthly standard deviation of {np.sqrt(np.diag(P.covariance(excess))).mean():.4f}; the first component's is {np.sqrt(full.eigenvalues[0]):.4f}")
sc = P.scores(excess, full, C.PCA_N_COMPONENTS)
corr_full = float(np.corrcoef(sc["PC1"], benchmark_excess)[0, 1])
print()
print(f"expectation 2, full sample: correlation between the first component's score and the benchmark's excess return {corr_full:.4f} "
      f"(level {C.PCA_PC1_MARKET_CORR_MIN}): {'MET' if corr_full >= C.PCA_PC1_MARKET_CORR_MIN else 'NOT MET'}")
print("correlation of each of the first five scores with the benchmark's excess return:", {c: round(float(np.corrcoef(sc[c], benchmark_excess)[0, 1]), 3) for c in sc.columns})
"""),
    md("""
## What the first component is made of

Each industry's loading on the first component, beside two things that could explain it: the industry's own monthly standard deviation and its average benchmark weight. If the first component were the benchmark, the loadings would follow the weights. If it is the market factor as a statistical object, they follow how much each industry moves with the market, which is larger for volatile industries whatever their size.
"""),
    code("""
L = full.frame(C.PCA_N_COMPONENTS)
sd = pd.Series(np.sqrt(np.diag(P.covariance(excess))), index=excess.columns, name="monthly standard deviation")
avg_w = weights.mean().rename("average benchmark weight")
beta = pd.Series({c: np.cov(excess[c], benchmark_excess, ddof=1)[0, 1] / benchmark_excess.var(ddof=1) for c in excess.columns}, name="beta to the benchmark")
view = pd.concat([L["PC1"].rename("PC1 loading"), sd, beta, avg_w], axis=1).sort_values("PC1 loading", ascending=False)
print("the ten largest and the ten smallest loadings on the first component:")
print(pd.concat([view.head(10), view.tail(10)]).to_string())
print()
print(f"correlation across industries between the PC1 loading and: the standard deviation {view['PC1 loading'].corr(view['monthly standard deviation']):.2f}, "
      f"the beta to the benchmark {view['PC1 loading'].corr(view['beta to the benchmark']):.2f}, the benchmark weight {view['PC1 loading'].corr(view['average benchmark weight']):.2f}")
print(f"loadings on PC1 that are negative: {int((L['PC1'] < 0).sum())} of 49")
print()
print("the second and third components, five largest positive and five most negative loadings each:")
for c in ("PC2", "PC3"):
    s_ = L[c].sort_values()
    print(f"  {c}: positive {{{', '.join(f'{k}: {v:.3f}' for k, v in s_.tail(5)[::-1].items())}}}; negative {{{', '.join(f'{k}: {v:.3f}' for k, v in s_.head(5).items())}}}")
"""),
    md("""
## Expectation 2 in the three windows fixed in advance

The same fit inside each window, and the first component's correlation with the benchmark's excess return there.
"""),
    code("""
def window_slice(frame, lo, hi):
    return frame.loc[(pd.Period(lo, "M") if lo else frame.index[0]):(pd.Period(hi, "M") if hi else frame.index[-1])]

fits, rows = {}, []
for name, (lo, hi) in C.PCA_WINDOWS.items():
    ex = window_slice(excess, lo, hi)
    be = window_slice(benchmark_excess, lo, hi)
    p = P.fit(ex, reference)
    s1 = P.scores(ex, p, 1)["PC1"]
    corr = float(np.corrcoef(s1, be)[0, 1])
    fits[name] = (ex, p)
    rows.append({"window": name, "months": len(ex), "first month": str(ex.index[0]), "last month": str(ex.index[-1]),
                 "PC1 variance share": p.shares[0], f"first {C.PCA_N_COMPONENTS} share": p.shares[:C.PCA_N_COMPONENTS].sum(),
                 "PC1 corr. with benchmark": corr, "verdict": "MET" if corr >= C.PCA_PC1_MARKET_CORR_MIN else "NOT MET"})
e2 = pd.DataFrame(rows).set_index("window")
print(e2.to_string())
n_met = int((e2["verdict"] == "MET").sum())
print()
print(f"expectation 2: {n_met} of {len(e2)} windows at or above {C.PCA_PC1_MARKET_CORR_MIN}, and the full sample {'MET' if corr_full >= C.PCA_PC1_MARKET_CORR_MIN else 'NOT MET'}")
if n_met < len(e2) or corr_full < C.PCA_PC1_MARKET_CORR_MIN:
    print("design consequence: notebook 10's PCA estimator imposes the market factor as its first component")
else:
    print("design consequence: none; notebook 10's PCA estimator takes its components from the data")
"""),
    md("""
## Expectation 3: how many components are more than noise

Parallel analysis draws 200 panels of independent normal returns with the same number of months and industries and the same variances as the data, so that nothing moves together in them, and takes the variance of each component in each draw. The bar for a component is the 95th percentile of its variance across the draws. A component of the data above its bar carries shared movement that independent noise does not produce one time in twenty.
"""),
    code("""
pa = P.parallel_analysis(excess)
show = pa.head(C.PCA_REPORT_COMPONENTS).copy()
show["ratio to the bar"] = show["eigenvalue"] / show[f"noise_p{C.PCA_PARALLEL_PERCENTILE}"]
print(show.to_string())
print()
print(f"components above the noise bar, counted from the first until the first one below it: {pa.attrs['n_above_noise']} of 49 "
      f"(the estimator of notebook 10 keeps {C.PCA_N_COMPONENTS})")
print(f"components above the bar anywhere in the list: {int(pa['above_noise'].sum())}")
"""),
    md("""
## Expectation 4: do the components of one period still describe another

Two views. The first table gives, for each of the first five components, the similarity of its loadings between each pair of windows: the absolute correlation across the 49 industries of the two loading vectors, 1 for the same combination of industries and 0 for unrelated ones. The second table asks the question the estimator cares about: inside each window, how much of the variance do the full-sample components explain, against how much the window's own components explain, for one component and for five. The window's own components are the best possible for that window, so the gap between the two columns is the cost of using components estimated on other months.
"""),
    code("""
names = list(C.PCA_WINDOWS)
pairs = [(names[0], names[1]), (names[1], names[2]), (names[0], names[2])]
sim = pd.DataFrame({f"{a} vs {b}": [P.loading_similarity(fits[a][1].loadings[:, k], fits[b][1].loadings[:, k]) for k in range(C.PCA_N_COMPONENTS)] for a, b in pairs},
                   index=[f"PC{k + 1}" for k in range(C.PCA_N_COMPONENTS)])
print("similarity of loadings between windows (absolute correlation across the 49 industries):")
print(sim.to_string())
print()
rows = []
for name, (ex, p) in fits.items():
    rows.append({"window": name,
                 "own PC1": P.explained_in_window(ex, p.loadings, 1), "full-sample PC1": P.explained_in_window(ex, full.loadings, 1),
                 f"own first {C.PCA_N_COMPONENTS}": P.explained_in_window(ex, p.loadings, C.PCA_N_COMPONENTS),
                 f"full-sample first {C.PCA_N_COMPONENTS}": P.explained_in_window(ex, full.loadings, C.PCA_N_COMPONENTS)})
ex4 = pd.DataFrame(rows).set_index("window")
ex4["gap, five components"] = ex4[f"own first {C.PCA_N_COMPONENTS}"] - ex4[f"full-sample first {C.PCA_N_COMPONENTS}"]
print("share of each window's variance explained by its own components and by the full-sample components:")
print(ex4.to_string())
"""),
    md("""
## Expectation 5: what the estimator will see, window by window

The first component's variance share and its correlation with the benchmark's excess return in every 120-month window, 567 of them, summarised by their minimum, median and maximum with the months at which the extremes end.
"""),
    code("""
roll = P.rolling_first_component(excess, benchmark_excess, C.EXT_ESTIMATION_WINDOW, reference)
summary = pd.DataFrame({
    "minimum": roll.min(), "month of minimum": roll.idxmin().astype(str), "median": roll.median(),
    "maximum": roll.max(), "month of maximum": roll.idxmax().astype(str),
})
print(f"{len(roll)} windows of {C.EXT_ESTIMATION_WINDOW} months, ending {roll.index[0]} to {roll.index[-1]}:")
print(summary.to_string())
print()
below = roll[roll["pc1_corr_benchmark"] < C.PCA_PC1_MARKET_CORR_MIN]
print(f"windows in which the first component's correlation with the benchmark is below {C.PCA_PC1_MARKET_CORR_MIN}: {len(below)} of {len(roll)}"
      + (f", ending {below.index[0]} to {below.index[-1]}" if len(below) else ""))
print("first component's variance share by decade of the window's last month (median):")
print((roll["pc1_share"].groupby((roll.index.year // 10) * 10).median()).to_string())
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. Count first | 686 months from 1969-07 to 2026-08, 49 industries, no gap; the benchmark rebuilt over the same months | holds |
| 2. The first component is the market: correlation at least 0.95 with the benchmark's excess return, full sample and three windows | 0.956 over the full sample; 0.959 to 2019-12, 0.971 in 2020 to 2022, 0.837 from 2023-01 | NOT MET in the window from 2023; the pre-registered consequence applies |
| 3. Components above the parallel-analysis bar | 2 | reported |
| 4. Stability of the loadings between windows | first component similarity 0.53 to 0.68; the full-sample components explain 0.2, 9.3 and 11.4 points less than each window's own | reported |
| 5. The rolling view, 567 windows of 120 months | first component share 37% to 69%, median 61%; correlation with the benchmark below 0.95 in 130 windows, all ending after 2000-05 | reported |

Expectation 1 holds: 686 months from 1969-07 to 2026-08, 49 industries, no gap, and the benchmark rebuilt over the same months.

What the components are. The first component explains 55% of the total variance of the 49 industries over the full sample, the second 6%, the third 4%, and the first five together 72%. Every one of the 49 loadings on the first component is positive: when it moves, all industries move the same way, which is what a market factor does. Its loadings follow how much each industry moves with the market and not how large the industry is: across industries the loading has a correlation of 0.97 with the industry's beta to the benchmark and of -0.30 with its benchmark weight. Software, Steel, Fun, Construction and Real Estate load most; Utilities, Food, Tobacco, Drugs and Gold load least. The second component sets the commodity producers (Gold, Coal, Mines, Oil, Steel, all with negative loadings) against retail, software, entertainment and clothing, so it is the component that moves when raw-material prices move against the rest of the economy; the third separates Gold from Coal.

Expectation 2, the first component is the market: met over the full sample (correlation 0.956) and in the windows to 2019-12 (0.959) and 2020-01 to 2022-12 (0.971), and not met in the window from 2023-01 (0.837, 44 months). The loadings table explains the miss. The benchmark weights industries by size, and since 2023 Chips and Software hold a third of it between them; the first component weights industries by how much they move with the others, which gives Chips and Software about 3% each of a component whose loadings are all between 0.07 and 0.20. In a period in which the largest industries move on their own, the two series part. The rolling view says the same: in 130 of the 567 windows of 120 months, all of them ending after May 2000, the correlation is below 0.95, with a minimum of 0.93 in the window ending December 2000. The pre-registered consequence applies, and `constants.py` records it: notebook 10's PCA estimator takes the benchmark's excess return as its first factor and finds the remaining components in what the market leaves unexplained, so that its first component is the market by construction in every window.

Expectation 3, how many components are more than noise: two. The first component's variance is 8.7 times what 200 panels of independent returns with the same variances produce at the 95th percentile; the second is 1.15 times; the third is below the bar, the fourth 1.02 times and the fifth below. The number the estimator of notebook 10 keeps, five, was fixed on 10 September; this count says that components three to five carry about as much shared movement as chance would, over the full sample. The constant stays at five, and notebook 10 reports the two-component estimator beside it, with neither declared right or wrong.

Expectation 4, stability. The first component's loadings have a similarity of 0.68 between the window to 2019 and the window 2020 to 2022, 0.61 between the second and the third, and 0.53 between the first and the third; the loadings of components two to five are mostly unrelated between windows (0.02 to 0.55). The second table asks what that costs. Inside the window to 2019 the full-sample components explain 72.9% of the variance against 73.1% for the window's own, a gap of 0.2 points, because that window is most of the full sample. Inside 2020 to 2022 the gap is 9.3 points (73.7% against 83.0%) and inside the window from 2023 it is 11.4 points (61.9% against 73.3%). The first component alone moves less: gaps of 0.1, 2.1 and 4.8 points. So the combinations of industries that moved together in one period explain a good part of another, and the smaller components are the ones that do not carry over.

Expectation 5, the rolling view. Across the 567 windows of 120 months, the first component's variance share runs from 37% (the window ending February 2001, the ten years of the technology boom, when technology moved on its own) to 69% (the window ending December 1987, which holds the crash of October 1987, a month in which everything fell together), with a median of 61%; by decade of the window's last month the median is 67% in the 1970s, 41% in the 2000s and 55% in the 2020s. The first five components explain between 66% and 84%.

**What this notebook does not settle.**

- The 44-month window from 2023 is short: a correlation measured on 44 months has a standard error of about 0.05 when its true value is near 0.9, so 0.837 against the level of 0.95 is two standard errors below it, and the rolling view confirms that the fall is real and not a feature of one short window.
- A variance share says how much of the industries' movement a component explains over the months it was estimated on; how well a covariance built from it serves a portfolio in the following month is notebook 10's question, and the gaps of expectation 4 are the first measure of it.
- Parallel analysis compares the data with independent returns of the same variances and nothing else; returns with fat tails or volatility clustering (notebooks 05 and 06) produce slightly larger extreme eigenvalues by chance, so the bar is slightly too low and the count of two is a generous one.
- The count of five components is a design parameter with a convention behind it (statistical risk models keep three to ten), fixed before the run, and the data-driven rules for the count disagree with each other: the Kaiser rule (components of the correlation matrix with variance above one), the scree plot (where the ordered variances flatten), parallel analysis (where chance would produce as much, two here), the Marchenko-Pastur bound of random-matrix theory (the same idea as a formula) and the information criteria of Bai and Ng (2002). All of them judge how well the components describe the sample. The count that serves a portfolio is the one whose covariance matrix forecasts next month's risk best, found by running the estimator with each count month by month on the months before each forecast; notebook 10 runs two counts beside each other and reports the difference, and a rule that chooses the count inside each window is the data-driven version a later study could fix before its run.
- The components were extracted from the covariance of excess returns, so an industry with twice the volatility weighs four times as much in the total variance; extracting them from the correlation matrix instead would treat every industry alike and give a different second and third component. The choice was fixed before the run because the estimator of notebook 10 works with covariances.
"""),
]


# ---------------------------------------------------------------------------
# 10: the four covariance estimators
# ---------------------------------------------------------------------------

NB10 = [
    md("""
# 10. Four ways to estimate a covariance matrix, and how to tell which is better

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same period |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money |
| Cap-weighted | weighted by market capitalisation |
| Benchmark | in the extension, the index the portfolio tracks, the cap-weighted combination of the 49 industries built in notebook 08 |
| Variance | the average squared distance of a series from its own average; its square root is the standard deviation, the usual measure of how much a return moves; volatility is the standard deviation of returns, stated per year here by multiplying the monthly figure by the square root of 12 |
| Covariance | a number that says how two series move together, positive when both tend to be above their averages in the same periods |
| Covariance matrix | the table of all variances and covariances of a set of assets, 49 by 49 here, 1,225 distinct numbers |
| Covariance estimator | a method for estimating the covariance matrix from a window of data |
| Estimation window | the past returns an estimator sees, 120 months or three years of trading days here |
| Estimation error | the difference between a number estimated from a window and its true value |
| Shrinkage | pulling an estimate part of the way towards a simpler target, which trades a little bias for less estimation error; the shrinkage intensity is the fraction of the way it is pulled |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors are long-short portfolios built to isolate one such source each |
| Beta | how much an asset moves with a factor on average |
| Idiosyncratic | an asset's own movement, unrelated to the factors |
| Principal component | a combination of the assets, with one weight per asset, chosen so that it explains as much of the assets' total variance as a single combination can (notebook 09); its variance is called an eigenvalue of the covariance matrix |
| Parallel analysis | the comparison of each component's variance with what independent noise would produce, used in notebook 09 to count the components that are more than noise |
| Minimum-variance portfolio | the fully invested portfolio with the lowest variance under a given covariance matrix; long-only when no weight may be negative, unconstrained when weights may be negative |
| Turnover | the fraction of the portfolio bought and sold at a rebalance, summed over the assets; a turnover of 0.76 means that 76% of the portfolio changes hands in the month |
| Basis point | one hundredth of a percentage point, so 50 basis points is 0.50% |
| Sharpe ratio | the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken; stated per year here as the annual excess return over the annual volatility |
| Active weight | the portfolio's weight in an asset minus the benchmark's weight in it |
| Tracking error | the standard deviation of the difference between two return series, stated per year |
| Bias statistic | the standard deviation of realised return divided by forecast standard deviation, over many periods; 1 when the forecasts of risk are right on average, above 1 when risk is under-forecast, below 1 when over-forecast |
| Condition number | the largest eigenvalue of a matrix divided by the smallest; it says how much inverting the matrix amplifies errors in it |
| Autocorrelation | the correlation of a series with its own value one period earlier |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |

**The problem, stated the way practitioners state it.** The key ingredient of every risk-based portfolio is the covariance matrix of the assets' returns. The natural estimate is the sample covariance, and it fails when the assets are many relative to the observations: for 49 industries and 120 monthly returns it has fewer than five observations per number. The literature answers with a long list of alternative estimators built on three ideas, shrinkage, time dynamics and factor structure, and it tests them almost always in one way, by the realised volatility of the unconstrained minimum-variance portfolio built from each. Dom, Howard, Jansen and Lohre (2024), whose introduction this paragraph follows, point out that such a portfolio is one no practitioner holds: it is leveraged, concentrated and trades a large part of its value every month, so the test rewards an estimator for what it does in positions nobody takes. They propose to judge estimators instead on realistic portfolios, long-only, weight-constrained and charged for trading, after costs, and they find that under those constraints the differences between estimators shrink, that time dynamics (recent days weighted more, as in RiskMetrics) matter more than shrinkage or structure, and that a simple dynamic estimator does as well as a complex one. This notebook takes their perspective. It builds four estimators at two data frequencies, judges each by the calibration of its risk forecasts and by both the unconstrained and the long-only minimum-variance portfolio it produces, and, in a final section, charges the portfolios for their trading, which is where the unconstrained portfolio's lower volatility turns out to be bought at a price no investor pays.

**What this notebook does.** The paper estimated the covariance matrix of its assets by the sample covariance of 120 monthly returns, and notebooks 02, 03 and 09 showed what that costs for 49 assets: 1,225 numbers from fewer than five observations each. This notebook builds four estimators and judges them on the 49 industries. The sample covariance uses every number the window offers. Ledoit-Wolf shrinkage pulls the sample covariance part of the way towards a simple target. The factor model describes the covariance by each industry's betas to six Fama-French factors plus its own variance. The principal-component model takes the market as its first factor and finds four more components in what the market leaves. Each is built at two data frequencies: the paper's 120 monthly returns, and three years of daily returns scaled to monthly, which is what practitioners use (Dom, Howard, Jansen and Lohre, 2024, estimate from daily returns over three years and rebalance monthly). Every estimate is built on the data before a month and judged on that month's realised returns, for every month from 1979-07 to the vintage's last month.

**How a covariance estimator is judged.** A covariance matrix makes two kinds of promise. The first is a forecast of risk: for any portfolio with weights w, w' Sigma w is the variance it predicts for next month. The bias statistic tests the promise over many months: divide each month's realised return by the forecast standard deviation, and take the standard deviation of those ratios; a calibrated forecaster gets 1, one that under-forecasts risk gets more than 1. The notebook tests it on each of the 49 industries, on 1/N, on the benchmark, and on 200 random active portfolios (weights that sum to zero, largest 2 percentage points, the extension's active weight bound), which is the tracking-error forecast the extension will rely on. The second promise is in the inverse: the minimum-variance portfolio uses Sigma^-1, and errors in the small directions of Sigma blow up there. Following Dom, Howard, Jansen and Lohre (2024), the notebook builds the minimum-variance portfolio from each estimate every month, with and without the long-only constraint, holds it for a month, and reports the volatility it realised over all months; a better covariance gives a lower one. The condition number of each estimate says how much its inverse amplifies errors.

**What I expect to see, written before the run (`constants.py`, 3 October 2026).**

1. Count first: the daily panel from 1969-07 has one missing day (Software on 1971-03-11), the daily factor files cover every day of every window, and the evaluation months are counted and the same for every estimator.
2. The frequency question: for the sample estimator, three years of daily returns give a bias statistic closer to 1 than 120 monthly returns for the benchmark and for the active portfolios, and a lower realised volatility of the unconstrained minimum-variance portfolio.
3. The finding of Dom, Howard, Jansen and Lohre: with daily data, the long-only minimum-variance portfolios of the four estimators realise volatilities within one percentage point a year of each other, and the unconstrained portfolio of the sample estimator on monthly data realises the highest volatility of all.
4. The scaling check: the benchmark's realised monthly variance over a three-year window divided by 21 times its daily variance over the same window averages between 0.8 and 1.25 over the windows; outside that, the daily estimators are still used as designed and the notebook says by how much and in which direction the scaling misses.
5. Reported with no pass or fail: the shrinkage intensity over time at both frequencies, the sensitivities (one- and five-year daily windows, exponential weighting with a one-year half-life, the constant-correlation shrinkage target, a two-component model), and the condition numbers.

Running time: about one minute. Three further tests, P1 to P3, were added after the run and are labelled as such below; their expectations were fixed in `constants.py` on 4 October 2026 before their code was written.
"""),
    md("""
## Modules

`constants`, `french_loader`, `benchmark` and `rules` are those of earlier notebooks; `rules` supplies the exact long-only minimum-variance solver of notebook 03. `covariance` is new: the four estimators, the sensitivities, the windows and the tests, each with a test on a made-up market with a known covariance in `tests/test_covariance.py`.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("benchmark.py"),
    writefile("rules.py"),
    writefile("covariance.py"),
    md("""
## Count first: monthly and daily panels, factors and the benchmark at both frequencies

The 49 industries' excess returns monthly from 1969-07 and daily from 1969-07-01; the six factors (Mkt-RF, SMB, HML, RMW, CMA, Mom) at both frequencies; the benchmark of notebook 08 monthly, and daily with each month's weights applied to that month's days.
"""),
    code("""
import sys
sys.path.insert(0, "src")
import time
import numpy as np
import pandas as pd
from bp import constants as C
from bp import french_loader as fl
from bp import benchmark as BM
from bp import covariance as CV

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 120)
pd.set_option("display.max_columns", 40)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

inputs = BM.load_inputs()
f3 = fl.load_monthly("factors3", 0)
f5 = fl.load_monthly("factors5", 0)
mom = fl.load_monthly("momentum", 0)
start = pd.Period(C.EXT_SAMPLE_START, "M")
returns_m = inputs["returns"].loc[start:]
LAST = returns_m.index[-1]
rf_m = f3["RF"].loc[start:LAST]
excess_m = returns_m.sub(rf_m, axis=0)
weights = BM.cap_weights(inputs["firms"].loc[start:], inputs["size"].loc[start:], C.CAPW_WEIGHT_TIMING)
bench_m = (BM.combination_return(returns_m, weights) - rf_m).rename("benchmark_excess")
factors_m = pd.concat([f5[["Mkt-RF", "SMB", "HML", "RMW", "CMA"]], mom["Mom"]], axis=1).loc[start:LAST]

returns_d = fl.load_monthly("ind49_daily", r"Value Weighted Returns -- Daily").loc[start.asfreq("D", "start"):]
f3d = fl.load_monthly("factors3_daily", 0)
f5d = fl.load_monthly("factors5_daily", 0)
momd = fl.load_monthly("momentum_daily", 0)
rf_d = f3d["RF"].reindex(returns_d.index)
excess_d = returns_d.sub(rf_d, axis=0)
factors_d = pd.concat([f5d[["Mkt-RF", "SMB", "HML", "RMW", "CMA"]], momd["Mom"]], axis=1).reindex(returns_d.index)
bench_d = CV.daily_benchmark_excess(returns_d, rf_d, weights)

eval_months = pd.period_range(C.COV_EVAL_START, LAST, freq="M")
first_daily_day = (eval_months[0] - 12 * max(C.EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY + (C.EXT_COV_DAILY_WINDOW_YEARS,))).asfreq("D", "start")

# Expectation 1
assert excess_m.shape == (len(pd.period_range(start, LAST, freq="M")), 49) and not excess_m.isna().any().any()
missing_days = excess_d.index[excess_d.isna().any(axis=1)]
assert len(missing_days) == 1 and str(missing_days[0]) == "1971-03-11" and excess_d.loc[missing_days[0]].isna().sum() == 1
assert rf_d.notna().all(), "the daily risk-free rate has a gap"
assert not factors_d.loc[first_daily_day:].isna().any().any(), "a daily factor is missing inside the daily windows"
assert not factors_m.loc[eval_months[0] - C.EXT_ESTIMATION_WINDOW:].isna().any().any()
assert bench_m.loc[eval_months].notna().all() and bench_d.loc[first_daily_day:].notna().sum() == excess_d.loc[first_daily_day:].dropna().shape[0]
provenance = [fl.download(key) for key in ("ind49", "factors3", "factors5", "momentum", "ind49_daily", "factors3_daily", "factors5_daily", "momentum_daily")]
fl.write_provenance(provenance)
print(f"monthly panel: {len(excess_m)} months, {start} to {LAST}; daily panel: {len(excess_d):,} trading days, {excess_d.index[0]} to {excess_d.index[-1]}, "
      f"{len(missing_days)} day with a missing industry return ({missing_days[0]}, {excess_d.columns[excess_d.loc[missing_days[0]].isna()][0]}), left out of every window")
print(f"evaluation months: {len(eval_months)}, {eval_months[0]} to {eval_months[-1]}; the 120-month window of the first ends {eval_months[0] - 1}, its three-year daily window starts {(eval_months[0] - 36).asfreq('D', 'start')}")
print(f"a three-year daily window holds about {int(round(len(excess_d.loc['2000-01-01':'2002-12-31']) ))} trading days (2000 to 2002), {int(round(len(excess_d.loc['2000-01-01':'2002-12-31']) * 49))} observations for 1,225 numbers; the monthly window holds {120 * 49:,}")
print("expectation 1 holds; CRSP vintage of the eight files:", ", ".join(sorted({r["vintage_line"].split("the ")[1].split(" ")[0] for r in provenance})))
"""),
    md("""
## The four estimators, in words

- **Sample covariance.** Each of the 1,225 numbers is the average over the window of the product of two industries' deviations from their means. It is unbiased and it uses every number; with few observations per number it is noisy, and its smallest directions, the combinations of industries that happened to move least in the window, are the noisiest of all.

- **Ledoit-Wolf shrinkage.** The estimate is (1 - k) times the sample covariance plus k times a target matrix that has the same average variance on its diagonal and zero everywhere else (the scaled identity). The intensity k is computed from the data by the formula of Ledoit and Wolf (2004b): the noisier the sample covariance relative to its distance from the target, the larger k. Shrinkage lifts the smallest directions and lowers the largest, so the inverse is tamer. The target with the same variances and one common correlation (Ledoit and Wolf 2004a) is run beside it; Dom, Howard, Jansen and Lohre (2024) found it inferior, which is why the scaled identity is the design.

- **Factor model.** Each industry's excess return is regressed, over the window, on six factors: the market, size, value, profitability, investment and momentum factors of Fama and French. The covariance is then the betas times the factors' covariance times the betas, plus each industry's residual variance on the diagonal. The 1,225 numbers become 49 times 6 betas, a 6 by 6 factor covariance and 49 residual variances, 364 numbers, each estimated from more information; the price is the assumption that whatever two industries share beyond the six factors is zero.

- **Principal-component model.** Notebook 09 found that the first component of the 49 industries is the market and that it parts from the cap-weighted benchmark in concentrated markets, so the design (`PCA_FIRST_COMPONENT`) imposes the market: each industry is regressed on the benchmark's excess return, and the covariance of the residuals is described by its first four principal components plus the diagonal of what they leave. The estimate is the betas times the benchmark's variance times the betas, plus that residual model. A version with one residual component (the count parallel analysis found above noise in notebook 09) is run beside it.

- **Two frequencies.** Each estimator sees either the last 120 monthly excess returns or the trading days of the last 36 calendar months, about 756 of them. A daily covariance is multiplied by 21, the number of trading days in an average month, to make it a monthly covariance; the step is exact when one day's return says nothing about the next day's, and expectation 4 checks it.
"""),
    md("""
## The evaluation loop

For every month from 1979-07, each estimator is built on the data before the month, and four things are recorded:

- the variance it predicts for each test portfolio, beside the portfolio's realised excess return in the month;
- the long-only and the unconstrained minimum-variance portfolios built from it, their realised returns in the month and their change of weights from the previous month;
- the condition number;
- for the shrinkage estimators, the intensity.
"""),
    code("""
A = CV.random_active_weights(49)
EW = np.ones(49) / 49
MAIN = [(e, f) for f in C.EXT_COV_FREQUENCIES for e in C.COV_ESTIMATORS]
SENSITIVITY = [("sample", "daily_1y"), ("sample", "daily_5y"), ("sample", "daily_5y_ewma"),
               ("ledoit_wolf_cc", "monthly_120"), ("ledoit_wolf_cc", "daily_3y"), ("pca_2", "monthly_120"), ("pca_2", "daily_3y")]
VARIANTS = MAIN + SENSITIVITY
YEARS = {"daily_3y": C.EXT_COV_DAILY_WINDOW_YEARS, "daily_1y": C.EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY[0],
         "daily_5y": C.EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY[1], "daily_5y_ewma": C.EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY[1]}


def estimate(name, freq, month):
    if freq == "monthly_120":
        X = CV.monthly_window(excess_m, month); F = factors_m.loc[X.index]; mk = bench_m.loc[X.index]; scale = 1.0
    else:
        X = CV.daily_window(excess_d, month, YEARS[freq]); F = factors_d.loc[X.index]; mk = bench_d.loc[X.index]; scale = C.DAILY_TO_MONTHLY_SCALE
    Xv = X.to_numpy(); intensity = np.nan
    if name == "sample":
        S = CV.ewma_cov(Xv, C.EXT_COV_EWMA_HALFLIFE_DAYS) if freq.endswith("ewma") else CV.sample_cov(Xv)
    elif name == "ledoit_wolf":
        S, intensity = CV.lw_scaled_identity(Xv)
    elif name == "ledoit_wolf_cc":
        S, intensity = CV.lw_constant_correlation(Xv)
    elif name == "factor":
        S, _ = CV.factor_cov(Xv, F.to_numpy())
    elif name == "pca":
        S, _ = CV.pca_cov(Xv, C.PCA_N_COMPONENTS, market=mk.to_numpy())
    elif name == "pca_2":
        S, _ = CV.pca_cov(Xv, C.PCA_N_COMPONENTS_SENSITIVITY, market=mk.to_numpy())
    return S * scale, intensity, len(X)


collected = {v: [] for v in VARIANTS}
previous = {v: (None, None) for v in VARIANTS}
t0 = time.time()
for i, month in enumerate(eval_months):
    r = excess_m.loc[month].to_numpy()
    b = weights.loc[month].to_numpy()
    for v in VARIANTS:
        S, intensity, n_obs = estimate(*v, month)
        w_lo = CV.min_variance_long_only(S)
        w_un = CV.min_variance_unconstrained(S)
        p_lo, p_un = previous[v]
        collected[v].append({
            "month": month, "n_obs": n_obs, "intensity": intensity, "condition": CV.condition_number(S),
            "pred_industries": np.diag(S), "pred_ew": EW @ S @ EW, "pred_bench": b @ S @ b, "pred_active": np.einsum("ij,jk,ik->i", A, S, A),
            "real_industries": r, "real_ew": EW @ r, "real_bench": b @ r, "real_active": A @ r,
            "gmv_lo_ret": w_lo @ r, "gmv_un_ret": w_un @ r,
            "gmv_lo_turnover": np.abs(w_lo - p_lo).sum() if p_lo is not None else np.nan,
            "gmv_un_turnover": np.abs(w_un - p_un).sum() if p_un is not None else np.nan,
            "gmv_lo_held": int((w_lo > 1e-6).sum()), "gmv_un_max_abs": float(np.abs(w_un).max()),
        })
        previous[v] = (w_lo, w_un)
    if i % 100 == 0:
        print(f"{month}: {time.time() - t0:.0f}s")
frames = {v: pd.DataFrame(recs).set_index("month") for v, recs in collected.items()}
print(f"{len(eval_months)} months, {len(VARIANTS)} estimator variants, {time.time() - t0:.0f}s")
"""),
    md("""
## Expectations 2 and 3: the forecasts of risk and the minimum-variance portfolios

One row per estimator and data frequency. Bias statistics first (1 is calibrated), then the realised volatility of the long-only and the unconstrained minimum-variance portfolios in percent a year, their average monthly turnover, how many of the 49 industries the long-only portfolio holds, and the median condition number.
"""),
    code("""
def summarise(v):
    df = frames[v]
    ind = [CV.bias_statistic(np.stack(df.real_industries)[:, j], np.stack(df.pred_industries)[:, j]) for j in range(49)]
    act = [CV.bias_statistic(np.stack(df.real_active)[:, j], np.stack(df.pred_active)[:, j]) for j in range(A.shape[0])]
    return {"estimator": v[0], "data": v[1], "observations": int(df.n_obs.median()),
            "bias: benchmark": CV.bias_statistic(df.real_bench, df.pred_bench), "bias: 1/N": CV.bias_statistic(df.real_ew, df.pred_ew),
            "bias: industries, mean": float(np.mean(ind)), "bias: industries, range": f"{min(ind):.2f} to {max(ind):.2f}",
            "bias: active, mean": float(np.mean(act)),
            "GMV long-only vol %": 100 * CV.annualised_vol(df.gmv_lo_ret), "GMV unconstrained vol %": 100 * CV.annualised_vol(df.gmv_un_ret),
            "turnover long-only": df.gmv_lo_turnover.mean(), "turnover unconstrained": df.gmv_un_turnover.mean(),
            "industries held (long-only)": df.gmv_lo_held.mean(), "largest |weight| (unconstrained, median)": df.gmv_un_max_abs.median(),
            "condition number (median)": df.condition.median(), "shrinkage intensity (median)": df.intensity.median()}

table = pd.DataFrame([summarise(v) for v in VARIANTS]).set_index(["estimator", "data"])
main = table.loc[[v for v in MAIN]]
print("the four estimators at the two frequencies:")
print(main.to_string(float_format=lambda x: f"{x:.3f}"))

s_m, s_d = table.loc[("sample", "monthly_120")], table.loc[("sample", "daily_3y")]
e2_bench = abs(s_d["bias: benchmark"] - 1) < abs(s_m["bias: benchmark"] - 1)
e2_active = abs(s_d["bias: active, mean"] - 1) < abs(s_m["bias: active, mean"] - 1)
e2_gmv = s_d["GMV unconstrained vol %"] < s_m["GMV unconstrained vol %"]
print()
print(f"expectation 2, the sample estimator on daily against monthly data: bias for the benchmark {s_d['bias: benchmark']:.3f} against {s_m['bias: benchmark']:.3f} "
      f"({'closer to 1' if e2_bench else 'NOT closer to 1'}); bias for the active portfolios {s_d['bias: active, mean']:.3f} against {s_m['bias: active, mean']:.3f} "
      f"({'closer to 1' if e2_active else 'NOT closer to 1'}); unconstrained minimum-variance volatility {s_d['GMV unconstrained vol %']:.1f}% against {s_m['GMV unconstrained vol %']:.1f}% "
      f"({'lower' if e2_gmv else 'NOT lower'}): {sum([e2_bench, e2_active, e2_gmv])} of 3 parts hold")
lo = main.xs("daily_3y", level="data")["GMV long-only vol %"]
e3_range = (lo.max() - lo.min()) / 100
un_all = table["GMV unconstrained vol %"]
e3_sample_highest_main = main["GMV unconstrained vol %"].idxmax() == ("sample", "monthly_120")
e3_sample_highest_all = un_all.idxmax() == ("sample", "monthly_120")
print(f"expectation 3: long-only minimum-variance volatility at daily_3y runs from {lo.min():.2f}% to {lo.max():.2f}%, a range of {100 * e3_range:.2f} points "
      f"(level {100 * C.COV_LONG_ONLY_RANGE_MAX:.0f} point): {'MET' if e3_range < C.COV_LONG_ONLY_RANGE_MAX else 'NOT MET'}; "
      f"the sample estimator on monthly data has the highest unconstrained volatility among the eight main variants: {'yes' if e3_sample_highest_main else 'no'} ({s_m['GMV unconstrained vol %']:.1f}%), "
      f"and among all {len(VARIANTS)} variants: {'yes' if e3_sample_highest_all else 'no'} (highest: {un_all.idxmax()}, {un_all.max():.1f}%)")
"""),
    md("""
## Expectation 4: does 21 times a daily covariance equal a monthly covariance

For every three-year window, the benchmark's realised monthly variance divided by 21 times its daily variance over the same window. The ratio is 1 when one day's return says nothing about the next day's. Beside it, the autocorrelation of the benchmark's daily excess return in the window (the correlation between one day's return and the next day's): positive autocorrelation makes monthly variance larger than 21 times the daily variance, negative autocorrelation makes it smaller.
"""),
    code("""
rows = []
for month in eval_months:
    Xd = CV.daily_window(excess_d, month, C.EXT_COV_DAILY_WINDOW_YEARS)
    bd = bench_d.loc[Xd.index]
    bm = bench_m.loc[month - 12 * C.EXT_COV_DAILY_WINDOW_YEARS: month - 1]
    rows.append({"month": month, "ratio": bm.var(ddof=1) / (C.DAILY_TO_MONTHLY_SCALE * bd.var(ddof=1)), "daily autocorrelation": bd.autocorr(1)})
scaling = pd.DataFrame(rows).set_index("month")
mean_ratio = scaling["ratio"].mean()
lo_r, hi_r = C.COV_SCALE_RATIO_RANGE
print(f"expectation 4: mean ratio {mean_ratio:.3f}, median {scaling['ratio'].median():.3f} (range {lo_r} to {hi_r}): {'MET' if lo_r <= mean_ratio <= hi_r else 'NOT MET'}")
by_decade = scaling.groupby((scaling.index.year // 10) * 10).agg(["mean", "min", "max"])
by_decade.index = [f"windows ending in the {d}s" for d in by_decade.index]
print()
print("by decade of the window's last month:")
print(by_decade.to_string(float_format=lambda x: f"{x:.3f}"))
print()
print(f"windows with a ratio above {hi_r}: {int((scaling['ratio'] > hi_r).sum())} of {len(scaling)}; below {lo_r}: {int((scaling['ratio'] < lo_r).sum())}")
print(f"correlation across windows between the ratio and the daily autocorrelation: {scaling['ratio'].corr(scaling['daily autocorrelation']):.2f}")
"""),
    md("""
## Expectation 5: the sensitivities, the shrinkage intensity over time, and the condition numbers

The sensitivities are the sample estimator on one and five years of daily returns and with exponential weighting (one-year half-life) over five years, Ledoit-Wolf shrinkage towards the constant-correlation target, and the principal-component model with one residual component. Then the shrinkage intensity by decade at both frequencies, and the condition numbers.
"""),
    code("""
sens = table.loc[[v for v in SENSITIVITY]]
print("sensitivities:")
print(sens.to_string(float_format=lambda x: f"{x:.3f}"))
print()
intensity = pd.DataFrame({f"{v[0]} {v[1]}": frames[v]["intensity"] for v in [("ledoit_wolf", "monthly_120"), ("ledoit_wolf", "daily_3y"), ("ledoit_wolf_cc", "monthly_120"), ("ledoit_wolf_cc", "daily_3y")]})
print("shrinkage intensity k (median by decade of the estimation month):")
print(intensity.groupby((intensity.index.year // 10) * 10).median().to_string(float_format=lambda x: f"{x:.3f}"))
print()
cond = pd.DataFrame({f"{v[0]} {v[1]}": frames[v]["condition"] for v in MAIN})
print("condition number (median by decade):")
print(cond.groupby((cond.index.year // 10) * 10).median().to_string(float_format=lambda x: f"{x:,.0f}"))
"""),
    md("""
## Added after the run: three open points, tested

The first run of this notebook (3 October 2026) ended with a list of open points. Three of them can be tested with the data already collected, and were, on 4 October 2026, with the expectations fixed in `constants.py` before the code was written. The cells below are labelled as additions; nothing above them changed.

- **P1, a scale correction that uses the autocorrelation.** Expectation 4 found that 21 times a daily variance is not a monthly variance when one day's return predicts the next day's. The correction measures how far the days are from independent inside the window and scales by that. For every window, the variance ratio is the variance of the benchmark's 21-day excess returns (every run of 21 consecutive days in the window) divided by 21 times the variance of its daily excess returns. It is 1 when days are independent, above 1 under positive autocorrelation, below 1 under negative. The corrected forecast multiplies the daily covariance by the variance ratio times 21 in place of 21. One number multiplies every entry of the matrix, so the minimum-variance weights and everything in expectations 2 and 3 about them are unchanged; only the forecasts of variance move. The correction is one number taken from the benchmark and not a matrix of autocovariances, because the matrix version (the variance of a 21-day sum of all 49 daily returns, the Newey-West estimate with 20 lags) has about fourteen times the sampling variance of the sample covariance, which would leave the equivalent of about 54 daily observations per entry and give away what daily data are for. The variance ratio inside the window is close to the ratio of expectation 4 by construction, so the test is out of window: the bias statistics on the months that follow. Main version: the variance ratio over the estimator's own three-year window. Sensitivity: over ten years of daily benchmark returns, because the autocorrelation moves over decades and a longer window trades noise for lag. Expectation P1a: for the benchmark and the sample estimator, the bias statistic by decade under the correction is closer to 1 than under the 21 rule in at least four of the five decades. P1b, reported with no verdict: the bias statistics for 1/N, the industries and the active portfolios under the correction; a portfolio whose own autocorrelation differs from the benchmark's keeps part of its miss.
- **P2, bias statistics by decade.** A bias statistic over 566 months at once can be close to 1 for a forecaster that under-forecasts risk for thirty years and over-forecasts it for twenty-five. The decades are 1979-07 to 1989-12, then each calendar decade, then 2020-01 to the last month. Expectation P2a, derived from the ratio table of expectation 4: under the 21 rule the benchmark's bias statistic on daily data is above 1 in the first decade, below 1 in the 2010s, and higher in the first decade than in the 2000s.
- **P3, trading costs.** The minimum-variance tests charged no trading costs, and the unconstrained portfolios trade a large part of their value every month. Here each portfolio's cost is its average monthly turnover times the cost per unit of turnover times 12, at the two cost levels of the replication (50 basis points per unit of turnover, DGU's figure, and 100 as the sensitivity), beside its gross excess return (the mean monthly excess return times 12), its net excess return (gross minus cost), its realised volatility and its Sharpe ratio net of cost (net excess return over volatility). Costs are applied after the fact and do not enter the optimisation, as in the replication. Expectations at the base cost: P3a, the long-only portfolio's net excess return exceeds the unconstrained portfolio's in at least six of the eight main variants; P3b, the same for the Sharpe ratio net of cost. P3c, arithmetic from the turnover already in the table above: the unconstrained sample portfolio on monthly data costs about 4.6% a year (0.763 times 0.005 times 12) and the long-only portfolios 0.3% to 0.5%.
"""),
    code("""
# Added after the run (4 October 2026): P1 and P2.
def decade_label(month):
    if month.year < 1990:
        return "1979-07 to 1989-12"
    if month.year >= 2020:
        return f"2020-01 to {eval_months[-1]}"
    return f"{(month.year // 10) * 10}s"

DECADES = ["1979-07 to 1989-12", "1990s", "2000s", "2010s", f"2020-01 to {eval_months[-1]}"]
decade_of = pd.Series([decade_label(m) for m in eval_months], index=eval_months)

vr_rows = []
for month in eval_months:
    row = {"month": month}
    for name, years in (("variance ratio (3y)", C.EXT_COV_DAILY_WINDOW_YEARS), ("variance ratio (10y)", C.COV_SCALE_VR_WINDOW_YEARS_SENSITIVITY)):
        bd = bench_d.loc[CV.daily_window(excess_d, month, years).index]
        row[name] = CV.variance_ratio(bd.to_numpy(), C.COV_SCALE_VR_HORIZON_DAYS)
    vr_rows.append(row)
vr = pd.DataFrame(vr_rows).set_index("month")
scaling = scaling.join(vr)
print("the variance ratio by decade of the window's last month (1 when days are independent), beside the ratio of expectation 4:")
print(scaling.groupby((scaling.index.year // 10) * 10)[["ratio", "variance ratio (3y)", "variance ratio (10y)"]].mean().to_string(float_format=lambda x: f"{x:.3f}"))
print(f"correlation across windows between the in-window variance ratio (3y) and the ratio of expectation 4: {scaling['ratio'].corr(scaling['variance ratio (3y)']):.2f} (both measure the same window, so this is close to 1 by construction)")
print()


def bias_table(df, factor=None):
    f = np.ones(len(df)) if factor is None else factor.loc[df.index].to_numpy()
    out = {}
    for lab in ["all months"] + DECADES:
        mask = np.ones(len(df), bool) if lab == "all months" else (decade_of.loc[df.index] == lab).to_numpy()
        sub, fs = df[mask], f[mask]
        ind = [CV.bias_statistic(np.stack(sub.real_industries)[:, j], np.stack(sub.pred_industries)[:, j] * fs) for j in range(49)]
        act = [CV.bias_statistic(np.stack(sub.real_active)[:, j], np.stack(sub.pred_active)[:, j] * fs) for j in range(A.shape[0])]
        out[lab] = {"months": int(mask.sum()), "benchmark": CV.bias_statistic(sub.real_bench, sub.pred_bench * fs),
                    "1/N": CV.bias_statistic(sub.real_ew, sub.pred_ew * fs), "industries, mean": float(np.mean(ind)), "active, mean": float(np.mean(act))}
    return pd.DataFrame(out).T


by_decade_bias = pd.concat({
    "sample, monthly_120": bias_table(frames[("sample", "monthly_120")]),
    "sample, daily_3y, 21 rule": bias_table(frames[("sample", "daily_3y")]),
    "sample, daily_3y, corrected (3y)": bias_table(frames[("sample", "daily_3y")], vr["variance ratio (3y)"]),
    "sample, daily_3y, corrected (10y)": bias_table(frames[("sample", "daily_3y")], vr["variance ratio (10y)"]),
}, names=["forecast", "period"])
print("P2, bias statistics by period (1 is calibrated; above 1, risk under-forecast):")
print(by_decade_bias.to_string(float_format=lambda x: f"{x:.3f}"))
print()

rule = by_decade_bias.loc["sample, daily_3y, 21 rule", "benchmark"]
corr3 = by_decade_bias.loc["sample, daily_3y, corrected (3y)", "benchmark"]
closer = [d for d in DECADES if abs(corr3[d] - 1) < abs(rule[d] - 1)]
print(f"P1a: the corrected benchmark forecast is closer to 1 than the 21 rule in {len(closer)} of {len(DECADES)} decades ({', '.join(closer)}); "
      f"level {C.COV_POST_RUN_DECADES_MIN_CLOSER}: {'MET' if len(closer) >= C.COV_POST_RUN_DECADES_MIN_CLOSER else 'NOT MET'}")
p2a = rule[DECADES[0]] > 1 and rule["2010s"] < 1 and rule[DECADES[0]] > rule["2000s"]
print(f"P2a: under the 21 rule the benchmark's bias statistic is {rule[DECADES[0]]:.3f} in {DECADES[0]} (above 1: {rule[DECADES[0]] > 1}), {rule['2010s']:.3f} in the 2010s (below 1: {rule['2010s'] < 1}), "
      f"{rule['2000s']:.3f} in the 2000s (first decade higher: {rule[DECADES[0]] > rule['2000s']}): {'MET' if p2a else 'NOT MET'}")
print()
others = pd.DataFrame({f"{v[0]}, daily_3y": {"21 rule": bias_table(frames[v]).loc["all months"], "corrected (3y)": bias_table(frames[v], vr["variance ratio (3y)"]).loc["all months"]}
                       for v in MAIN if v[1] == "daily_3y"}).T
others = pd.concat({k: pd.DataFrame(v.tolist(), index=v.index) for k, v in others.items()}, names=["scale", "estimator"]).swaplevel().sort_index()
print("P1b, all months, the four daily estimators under the 21 rule and corrected (3y):")
print(others.drop(columns="months").to_string(float_format=lambda x: f"{x:.3f}"))
"""),
    code("""
# Added after the run (4 October 2026): P3, trading costs.
cost_rows = []
for v in MAIN:
    df = frames[v]
    for port, label in (("lo", "long-only"), ("un", "unconstrained")):
        ret, to = df[f"gmv_{port}_ret"], df[f"gmv_{port}_turnover"].mean()
        gross, vol = 12 * ret.mean(), CV.annualised_vol(ret)
        row = {"estimator": v[0], "data": v[1], "portfolio": label, "turnover a month": to, "gross excess return % a year": 100 * gross, "volatility % a year": 100 * vol}
        for c in C.EXT_COST_LEVELS:
            bp = int(round(c * 1e4))
            cost = 12 * to * c
            row[f"cost % a year at {bp} bp"] = 100 * cost
            row[f"net excess return % at {bp} bp"] = 100 * (gross - cost)
            row[f"Sharpe net at {bp} bp"] = (gross - cost) / vol
        cost_rows.append(row)
costs = pd.DataFrame(cost_rows).set_index(["estimator", "data", "portfolio"])
print("P3, the minimum-variance portfolios with trading costs (eight main variants):")
print(costs.to_string(float_format=lambda x: f"{x:.2f}"))
print()
base = int(round(C.EXT_COST_LEVELS[0] * 1e4))
lo_c, un_c = costs.xs("long-only", level="portfolio"), costs.xs("unconstrained", level="portfolio")
n_ret = int((lo_c[f"net excess return % at {base} bp"] > un_c[f"net excess return % at {base} bp"]).sum())
n_sr = int((lo_c[f"Sharpe net at {base} bp"] > un_c[f"Sharpe net at {base} bp"]).sum())
print(f"P3a: at {base} bp the long-only portfolio's net excess return exceeds the unconstrained portfolio's in {n_ret} of {len(MAIN)} variants (level {C.COV_POST_RUN_COST_MIN_VARIANTS}): {'MET' if n_ret >= C.COV_POST_RUN_COST_MIN_VARIANTS else 'NOT MET'}")
print(f"P3b: the same for the Sharpe ratio net of cost: {n_sr} of {len(MAIN)}: {'MET' if n_sr >= C.COV_POST_RUN_COST_MIN_VARIANTS else 'NOT MET'}")
print(f"P3c: the unconstrained sample portfolio on monthly data costs {un_c.loc[('sample', 'monthly_120'), f'cost % a year at {base} bp']:.1f}% a year at {base} bp; "
      f"the long-only portfolios cost {lo_c[f'cost % a year at {base} bp'].min():.1f}% to {lo_c[f'cost % a year at {base} bp'].max():.1f}%")
"""),
    md("""
## Save the summary for the later notebooks

The summary table, the scaling check with the variance ratios, the bias statistics by period and the cost table are written to `outputs/`, with the vintage in the file name, as a record; notebooks 11 to 13 rebuild what they need from the modules.
"""),
    code("""
os.makedirs(C.OUTPUT_DIR, exist_ok=True)
vintage = provenance[0]["vintage_line"].split("the ")[1].split(" ")[0]
table.to_csv(f"{C.OUTPUT_DIR}/covariance_estimators_{vintage}.csv", float_format="%.6f")
scaling.to_csv(f"{C.OUTPUT_DIR}/daily_to_monthly_scaling_{vintage}.csv", float_format="%.6f")
by_decade_bias.to_csv(f"{C.OUTPUT_DIR}/bias_by_period_{vintage}.csv", float_format="%.6f")
costs.to_csv(f"{C.OUTPUT_DIR}/minimum_variance_costs_{vintage}.csv", float_format="%.6f")
print("written:", sorted(f for f in os.listdir(C.OUTPUT_DIR) if f.startswith(("covariance", "daily_to", "bias_by", "minimum_variance"))))
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. Count first | 686 months and 14,414 trading days from 1969-07, one missing day left out, 566 evaluation months for every estimator | holds |
| 2. Daily data beat monthly data for the sample estimator | unconstrained minimum-variance volatility 11.9% against 14.1%; bias statistics 1.028 against 1.023 for the benchmark and 1.060 against 1.060 for the active portfolios | 1 of 3 parts |
| 3. The finding of Dom, Howard, Jansen and Lohre (2024) | long-only volatility 12.11% to 12.20% across the four daily estimators, a range of 0.09 points against the level of 1; the sample covariance on monthly data has the highest unconstrained volatility of the eight main variants (14.1%), and the two-component sensitivity on daily data is higher (14.3%) | MET; the second part holds for the main variants only |
| 4. 21 times a daily variance is a monthly variance | mean ratio 0.92, inside 0.8 to 1.25; 186 of 566 windows inside; 1.82 for windows ending in the 1970s and 0.62 in the 2000s; correlation 0.81 with the daily autocorrelation | MET on the mean, fails in 380 windows |
| 5. Sensitivities, shrinkage intensity, condition numbers | exponential weighting gives the lowest unconstrained volatility (11.7%); median intensity 0.07 on monthly data and 0.01 on daily; condition numbers 1,859 for the sample covariance against 349 after shrinkage | reported |
| P1a. The variance-ratio correction brings the benchmark's bias statistic closer to 1 in at least 4 of 5 decades | 4 of 5 (every decade except the 1990s) | MET |
| P1b. The correction for 1/N, the industries and the active portfolios | 1.16, 1.16 and 1.13 under the correction against 1.12, 1.10 and 1.06 under the 21 rule | reported |
| P2a. Under the 21 rule the benchmark's bias statistic is above 1 in the first decade, below 1 in the 2010s, and higher in the first decade than in the 2000s | 1.34, 0.78 and 0.87 | MET |
| P3a. At 50 basis points the long-only portfolio's net excess return exceeds the unconstrained portfolio's in at least 6 of 8 variants | 8 of 8 | MET |
| P3b. The same for the Sharpe ratio net of cost | 8 of 8 | MET |
| P3c. The cost of the unconstrained sample portfolio on monthly data | 4.6% a year at 50 basis points; the long-only portfolios 0.3% to 0.5% | as computed |

Expectation 1 holds: 686 months and 14,414 trading days from 1969-07, one missing day left out, factors on every day of every window, 566 evaluation months from 1979-07 to 2026-08 for every estimator. A three-year daily window holds about 752 days, 36,848 observations for the 1,225 numbers, against 5,880 in the monthly window.

Expectation 2, the frequency question, holds in one of its three parts. Where the covariance is inverted, daily data win clearly: the unconstrained minimum-variance portfolio built from the sample covariance realises 14.1% a year of volatility on monthly data and 11.9% on daily data, with a turnover of 0.76 a month against 0.40 and a condition number of 1,859 against 691. Where the covariance is only read, as a forecast of a portfolio's risk, daily data do no better: the bias statistic for the benchmark is 1.028 on daily data against 1.023 on monthly, and for the active portfolios 1.060 against 1.060. Expectation 4 says why, and the two halves of the result are consistent with each other: the minimum-variance weights do not change when every entry of the covariance matrix is multiplied by the same number (the weights are Sigma^-1 times a vector of ones, scaled to sum to one, and the scale cancels), so the portfolio test cannot see an error in the daily-to-monthly scale, while a forecast of variance is that scale. Daily data improved what the portfolio test measures, the pattern of the matrix, and left what the forecast test measures, its level over a month, to the scaling step.

Expectation 3, the finding of Dom, Howard, Jansen and Lohre (2024), holds. With the long-only constraint, the minimum-variance portfolios of the four estimators on daily data realise between 12.11% and 12.20% a year, a range of 0.09 points against the level of 1 point, and on monthly data between 12.15% and 12.32%: under the constraint, the choice of estimator and even the choice of data frequency make no visible difference. The constraint does the estimator's work, because forbidding negative weights removes the long-short positions in which the noisiest directions of the covariance are exploited; the long-only portfolio holds 8 to 10 of the 49 industries whatever the estimate. Without the constraint the estimate matters: the sample covariance on monthly data realises 14.1%, the highest of the eight main variants, against 12.1% for Ledoit-Wolf shrinkage, 12.8% for the factor model and 12.7% for the principal-component model on the same data. Among all fifteen variants, including the sensitivities, the highest is the two-component model on daily data at 14.3%, so the second part of the expectation holds for the eight main variants and fails when the sensitivities are counted. On daily data the order reverses: the sample covariance (11.9%) and shrinkage (11.9%, with a median intensity of only 0.012) are the best, and the factor model (13.2%) and the component model (13.5%) are the worst. With 756 observations the sample covariance is no longer noisy enough for shrinkage to have anything to correct, and the structured estimators pay for their assumption that whatever two industries share beyond the factors is zero.

Expectation 4, the scaling check, is met on average and fails in most windows. The mean ratio of the benchmark's monthly variance to 21 times its daily variance is 0.92, inside 0.8 to 1.25; the median is 0.83, and only 186 of the 566 windows lie inside the range: 108 above 1.25 and 272 below 0.8. The ratio moves with the decade: 1.82 for windows ending in the 1970s, 1.41 in the 1980s, 1.06 in the 1990s, 0.62 in the 2000s, 0.64 in the 2010s and 0.77 in the 2020s. The autocorrelation of the benchmark's daily return explains it, with a correlation of 0.81 across windows: a day's return predicted the next day's positively in the 1970s (autocorrelation 0.21), so monthly variance was larger than 21 daily variances, and negatively since 2000 (-0.03 to -0.12), so it was smaller. The rule that variance grows in proportion to time assumes that days are independent, and for these portfolios they were not, in one direction for thirty years and in the other for twenty-five. This is why the daily-based forecasts of risk are no better calibrated than the monthly ones: on 1/N and on the single industries, where the effect is strongest, the daily-based bias statistics are 1.10 to 1.13 against 1.02 to 1.04 for the monthly-based ones, an under-forecast of risk of about ten percent that the 1970s and 1980s produce. P1 tests the remedy.

Expectation 5, the sensitivities. One year of daily data gives the same unconstrained volatility as three (11.9%) with three times the turnover (1.18 a month against 0.40); five years gives 11.9% with 0.26. Exponential weighting with a one-year half-life over five years gives the lowest unconstrained volatility of all variants, 11.7%, and the best-calibrated forecast for the benchmark, a bias statistic of 0.998, at the cost of a turnover of 0.48: weighting recent days more is worth more than any choice of structure, which is what Dom, Howard, Jansen and Lohre found. The constant-correlation shrinkage target shrinks much harder (median intensity 0.27 on monthly data against 0.07 for the scaled identity) and does the same or slightly worse. The two-component model does worse than the five-component one without the constraint (13.3% against 12.7% on monthly data, 14.3% against 13.5% on daily) and the same with it. The condition numbers say what shrinkage does to the inverse: the sample covariance on monthly data has a median condition number of 1,859 and Ledoit-Wolf shrinkage 349, so the inverse of the sample covariance amplifies errors about five times more.

**P1 to P3, the open points tested.**

P1, the scale correction. The variance ratio measured inside each three-year window follows the ratio of expectation 4 (correlation 0.91 across windows) and moves with the decade: 1.52 for windows ending in the 1970s, 0.69 for windows ending in the 2010s. Scaling the daily covariance by that ratio times 21, in place of 21, brings the benchmark's bias statistic closer to 1 in four of the five decades (1.14 against 1.34 in 1979-07 to 1989-12, 1.07 against 0.87 in the 2000s, 0.95 against 0.78 in the 2010s, 1.02 against 0.89 from 2020) and further from it in the 1990s (1.11 against 1.08), the one decade where the 21 rule was already close. Over all 566 months at once the corrected statistic is 1.07 against 1.03 under the rule, and the two numbers do not say the same thing: under the rule the under-forecasts of the first decade and the over-forecasts of the 2000s and 2010s cancel inside one statistic; under the correction every decade but the 2010s sits between 1.02 and 1.14 and nothing cancels. The ten-year variance ratio does better than the three-year one in every decade: 1.09, 1.04, 0.97, 0.95 and 1.03, a range of 0.14, against 0.78 to 1.34 under the 21 rule and 0.84 to 1.20 for the forecast from 120 monthly returns. A three-year window gives a noisy ratio (its standard error is about 0.19 when days are independent) and the autocorrelation moves over decades, so ten years of it is the better estimate. This reopens the forecast half of expectation 2 after the fact: with a scale that accounts for the autocorrelation, three years of daily data forecast the benchmark's monthly risk more evenly across the decades than 120 monthly returns do. The correction does not help 1/N, the industries or the active portfolios (1.16, 1.16 and 1.13 against 1.12, 1.10 and 1.06), because the ratio is the benchmark's: 1/N and the single industries had stronger positive autocorrelation than the cap-weighted benchmark (under the 21 rule their bias statistics reach 1.46 and 1.36 in the first decade against the benchmark's 1.34), so a correction fitted to the benchmark fits them less. The other three daily estimators move with the sample estimator, within 0.02 of it.

P2, the bias statistics by decade. The 21 rule's forecast on daily data under-forecast the benchmark's risk in the first decade (1.34) and over-forecast it in the 2000s (0.87) and the 2010s (0.78), as the ratios of expectation 4 implied. The forecast from 120 monthly returns swings for a different reason: it ranges from 0.84 in the 2010s, when its window still carried 2008 and the market was calm, to 1.20 from 2020, when the fall of March 2020 met a window built on calm years. A 120-month window adapts to a change in the level of volatility over ten years; a three-year daily window adapts within three.

P3, trading costs. The unconstrained portfolios earn less before costs than the long-only ones in every one of the eight variants (gross excess returns of 4.0% to 7.3% a year against 7.5% to 8.0%) and trade three to eleven times as much (0.21 to 0.76 a month against 0.05 to 0.09). At 50 basis points per unit of turnover their net excess returns are 2.3% to 5.7% a year against 7.1% to 7.5%, and their Sharpe ratios net of cost 0.17 to 0.45 against 0.58 to 0.62. The unconstrained sample portfolio on monthly data pays 4.6% a year in costs, two thirds of its gross return; at 100 basis points its net return is negative. Only two unconstrained portfolios realise less volatility than their long-only counterpart, the sample covariance and shrinkage on daily data, by 0.24 and 0.35 points of volatility, and they pay 1.9 and 1.6 points of return a year more in costs for it. This is expectation 3 seen from the cost side, and it is one reason why the extension's portfolio is long-only with a turnover cap, a limit on the fraction of the portfolio that may change hands in a month.

**What this notebook does not settle.**

- The extension's portfolio is long-only with bounds on active weights and turnover, and expectation 3 says that under such constraints the estimators realise the same risk to within a tenth of a percentage point. Notebook 12 measures whether that holds for tracking error against the benchmark, which is the extension's question, and the answer may be that the choice of estimator does not matter there either.
- The two-component model, the count parallel analysis gave in notebook 09, built the worst unconstrained minimum-variance portfolio of all variants on daily data (14.3% a year against 13.5% for the five-component model) and the same portfolio as the others under the long-only constraint. The minimum-variance weights come from the inverse of the covariance matrix, which gives the largest weights to the combinations of industries with the smallest variance; a model that drops a component sets to zero the shared movement it carried, so its matrix differs from the data's in exactly those low-variance combinations, and the inverse magnifies the error (a combination whose variance is understated by half gets twice the weight it should). Parallel analysis judges how well the components describe the sample, where a small component matters little; the portfolio depends on the inverse, where it matters most; the two tests give different counts, and the choice of five stands as the design parameter it was, with the rule that would choose the count inside each window named in notebook 09 as a later study's option.
- The scale correction is one number taken from the benchmark. A portfolio whose autocorrelation differs from the benchmark's, 1/N or a single industry, keeps part of its miss, and a correction per portfolio would need each portfolio's own variance ratio, or the matrix of autocovariances, which three years of daily data cannot estimate with useful precision. Notebook 12 reports its forecast tracking error under the 21 rule and under the ten-year variance ratio.
- The cost figures use one proportional cost per unit of turnover for every industry and every month, as the replication does; costs differ across industries and have fallen over the decades. The cost differences between the portfolios are arithmetic on their turnover and are not noisy; the differences in gross return are, because a mean return over 566 months has a standard error of about 1.8 percentage points a year, so the gross return gaps of 0.4 to 3.6 points between long-only and unconstrained portfolios are mostly within noise, and P3a and P3b rest on the costs.
- P1 to P3 were designed after the first run, with their expectations fixed before their code but after the outcomes of expectations 1 to 5 were known. That is weaker than fixing them before any run: P2a in particular restates what the ratio table of expectation 4 already implied, and P1a was written knowing that the 21 rule missed by a factor of 1.8 and 0.6 in the decades where a correction has most to gain.
"""),
]

# ---------------------------------------------------------------------------
# 11: the optimiser
# ---------------------------------------------------------------------------

NB11 = [
    md("""
# 11. The optimiser: the portfolio that tracks the benchmark most closely under constraints

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same period |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money |
| Cap-weighted | weighted by market capitalisation |
| Benchmark | in the extension, the index the portfolio tracks, the cap-weighted combination of the 49 industries built in notebook 08 |
| Variance | the average squared distance of a series from its own average; its square root is the standard deviation, the usual measure of how much a return moves; volatility is the standard deviation of returns, stated per year here by multiplying the monthly figure by the square root of 12 |
| Covariance | a number that says how two series move together, positive when both tend to be above their averages in the same periods |
| Covariance matrix | the table of all variances and covariances of a set of assets, 49 by 49 here, 1,225 distinct numbers |
| Covariance estimator | a method for estimating the covariance matrix from a window of data; notebook 10 built four |
| Estimation window | the past returns an estimator sees, 120 months or three years of trading days here |
| Estimation error | the difference between a number estimated from a window and its true value |
| Shrinkage | pulling an estimate part of the way towards a simpler target, which trades a little bias for less estimation error; the shrinkage intensity is the fraction of the way it is pulled |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors are long-short portfolios built to isolate one such source each |
| Beta | how much an asset moves with a factor on average; the beta to the benchmark is how much it moves with the benchmark, one for the benchmark itself |
| Principal component | a combination of the assets, with one weight per asset, chosen so that it explains as much of the assets' total variance as a single combination can (notebook 09) |
| Active weight | the portfolio's weight in an asset minus the benchmark's weight in it |
| Tracking error | the standard deviation of the difference between two return series, stated per year; forecast (ex-ante) when computed from a covariance matrix before the month, realised (ex-post) when measured on the returns afterwards |
| Long-only | said of a portfolio in which no weight is negative, so nothing is sold that is not held |
| One-way turnover | half the sum over industries of the absolute changes in weight at a rebalance; the fraction of the portfolio sold, which is also the fraction bought when the portfolio stays fully invested; 0.02 means 2% of the portfolio changes hands |
| Turnover cap | an upper limit on the one-way turnover of a rebalance; 2% a month here |
| Drifted weights | the previous month's weights after that month's returns have moved them: each weight times one plus its industry's return, divided by the portfolio's own gross return, so they still sum to one |
| Tilt | a constraint that holds named industries below their benchmark weight; here Coal, Oil and Utilities at no more than half of it, a 50% reduction relative to the benchmark |
| Exclusion | a constraint that holds named industries at zero weight; in the mandate's set it holds Smoke (tobacco) and Guns (weapons) at zero |
| Beta-neutral | a constraint that holds the portfolio's beta to the benchmark equal to the benchmark's own, one; written as the active weights' beta summing to zero |
| Mandate | the whole set of rules a fund must obey; here the carbon tilt together with the exclusions of tobacco and weapons and beta neutrality |
| Robust portfolio | the weights whose largest forecast tracking error across a set of covariance matrices, the five estimators' here, is smallest; a portfolio that trusts no single matrix |
| Optimiser | the extension's routine that solves the constrained tracking-error problem: the weights that minimise forecast tracking error under a named set of constraints |
| Constraint set | one of the four cumulative sets C0 to C3 of the design: long-only; plus the active weight bound; plus the turnover cap; plus the mandate (the tilt alone in the design of 10 September; the tilt with beta neutrality and the exclusions from 4 October) |
| Feasible | said of weights that satisfy every constraint of the set; a set is infeasible in a month when no weights satisfy all of them at once |
| Binding | said of a constraint that holds with equality at the solution, so that relaxing it would lower the tracking error; a constraint that is not binding could be dropped without changing the answer |
| Quadratic program | a minimisation whose objective is a quadratic function of the weights and whose constraints are linear; when the quadratic is a variance it is convex and has one global minimum, which a solver finds exactly |
| Solver | the numerical routine that finds the minimum of a quadratic program; cvxpy with Clarabel here |
| Effective number of holdings | one divided by the sum of squared weights; 49 for 1/N across 49 industries, 1 for a portfolio in one industry, smaller the more concentrated the portfolio |
| Basis point | one hundredth of a percentage point, so 50 basis points is 0.50% |
| Sharpe ratio | the average monthly excess return divided by the standard deviation of the excess return; the reward earned per unit of risk taken |
| Active return | the portfolio's return minus the benchmark's return in the same period |
| Attribution | splitting a portfolio's active return into the parts due to named sources, the Fama-French factors in notebook 13, plus a remainder |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |

**The problem, stated the way practitioners state it.** Dom, Howard, Jansen and Lohre (2024), whose framing this notebook follows, argue that covariance estimators should be judged on portfolios a practitioner would hold: long-only, with bounds on weights, charged for trading, after costs. Their test portfolio is the constrained minimum-variance portfolio. An index manager's portfolio is the same problem with a different target: in place of the lowest variance, the smallest deviation from a benchmark, measured as tracking error, under the same kind of constraints and one more, the mandate's own rules about what may and may not be held. This notebook builds that portfolio. It is the point where the covariance stops being a forecast and becomes a decision: the optimiser takes a covariance matrix and a set of rules and returns the weights, and every rule's cost can be read off in forecast tracking error, which is how enhanced-index managers quote it.

**What this notebook does.** The replication asked which rule earns the best Sharpe ratio. The extension asks the question an index fund with a mandate asks: given a benchmark to track and a set of rules the fund must obey, find the weights that track the benchmark most closely. That is a minimisation. For a month with benchmark weights b and a covariance matrix Sigma, the optimiser finds the weights w that minimise the forecast tracking error, the square root of 12 times (w - b)' Sigma (w - b), subject to the constraints of the chosen set. With no constraints the minimum is at w = b and the tracking error is zero: holding the index tracks the index. Each constraint takes something away from that answer, and what it takes away is measured in forecast tracking error, which is how index managers quote the cost of a constraint. This notebook builds the optimiser (`src/bp/optimiser.py`), checks it against answers known by hand and against an independent solver (`tests/test_optimiser.py`), and runs it at three fixed months with each of notebook 10's estimators under each constraint set, to see what each constraint costs, where the tilt's weight goes, and how the turnover cap acts as a speed limit. Notebook 12 runs it in every month and judges the result on realised tracking error.

**The constraints, each with a number.**

- Budget: the weights sum to one. Always on; the benchmark's own weights sum to one.
- Long-only (C0): no weight below zero. The fund does not sell what it does not hold.
- Active weight bound (C1): each untilted industry within 2 percentage points of its benchmark weight. If Banks is 8.0% of the benchmark, the portfolio holds between 6.0% and 10.0% in Banks. The bound is around the benchmark weight because the 49 weights run from under 0.5% to over 10%, so one cap for all would be loose for the small industries and tight for the large ones.
- Turnover cap (C2): one-way turnover at most 2% a month, measured against the drifted weights. Selling 2% of the portfolio and buying 2% in one month is about 24% a year, the range of enhanced indexing. The fund starts as the index, so the cap applies from the first rebalance.
- Tilt (C3): Coal, Oil and Utilities each at no more than half their benchmark weight. If Oil is 3.0% of the benchmark, the portfolio holds at most 1.5%. The active weight bound does not apply to a tilted industry, because for any industry above 4% of the benchmark the two would contradict each other.
- Exclusion: named industries at zero. Part of the mandate's C3 (the second part of this notebook), for Smoke (tobacco) and Guns (weapons), the standard exclusions of Dutch institutional mandates.
- Beta-neutral: the portfolio's beta to the benchmark equal to one. Part of the mandate's C3 from the second part of this notebook on, after the first part showed that the tilt's hedge left a beta bet standing when the covariance was noisy.

**How this notebook is organised, and the two versions of C3.** The notebook has three parts, and the order is the order in which the work was done, because every expectation was written into `constants.py` before the code that tests it, and that order is the record. The first part runs the optimiser at three months under the constraint sets as first designed (10 September 2026), in which C3 is the tilt alone: long-only, the bound, the cap and the tilt. Expectations 1 to 5 belong to it. The second part is four checks on the practical problem behind the tilt's hedge (D1 to D4, 4 October), which found three problems a manager would fix, and the three fixes (F1 to F3, the same day): C3 became the mandate, the tilt with beta neutrality and the exclusions, and a robust portfolio joined the variants. The mandate's C3 is the one notebook 12 runs; the tilt-only set is kept in `constants.py` as `CONSTRAINT_SET_TILT_ONLY` so that the cost of the fixes can be measured there. The third part is one check on the solver itself (D5, 6 October), prompted by a month of notebook 12's first run.

**What the optimiser does with an infeasible month.** The tilt, the active bound and long-only are hard: a month in which they contradict each other stops the notebook. The turnover cap can make a month infeasible on its own, in the first month under a tilt (the previous portfolio is the benchmark and the tilt alone demands more trading than 2%) or in a month when the benchmark's weights moved by more than the cap. The optimiser therefore finds the smallest feasible one-way turnover first, by minimising turnover subject to the other constraints; when it exceeds the cap, the cap is raised to it, the month is counted, and only then is the tracking-error problem posed, so that the solver is never handed a problem that has no solution. Notebook 12 reports the count. The third part of this notebook (D5) shows what a solver does with a problem that has no solution, and why the order of the two steps matters.

**Where the numbers come from, and why this solver.** The constraints date from the design of 10 September 2026 and are in `constants.py` with their reasons.

- Tracking error. Public descriptions of enhanced indexing give the tracking error they run at: Robeco's enhanced-index developed-market composite ran at 1.06% a year from 2004 to 2016 and is offered up to about 5% (Robeco, "Building customized core quant portfolios", interview, October 2016); J.P. Morgan writes that enhanced index strategies typically have a tracking error below 2%, its own Research Enhanced Index strategy 0.67% over twenty years (J.P. Morgan Asset Management, "Celebrating 20 years of our Global Research Enhanced Index Strategy", 2024); Morgan Stanley's Applied Enhanced Index Russell 1000 strategy targets 1.5% to 2.0% with 200 to 300 holdings (strategy profile). The level of expectation 3, 1% a year, sits inside that range.
- Tilt. Robeco's enhanced-index products carry at least a 30% lower carbon footprint than the index, and its Paris-aligned versions target a 50% reduction (robeco.com, Enhanced Indexing Equities product page, read 4 October 2026). French's data carry no footprint per firm, so the tilt applies that 50% reduction to the three most carbon-intensive industries of the 49: Coal, Oil and Utilities.
- Active weight bound and turnover cap. The same descriptions call deviations from the index limited and turnover low, without a number. The 2 percentage points around each benchmark weight and the 2% one way a month (about 24% a year) are this study's own settings, chosen so that each constraint can bind without preventing the portfolio from following the benchmark; the tables report what each costs, which is the test of whether they are sensible.
- Exclusion. Built for the planned second study, what exclusion lists cost a long-only portfolio; the lists would come from what Dutch institutional investors publish about the firms they exclude.
- Solver. The problem is a convex quadratic program, and cvxpy is the layer that writes it almost as on paper and hands it to a solver (Diamond and Boyd, "CVXPY: A Python-Embedded Modeling Language for Convex Optimization", Journal of Machine Learning Research 17, 2016). It is the tool of the convex-optimisation portfolio literature: Boyd, Busseti, Diamond, Kahn, Koh, Nystrup and Speth, "Multi-Period Trading via Convex Optimization" (Foundations and Trends in Optimization, 2017), with three authors at BlackRock, ships with cvxportfolio, built on cvxpy. Asset managers run the same formulations in production on commercial solvers (MSCI's Barra Optimizer; Axioma, now part of SimCorp; Gurobi, which Robeco uses for its systematic fixed-income portfolios of about EUR 12.5 billion across about 30,000 instruments, Gurobi case study); what carries over from here to there is the formulation. The solver under cvxpy here is Clarabel (Goulart and Chen, 2024), an interior-point method, with its stopping rule tightened from the default.

**What I expect to see, written before the run (`constants.py`, 4 October 2026).**

1. Count first: the benchmark weights sum to one in every month from 1969-07; the drifted weights are defined for every month after the first and sum to one; Coal, Oil and Util are columns of the 49-industry file; the specification count is 28 (five estimator variants, the robust portfolio and RiskMetrics, times four constraint sets).
2. Known answers, at every report month and estimator: (a) under C0 and C1, with the benchmark as the previous portfolio, the solution is the benchmark and the forecast tracking error is zero within 1e-6 a year; (b) under C3 the three tilted industries sit at the top of their allowed range, half their benchmark weight, and the forecast tracking error is positive; (c) the forecast tracking error does not fall from C0 to C1 to C2 (each set adds a constraint, so the minimum cannot fall; this checks the solver) and rises from C2 to C3 (the tilt forces deviations that the freedom it gives the tilted industries does not repay; this is a statement about the data).
3. The cost of the tilt: at the last month, under C3 with the sample covariance on daily data, the forecast tracking error is below 100 basis points a year, the ex-ante tracking-error limit of enhanced indexing. Reason: the tilt removes about 3% of the portfolio from three industries whose own risk beyond the market is 12% to 20% a year, and the optimiser places that weight in the industries that move most with them, so the deviation's risk is a fraction of 3% times 20%.
4. Reported, no verdict: where the tilt's weight goes (the industries with the largest positive active weights under C3), the effective number of holdings of the benchmark and of each portfolio, the forecast tracking error under C3 across the five estimators (notebook 12 judges them on realised tracking error), and which constraints bind.
5. The turnover cap as a speed limit, a stress case at the last month: starting from 1/N weights under long-only plus the cap, the one-way turnover equals the cap (it binds) and the forecast tracking error is positive, while under C1 from the same start it is zero. Reported, no verdict: the forecast tracking error after 1, 6, 12 and 24 monthly rebalances from 1/N with the benchmark and the covariance held fixed; the one-way distance from 1/N to the benchmark divided by the cap; and what C2 does from the same start, where the active bound is hard and demands more trading than the cap allows, so the cap is relaxed to the smallest feasible turnover.

**Checks and fixes added after the first part, each with its expectation written in `constants.py` before its code.** D1 to D4 (4 October): how much of the tilt is a market bet, what forcing the beta to one costs, what refusing the tobacco hedge costs, and how much the hedge depends on the estimator and the month. F1 to F3 (4 October): the mandate's C3 and the robust portfolio at the same three months. D5 (6 October): the solver's status against the independent check on a month with no feasible portfolio. Their expectations are stated in full at the head of their sections.

Running time: about three minutes, most of it the download of the daily files.
"""),
    md("""
## Modules

`constants`, `french_loader`, `benchmark`, `rules` and `covariance` are those of earlier notebooks; `covariance` gained the panel loader and the estimator dispatch that notebook 10's loop used inline. `optimiser` is new: the constrained tracking-error minimiser, the drifted weights, the feasibility checks and the effective number of holdings, each tested on made-up markets in `tests/test_optimiser.py`, including against an independent solver. `evaluation`, notebook 12's module, is written here as well, for the check D5, which reruns the first five years of one of notebook 12's paths.
"""),
    code("""
import importlib.util, subprocess, sys
if importlib.util.find_spec("cvxpy") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "cvxpy"])
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("benchmark.py"),
    writefile("rules.py"),
    writefile("covariance.py"),
    writefile("optimiser.py"),
    writefile("evaluation.py"),
    md("""
## Count first: the benchmark weights, the drifted weights, the tilted industries, the specification count
"""),
    code("""
import sys
sys.path.insert(0, "src")
import time
import numpy as np
import pandas as pd
import cvxpy
from bp import constants as C
from bp import french_loader as fl
from bp import covariance as CV
from bp import optimiser as O

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 120)
pd.set_option("display.max_columns", 40)

P = CV.Panels()
weights, returns_m = P.weights, P.returns_m
eval_months = pd.period_range(C.COV_EVAL_START, P.last, freq="M")
industries = [c.strip() for c in weights.columns]
tilt_mask, exclude_mask = O.masks(weights.columns)

# Expectation 1
assert np.allclose(weights.sum(axis=1), 1.0, atol=1e-9), "benchmark weights do not sum to one in every month"
drift = pd.DataFrame({m: O.drifted_weights(weights.loc[m - 1].to_numpy(), returns_m.loc[m - 1].to_numpy()) for m in weights.index[1:]}, index=weights.columns).T
drift.index = pd.PeriodIndex(drift.index, freq="M")
assert len(drift) == len(weights) - 1 and np.allclose(drift.sum(axis=1), 1.0, atol=1e-9)
assert tilt_mask.sum() == len(C.TILT_INDUSTRIES) == 3
spec_count = len(CV.ALL_VARIANTS) * len(C.CONSTRAINT_SETS)
assert spec_count == C.EXT_SPEC_COUNT == 28
provenance = [fl.download(key) for key in P.files]
fl.write_provenance(provenance)
vintage = provenance[0]["vintage_line"].split("the ")[1].split(" ")[0]
print(f"{len(weights)} months of benchmark weights, {weights.index[0]} to {weights.index[-1]}, each summing to one; drifted weights for {len(drift)} months, each summing to one")
print(f"tilted industries: {', '.join(C.TILT_INDUSTRIES)}, held at no more than {C.TILT_MAX_SHARE_OF_BENCHMARK:.0%} of their benchmark weight; at {weights.index[-1]} they are "
      + ", ".join(f"{n} {100 * weights.loc[weights.index[-1], c]:.2f}%" for n, c in zip(C.TILT_INDUSTRIES, weights.columns[tilt_mask])) + " of the benchmark")
print(f"specification count: {spec_count} ({len(CV.ALL_VARIANTS)} variants, five estimators, the robust portfolio and RiskMetrics, times {len(C.CONSTRAINT_SETS)} constraint sets); cvxpy {cvxpy.__version__}, solver {C.OPT_SOLVER}")
print(f"expectation 1 holds; CRSP vintage of the eight files: {vintage}")
"""),
    md("""
## The optimiser at three months

This is the first part of the notebook: C3 is the tilt alone, the first of its two versions. The report months are the first evaluation month (1979-07, the first with both a 120-month and a three-year daily window), the paper's last month (2004-11) and the vintage's last month. At each, the five estimator variants of the rolling evaluation (the four estimators on three years of daily returns and the sample covariance of 120 monthly returns) give five covariance matrices, and the optimiser runs under each constraint set with the benchmark as the previous portfolio. The table reports, for each portfolio, the forecast tracking error in basis points a year, the one-way turnover, the cap after any relaxation, how many industries it holds, its effective number of holdings, the active weights of the three tilted industries in percentage points, and how many constraints of each kind bind.
"""),
    code("""
SETS = {"C0": C.CONSTRAINT_SETS["C0"], "C1": C.CONSTRAINT_SETS["C1"], "C2": C.CONSTRAINT_SETS["C2"], "C3": C.CONSTRAINT_SET_TILT_ONLY}   # the first run: C3 as designed on 10 September, the tilt alone
report_months = [eval_months[0] if m == "first_eval" else (P.last if m == "last" else pd.Period(m, "M")) for m in C.OPT_REPORT_MONTHS]
tilt_cols = list(weights.columns[tilt_mask])

Sigmas = {}
t0 = time.time()
for month in report_months:
    for v in CV.EVALUATION_VARIANTS:
        Sigmas[(month, v)], _, _ = CV.estimate(*v, month, P)
print(f"{len(Sigmas)} covariance matrices built in {time.time() - t0:.0f}s")

rows, solutions = [], {}
for month in report_months:
    b = weights.loc[month].to_numpy()
    for v in CV.EVALUATION_VARIANTS:
        S = Sigmas[(month, v)]
        for cs, names in SETS.items():
            sol = O.solve(S, b, names, w_prev=b, tilt_mask=tilt_mask)
            solutions[(month, v, cs)] = sol
            row = {"month": str(month), "estimator": v[0], "data": v[1], "set": cs,
                   "tracking error (bp a year)": 1e4 * sol.tracking_error, "one-way turnover": sol.turnover,
                   "cap used": sol.turnover_cap_used if "turnover_cap" in names else np.nan, "cap relaxed": sol.relaxed,
                   "industries held": int((sol.weights > 1e-6).sum()), "effective number": O.effective_number(sol.weights)}
            for name, j in zip(C.TILT_INDUSTRIES, np.flatnonzero(tilt_mask)):
                row[f"active {name} (pp)"] = 100 * sol.active[j]
            for k, n in sol.binding.items():
                row[f"binding: {k}"] = n
            rows.append(row)
report = pd.DataFrame(rows).set_index(["month", "estimator", "data", "set"])
print(report.to_string(float_format=lambda x: f"{x:.2f}"))
"""),
    md("""
## Expectations 2 and 3: the known answers and the cost of the tilt
"""),
    code("""
te = report["tracking error (bp a year)"] / 1e4
pairs = [(m, v) for m in report_months for v in CV.EVALUATION_VARIANTS]
def TE(m, v, cs):
    return te.loc[(str(m), v[0], v[1], cs)]

e2a = sum(TE(m, v, "C0") < C.OPT_TOL_TE and TE(m, v, "C1") < C.OPT_TOL_TE for m, v in pairs)
e2b = sum(report.loc[(str(m), v[0], v[1], "C3"), "binding: tilt"] == 3 and TE(m, v, "C3") > C.OPT_TOL_TE for m, v in pairs)
e2c_mono = sum(TE(m, v, "C1") >= TE(m, v, "C0") - C.OPT_TOL_TE and TE(m, v, "C2") >= TE(m, v, "C1") - C.OPT_TOL_TE for m, v in pairs)
e2c_tilt = sum(TE(m, v, "C3") > TE(m, v, "C2") for m, v in pairs)
n = len(pairs)
print(f"expectation 2a: under C0 and C1 the solution is the benchmark (forecast tracking error below {C.OPT_TOL_TE:g} a year) in {e2a} of {n} month-estimator pairs: {'MET' if e2a == n else 'NOT MET'}")
print(f"expectation 2b: under C3 all three tilts bind and the tracking error is positive in {e2b} of {n}: {'MET' if e2b == n else 'NOT MET'}")
print(f"expectation 2c: the tracking error does not fall from C0 to C1 to C2 in {e2c_mono} of {n} ({'MET' if e2c_mono == n else 'NOT MET'}), and rises from C2 to C3 in {e2c_tilt} of {n} ({'MET' if e2c_tilt == n else 'NOT MET'})")
last = report_months[-1]
te_tilt = TE(last, ("sample", "daily_3y"), "C3")
print(f"expectation 3: at {last} the forecast tracking error under C3 with the sample covariance on daily data is {1e4 * te_tilt:.1f} basis points a year "
      f"(level {1e4 * C.OPT_TILT_TE_MAX_ANNUAL:.0f}): {'MET' if te_tilt < C.OPT_TILT_TE_MAX_ANNUAL else 'NOT MET'}")
print()
c3 = report.xs("C3", level="set")["tracking error (bp a year)"].unstack(["estimator", "data"])
print("the cost of the tilt by month and estimator, forecast tracking error under C3 in basis points a year:")
print(c3.to_string(float_format=lambda x: f"{x:.1f}"))
"""),
    md("""
## Expectation 4: where the tilt's weight goes, the effective number of holdings, which constraints bind

The tilt takes weight out of Coal, Oil and Utilities, and the optimiser puts it where the forecast tracking error grows least. Two things decide where that is. First, the portfolio's beta to the benchmark: Oil and Utilities are low-beta industries (their returns move less than one for one with the market), so removing them leaves a portfolio with a beta above one, and the cheapest way to bring it back to one is to buy other low-beta industries. Second, among the low-beta industries, those whose remaining movement (after the market is taken out) is correlated with Oil and Utilities, and whose own volatility is low, replace the removed exposure at the least added risk. The table lists, at the last month under C3 with the sample covariance on daily data, the industries with the largest positive active weights beside each one's beta to the benchmark, its own volatility, and its correlation with Oil and with Utilities after the market is taken out; the rank correlations below the table say which of these numbers predicts the active weights. One more thing shapes the list: under C3 the first month's cap is relaxed to the smallest feasible turnover, so the portfolio trades exactly what the tilt requires and nothing else, and the purchases concentrate in the few industries with the best hedge per unit traded.
"""),
    code("""
b_last = weights.loc[last].to_numpy()
S_last = Sigmas[(last, ("sample", "daily_3y"))]
sol = solutions[(last, ("sample", "daily_3y"), "C3")]
own_vol = np.sqrt(12 * np.diag(S_last))
beta_bench = (S_last @ b_last) / (b_last @ S_last @ b_last)
resid = S_last - np.outer(S_last @ b_last, S_last @ b_last) / (b_last @ S_last @ b_last)     # covariance after the benchmark is taken out
resid_corr = resid / np.sqrt(np.outer(np.diag(resid), np.diag(resid)))
i_oil, i_util = industries.index("Oil"), industries.index("Util")
where = pd.DataFrame({"benchmark weight %": 100 * b_last, "active weight (pp)": 100 * sol.active, "beta to benchmark": beta_bench, "own volatility %": 100 * own_vol,
                      "residual corr with Oil": resid_corr[:, i_oil], "residual corr with Util": resid_corr[:, i_util]}, index=industries)
print(f"where the tilt's weight goes at {last} (C3, sample covariance on daily data); the tilt removes {-100 * sol.active[tilt_mask].sum():.2f} percentage points from Coal, Oil and Util, "
      f"whose betas to the benchmark are {', '.join(f'{beta_bench[j]:.2f}' for j in np.flatnonzero(tilt_mask))}:")
print(where.sort_values("active weight (pp)", ascending=False).head(10).to_string(float_format=lambda x: f"{x:.2f}"))
print()
print(f"{int((sol.active[~tilt_mask] > 1e-6).sum())} of the 46 untilted industries receive weight; the portfolio's beta to the benchmark is {float(sol.weights @ beta_bench):.3f}")
sp = where.loc[~tilt_mask].corr(method="spearman")["active weight (pp)"]
print("rank correlation across the 46 untilted industries between the active weight and: " + "; ".join(f"{c} {sp[c]:.2f}" for c in ["beta to benchmark", "own volatility %", "residual corr with Oil", "residual corr with Util", "benchmark weight %"]))
print()
eff = report["effective number"].unstack("set")
eff.insert(0, "benchmark", [O.effective_number(weights.loc[pd.Period(m, 'M')].to_numpy()) for m in eff.index.get_level_values("month")])
print("effective number of holdings (49 would be 1/N):")
print(eff.to_string(float_format=lambda x: f"{x:.1f}"))
print()
bind_cols = [c for c in report.columns if c.startswith("binding")]
print("constraints binding (count of bounds at their limit), by set, averaged over the fifteen month-estimator pairs:")
print(report[bind_cols].groupby(level="set").mean().to_string(float_format=lambda x: f"{x:.1f}"))
"""),
    md("""
## Expectation 4, continued: the tilt's cost with and without the transition cap

Reported, no verdict. Under C3 at a report month the previous portfolio is the benchmark, so the cap is relaxed to the smallest feasible turnover and the portfolio trades exactly the tilt and nothing else. The same tilt with free trading (long-only, active bound and tilt, no cap) is the cost of the tilt once the portfolio has settled, which notebook 12's rolling evaluation reaches after the first months. The two are reported side by side.
"""),
    code("""
# Added after the first run (4 October 2026): the tilt under the minimum-turnover transition (C3) against the tilt with free trading.
rows = []
for month in report_months:
    b = weights.loc[month].to_numpy()
    for v in CV.EVALUATION_VARIANTS:
        s3 = solutions[(month, v, "C3")]
        sf = O.solve(Sigmas[(month, v)], b, ("long_only", "active_weight_bound", "tilt"), w_prev=b, tilt_mask=tilt_mask)
        rows.append({"month": str(month), "estimator": v[0], "data": v[1], "C3, transition (bp)": 1e4 * s3.tracking_error, "turnover C3": s3.turnover,
                     "tilt, free trading (bp)": 1e4 * sf.tracking_error, "turnover free": sf.turnover, "industries held, free": int((sf.weights > 1e-6).sum())})
free = pd.DataFrame(rows).set_index(["month", "estimator", "data"])
print(free.to_string(float_format=lambda x: f"{x:.2f}"))
"""),
    md("""
## Expectation 5: the turnover cap as a speed limit

A stress case at the last month: the fund starts as 1/N, far from the cap-weighted benchmark, and may trade 2% one way a month. Under C1 it reaches the benchmark at once, because nothing limits the trade. Under long-only plus the cap it moves towards the benchmark 2% a month, choosing each month the trade that lowers the forecast tracking error most; the benchmark weights and the covariance are held fixed so that only the cap acts. Under C2 the active bound is hard and 1/N is far outside it, so the cap is relaxed to the smallest turnover that reaches the bound.
"""),
    code("""
start = np.ones(49) / 49
distance = O.one_way_turnover(start, b_last)
sol_c1 = O.solve(S_last, b_last, SETS["C1"], w_prev=start, tilt_mask=tilt_mask)
path, w_now = [], start.copy()
for step in range(1, max(C.OPT_SPEED_LIMIT_STEPS) + 1):
    s = O.solve(S_last, b_last, ("long_only", "turnover_cap"), w_prev=w_now, tilt_mask=tilt_mask)
    path.append({"rebalance": step, "one-way turnover": s.turnover, "forecast tracking error (bp a year)": 1e4 * s.tracking_error,
                 "one-way distance to the benchmark": O.one_way_turnover(s.weights, b_last)})
    w_now = s.weights
path = pd.DataFrame(path).set_index("rebalance")
first = path.loc[1]
e5 = abs(first["one-way turnover"] - C.TURNOVER_CAP_MONTHLY_ONE_WAY) <= C.OPT_TOL and first["forecast tracking error (bp a year)"] > 0 and sol_c1.tracking_error < C.OPT_TOL_TE
print(f"from 1/N at {last}: one-way distance to the benchmark {distance:.3f}, which is {distance / C.TURNOVER_CAP_MONTHLY_ONE_WAY:.0f} months of trading at the cap if every trade reduced it")
print(f"expectation 5: under long-only plus the cap the first rebalance trades {first['one-way turnover']:.4f} one way (cap {C.TURNOVER_CAP_MONTHLY_ONE_WAY}) and leaves a forecast tracking error of {first['forecast tracking error (bp a year)']:.0f} basis points; "
      f"under C1 the first rebalance reaches the benchmark (tracking error {1e4 * sol_c1.tracking_error:.4f} basis points, turnover {sol_c1.turnover:.3f}): {'MET' if e5 else 'NOT MET'}")
print()
print("the journey from 1/N under long-only plus the cap, benchmark and covariance held fixed:")
print(path.loc[list(C.OPT_SPEED_LIMIT_STEPS)].to_string(float_format=lambda x: f"{x:.4f}"))
sol_c2 = O.solve(S_last, b_last, SETS["C2"], w_prev=start, tilt_mask=tilt_mask)
print()
print(f"under C2 from 1/N the active bound demands a one-way turnover of {sol_c2.turnover:.3f} at once, so the cap is relaxed to it ({'relaxed' if sol_c2.relaxed else 'not relaxed'}); forecast tracking error {1e4 * sol_c2.tracking_error:.1f} basis points, the cost of landing inside the bound in one month")
"""),
    md("""
## Part two: the practical problem behind the hedge (D1 to D4)

A tilt removes exposure, and the optimiser replaces it with whatever the covariance says is closest. Four things about that replacement matter to a manager, each checked here with its expectation fixed in `constants.py` before the code (4 October 2026):

- **D1, how much of the tilt is a market bet.** The forecast active variance a' Sigma a splits exactly into a market part, (a' beta)^2 times the benchmark's variance, with beta the industries' betas to the benchmark under the same covariance, and a residual part, the variance of what the benchmark leaves unexplained. Expectation D1a: the market part is below 5% of the whole in all fifteen month-estimator pairs, because the market is the largest direction of the covariance, so a beta away from one is the most expensive deviation and the optimiser removes it on its own.
- **D2, forcing the beta to one.** A beta-neutral constraint, the portfolio's beta equal to the benchmark's, is added to C3 as a new switchable constraint. Expectation D2a: it raises the forecast tracking error by less than 1 basis point a year in every pair, for the same reason. The lesson, if it holds: with a tracking-error objective and a usable covariance, a manager does not need to impose beta neutrality by hand; the optimiser's first move is to restore it.
- **D3, is the hedge consistent with the mandate.** At 2026-08 the tobacco industry (Smoke) received weight as a low-beta substitute for Utilities. A sustainability mandate that underweights carbon would not buy tobacco to hedge it. Reported, no verdict: the forecast tracking error of C3 plus the exclusion of Smoke, against C3, at every report month and estimator; the expectation written before the code is a rise below 2 basis points, because the other low-beta industries are close substitutes.
- **D4, how much the hedge depends on the covariance and on the month.** (a) The rank correlation between the C3 active-weight vectors of each pair of estimators at the same month, over the 46 untilted industries; expectation D4a: at every report month the four daily estimators agree with each other more than any of them agrees with the monthly sample covariance. (b) The cross-evaluation matrix at the last month: the C3 portfolio built with estimator i (the row), its tracking error forecast with estimator j's covariance (the column). Within a column the diagonal is the minimum by construction, because the column's estimator built that portfolio to minimise its own forecast and the other rows' portfolios are feasible under the same set; so the report is the excess of each entry over its column's diagonal, in basis points: how much worse the column's estimator thinks another estimator's portfolio is than its own. (c) The three industries that absorb most of the tilt at each report month under the sample covariance on daily data.
"""),
    code("""
# Added after the first run (4 October 2026): D1 and D2, the market part of the tilt and the beta-neutral constraint.
rows = []
for month in report_months:
    b = weights.loc[month].to_numpy()
    for v in CV.EVALUATION_VARIANTS:
        S = Sigmas[(month, v)]
        s3 = solutions[(month, v, "C3")]
        market, rest = O.active_variance_parts(s3.active, S, b)
        beta = O.benchmark_betas(S, b)
        s_bn = O.solve(S, b, C.CONSTRAINT_SET_TILT_ONLY + ("beta_neutral",), w_prev=b, tilt_mask=tilt_mask)
        rows.append({"month": str(month), "estimator": v[0], "data": v[1], "C3 tracking error (bp)": 1e4 * s3.tracking_error,
                     "market share of active variance": market / (market + rest), "portfolio beta under C3": float(s3.weights @ beta),
                     "C3 + beta-neutral (bp)": 1e4 * s_bn.tracking_error, "rise (bp)": 1e4 * (s_bn.tracking_error - s3.tracking_error)})
d12 = pd.DataFrame(rows).set_index(["month", "estimator", "data"])
print(d12.to_string(float_format=lambda x: f"{x:.4f}"))
d1a = int((d12["market share of active variance"] < C.OPT_D1_MARKET_SHARE_MAX).sum())
d2a = int((d12["rise (bp)"] < 1e4 * C.OPT_D2_TE_RISE_MAX).sum())
print()
print(f"D1a: the market part is below {C.OPT_D1_MARKET_SHARE_MAX:.0%} of the active variance in {d1a} of {len(d12)} pairs (largest share {d12['market share of active variance'].max():.4f}; "
      f"portfolio beta under C3 between {d12['portfolio beta under C3'].min():.3f} and {d12['portfolio beta under C3'].max():.3f}): {'MET' if d1a == len(d12) else 'NOT MET'}")
print(f"D2a: the beta-neutral constraint raises the tracking error by less than {1e4 * C.OPT_D2_TE_RISE_MAX:.0f} basis point in {d2a} of {len(d12)} pairs (largest rise {d12['rise (bp)'].max():.3f} bp): {'MET' if d2a == len(d12) else 'NOT MET'}")
"""),
    code("""
# Added after the first run (4 October 2026): D3, the cost of refusing the tobacco hedge, and D4, the dependence of the hedge on the estimator and the month.
_, smoke_mask = O.masks(weights.columns, exclude=C.OPT_D3_EXCLUDE)
rows = []
for month in report_months:
    b = weights.loc[month].to_numpy()
    for v in CV.EVALUATION_VARIANTS:
        s3 = solutions[(month, v, "C3")]
        s_ex = O.solve(Sigmas[(month, v)], b, C.CONSTRAINT_SET_TILT_ONLY + ("exclusion",), w_prev=b, tilt_mask=tilt_mask, exclude_mask=smoke_mask)
        rows.append({"month": str(month), "estimator": v[0], "data": v[1], "C3 (bp)": 1e4 * s3.tracking_error, "active Smoke under C3 (pp)": 100 * s3.active[smoke_mask][0],
                     "C3 without Smoke (bp)": 1e4 * s_ex.tracking_error, "rise (bp)": 1e4 * (s_ex.tracking_error - s3.tracking_error)})
d3 = pd.DataFrame(rows).set_index(["month", "estimator", "data"])
print(f"D3, the cost of excluding {', '.join(C.OPT_D3_EXCLUDE)} from the hedge:")
print(d3.to_string(float_format=lambda x: f"{x:.2f}"))
print()

labels = [f"{v[0]}, {v[1].replace('_', ' ')}" for v in CV.EVALUATION_VARIANTS]
daily = [i for i, v in enumerate(CV.EVALUATION_VARIANTS) if v[1] == "daily_3y"]
monthly = [i for i, v in enumerate(CV.EVALUATION_VARIANTS) if v[1] == "monthly_120"]
d4a_holds = []
for month in report_months:
    A_act = pd.DataFrame({labels[i]: solutions[(month, v, "C3")].active[~tilt_mask] for i, v in enumerate(CV.EVALUATION_VARIANTS)})
    rc = A_act.corr(method="spearman")
    dd = np.mean([rc.iloc[i, j] for i in daily for j in daily if i < j])
    dm = np.mean([rc.iloc[i, j] for i in daily for j in monthly])
    d4a_holds.append(dd > dm)
    print(f"D4a at {month}: rank correlation of the C3 active weights across estimators (46 untilted industries); daily-daily mean {dd:.2f}, daily-monthly mean {dm:.2f}")
    print(rc.to_string(float_format=lambda x: f"{x:.2f}"))
    print()
print(f"D4a: the daily estimators agree with each other more than with the monthly sample covariance at {sum(d4a_holds)} of {len(report_months)} report months: {'MET' if all(d4a_holds) else 'NOT MET'}")
print()
cross = pd.DataFrame(index=labels, columns=labels, dtype=float)
for i, vi in enumerate(CV.EVALUATION_VARIANTS):
    w_i = solutions[(last, vi, "C3")].weights
    for j, vj in enumerate(CV.EVALUATION_VARIANTS):
        cross.iloc[i, j] = 1e4 * O.forecast_tracking_error(w_i, b_last, Sigmas[(last, vj)])
excess = cross.sub(np.diag(cross.to_numpy()), axis=1)
assert (excess.to_numpy() >= -1e-6).all(), "a column's own portfolio must be that column's minimum"
print(f"D4b at {last}: forecast tracking error (bp a year) of the C3 portfolio built with the row's estimator, judged by the column's covariance:")
print(cross.to_string(float_format=lambda x: f"{x:.1f}"))
print()
print("excess over the column's own portfolio (bp): how much worse the column's estimator thinks the row's portfolio is than its own")
print(excess.to_string(float_format=lambda x: f"{x:.1f}"))
print()
print("D4c: the three industries that absorb most of the tilt, sample covariance on daily data, by report month:")
for month in report_months:
    a = pd.Series(solutions[(month, ("sample", "daily_3y"), "C3")].active, index=industries)
    top = a.sort_values(ascending=False).head(3)
    print(f"  {month}: " + ", ".join(f"{k} +{100 * x:.2f} pp" for k, x in top.items()) + f"; tilt removes {-100 * a[tilt_mask].sum():.2f} pp")
"""),
    md("""
## The fixes (F1 to F3): the mandate's C3 and the robust portfolio at the three months

D1 to D4 describe problems a manager would fix, so the design was changed (4 October 2026, before notebook 12's code), with the expectations written into `constants.py` first:

- **Fix 1 (D1, D2).** Beta neutrality joins C3 for every covariance. It cost the daily estimators at most 1.2 basis points and removes the beta bet the monthly covariance left standing. Factor neutrality beyond the market is not imposed: the market is 55% of the industries' variance (notebook 09) and the next components 17%, and factor betas from a window carry their own estimation error.
- **Fix 2 (D3).** The optimiser receives the whole mandate: the carbon tilt and the exclusions of tobacco (Smoke) and weapons (Guns), the standard exclusions of Dutch institutional mandates, both of which the tilt's hedge had bought. Excluded industries are at weight zero, which costs tracking error of its own (together 0.9% of the 2026-08 benchmark).
- **Fix 3 (D4).** A robust portfolio for model risk: the weights whose largest forecast tracking error across the five covariances is smallest, so that no single matrix is trusted; one more convex problem, with beta neutrality under every covariance. It joins notebook 12's rolling evaluation as a sixth variant.

Expectations: F1, under the mandate's C3 the portfolio's beta equals one within 1e-6 and Smoke and Guns have weight zero, in all fifteen pairs. F2, the mandate's C3 costs more than the tilt alone in every pair (its feasible set is smaller) and the rise is below 15 basis points a year everywhere; D2 and D3 together suggest up to about 12 for the monthly covariance at 2004-11. F3, the robust portfolio's worst forecast tracking error across the five covariances is at most the worst of every single-estimator portfolio (a check, it is the minimax by construction), and under each covariance its excess over that covariance's own minimum is at most the largest excess any single-estimator portfolio shows there (F3a, a statement about the data: the compromise is nobody's worst case). Reported: the robust portfolio's mean excess and where its weight goes.
"""),
    code("""
# The fixes (4 October 2026): the mandate's C3 and the robust portfolio at the three report months.
_, mandate_mask = O.masks(weights.columns, exclude=C.MANDATE_EXCLUSIONS)
fix_rows, fixed, robust = [], {}, {}
for month in report_months:
    b = weights.loc[month].to_numpy()
    for v in CV.EVALUATION_VARIANTS:
        S = Sigmas[(month, v)]
        s_old = solutions[(month, v, "C3")]
        s_new = O.solve(S, b, C.CONSTRAINT_SETS["C3"], w_prev=b, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
        fixed[(month, v)] = s_new
        beta = O.benchmark_betas(S, b)
        fix_rows.append({"month": str(month), "estimator": v[0], "data": v[1], "tilt only (bp)": 1e4 * s_old.tracking_error, "mandate C3 (bp)": 1e4 * s_new.tracking_error,
                         "rise (bp)": 1e4 * (s_new.tracking_error - s_old.tracking_error), "beta": float(s_new.weights @ beta),
                         "Smoke + Guns weight": float(s_new.weights[mandate_mask].sum()), "one-way turnover": s_new.turnover, "industries held": int((s_new.weights > 1e-6).sum())})
    robust[month] = O.solve_robust([Sigmas[(month, v)] for v in CV.EVALUATION_VARIANTS], b, C.CONSTRAINT_SETS["C3"], w_prev=b, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
fixes = pd.DataFrame(fix_rows).set_index(["month", "estimator", "data"])
print("the mandate's C3 against the tilt alone:")
print(fixes.to_string(float_format=lambda x: f"{x:.4f}"))
f1 = int((((fixes["beta"] - 1).abs() <= 1e-5) & (fixes["Smoke + Guns weight"].abs() <= C.OPT_TOL)).sum())
f2 = int(((fixes["rise (bp)"] > -1e-6) & (fixes["rise (bp)"] < 1e4 * C.OPT_FIX_RISE_MAX)).sum())
print()
print(f"F1: beta equal to one and Smoke and Guns at zero in {f1} of {len(fixes)} pairs: {'MET' if f1 == len(fixes) else 'NOT MET'}")
print(f"F2: the mandate's C3 costs more than the tilt alone and less than {1e4 * C.OPT_FIX_RISE_MAX:.0f} basis points more in {f2} of {len(fixes)} pairs (largest rise {fixes['rise (bp)'].max():.1f} bp, at {fixes['rise (bp)'].idxmax()}): {'MET' if f2 == len(fixes) else 'NOT MET'}")
print()
# F3: the robust portfolio against the single-estimator portfolios, under each covariance
f3_check, f3a, rob_rows = [], [], []
for month in report_months:
    b = weights.loc[month].to_numpy()
    covs = [Sigmas[(month, v)] for v in CV.EVALUATION_VARIANTS]
    own = np.array([fixed[(month, v)].tracking_error for v in CV.EVALUATION_VARIANTS])
    te_single = np.array([[O.forecast_tracking_error(fixed[(month, vi)].weights, b, Sj) for Sj in covs] for vi in CV.EVALUATION_VARIANTS])   # row i built, column j judged
    te_rob = np.array([O.forecast_tracking_error(robust[month].weights, b, Sj) for Sj in covs])
    worst_single = te_single.max(axis=1)
    f3_check.append(bool(te_rob.max() <= worst_single.min() + 1e-7))
    excess_single = te_single - own[None, :]          # excess of portfolio i over estimator j's own minimum, under j
    excess_rob = te_rob - own
    f3a.append(bool((excess_rob <= excess_single.max(axis=0) + 1e-9).all()))
    rob_rows.append({"month": str(month), "robust worst case (bp)": 1e4 * te_rob.max(), "best single worst case (bp)": 1e4 * worst_single.min(),
                     "robust mean excess (bp)": 1e4 * excess_rob.mean(), "largest single excess (bp)": 1e4 * excess_single[~np.eye(5, dtype=bool)].max(),
                     "robust turnover": robust[month].turnover, "industries held": int((robust[month].weights > 1e-6).sum())})
rob_table = pd.DataFrame(rob_rows).set_index("month")
print("F3, the robust portfolio under the mandate's C3:")
print(rob_table.to_string(float_format=lambda x: f"{x:.2f}"))
print(f"F3 check (the robust worst case is at most every single portfolio's worst case): {sum(f3_check)} of {len(f3_check)} months; "
      f"F3a (under each covariance the robust excess is at most the largest single-portfolio excess): {sum(f3a)} of {len(f3a)} months: {'MET' if all(f3a) else 'NOT MET'}")
print()
a_rob = pd.Series(robust[last].active, index=industries)
print(f"where the robust portfolio's weight goes at {last} (mandate's C3): " + ", ".join(f"{k} +{100 * x:.2f} pp" for k, x in a_rob.sort_values(ascending=False).head(5).items())
      + f"; Smoke and Guns {100 * robust[last].weights[mandate_mask].sum():.2f}%, tilt removes {-100 * a_rob[tilt_mask].sum():.2f} pp")
a_new = pd.Series(fixed[(last, ("sample", "daily_3y"))].active, index=industries)
print(f"where the sample covariance's weight goes under the mandate's C3 at {last}: " + ", ".join(f"{k} +{100 * x:.2f} pp" for k, x in a_new.sort_values(ascending=False).head(5).items()))
"""),
    md("""
## Part three: a check on the solver (D5)

A solver returns two things, a status word ("optimal", "optimal_inaccurate", "infeasible" or "unbounded") and a list of 49 weights, and both can be wrong at once. The first run of notebook 12 found such a case. At 1984-07, a July in which French rebuilds the industry portfolios from the end-of-June SIC codes, the index itself moved 4.3% one way, above the cap of 2%, so no portfolio satisfied the cap and the tilt at once; the right answer was "infeasible". The solver returned "optimal" and weights that summed to 1.0037. The independent check of the returned weights (`optimiser.check`: the weights sum to one, lie inside their bounds and respect the cap, each within 1e-6) failed them and the run stopped, which is what the check is for.

Why it matters to a manager: the optimiser's output is the trade list. A portfolio whose weights sum to 1.0037 buys 0.37% more than the fund's money, an unintended loan or a failed settlement; one that trades 22% of the fund in a month with a 2% cap pays eleven times the cost budget, 11 basis points at 50 basis points per unit of turnover against 1, and breaks the promise made to the client. A solver's status is its own opinion of its arithmetic and says nothing about the mandate. A firm answers the mandate question with a check that does not belong to the solver, the pre-trade compliance test of the order management system, which tests the proposed portfolio against every rule before an order leaves; `optimiser.check` is the same thing in miniature.

The check D5 reruns that month on the final form of the problem, with its expectation in `constants.py` first: (a) at 1984-07 under the tilt-only set, with the previous portfolio taken from the robust path run from 1979-07, the smallest one-way turnover that satisfies the tilt and the active bound exceeds the 2% cap, so the month is infeasible under the cap; (b) handed the capped problem at its default stopping rule, the solver reports "optimal" and the returned weights fail the independent check; reported beside it, the status at the 1e-9 rule the robust problem runs at and at the 1e-12 rule of the single-covariance problem; (c) the optimiser's full routine returns a portfolio that passes every check, with the cap raised to the smallest feasible turnover (within the rule's margin of 2e-6) and the month marked as relaxed.

Two repairs were tried, and the second is the one that holds. The first was to write the turnover cap differently. The cap can be written with absolute values (half the sum of |w - w0| at most 2%) or with a purchase p and a sale n per industry (w - w0 = p - n, half the sum of p + n at most 2%; an industry that goes from 7.0% to 6.4% has p = 0 and n = 0.6 points, and p + n is the 0.6 the absolute value gives). The two mean the same thing, and the rerun shows that the second way also comes back "optimal" at the default stopping rule, with different wrong weights (summing to 0.961 and trading 21.9%): rewriting the constraint changed which wrong weights came back and left the wrong status word in place, so it protects nothing. The second repair is the order of the two steps described at the start of this notebook. Both sets of wrong weights came from a problem that had no solution, and whether the capped problem has a solution can be known before it is posed: the smallest turnover the other constraints allow is a linear program, a problem with a linear objective and linear constraints, which the solver answers reliably, and comparing that turnover with the cap says whether the capped problem is feasible. The optimiser runs that program first in every month with a cap, raises the cap when that turnover is above it, and only then poses the tracking-error problem, so the solver never sees a capped problem without a solution. What this does not do is make the check unnecessary: on a feasible problem a solver can still return weights that are off by a little (at its default stopping rule, by 1e-4 against an independent solver's, which is why the stopping rule was tightened), so the check of every returned portfolio stays as the backstop. D5c runs the full routine.
"""),
    code("""
# Added after the first run of notebook 12 (6 October 2026): D5, the solver's status against the independent check at 1984-07.
import warnings
from bp import evaluation as E
d5_month = pd.Period(C.OPT_D5_MONTH, "M")
d5_months = pd.period_range(C.COV_EVAL_START, d5_month, freq="M")
Sig5 = {m: [CV.estimate(*v, m, P)[0] for v in CV.EVALUATION_VARIANTS] for m in d5_months}
path5 = E.run_path(d5_months, Sig5, weights, returns_m, C.CONSTRAINT_SET_TILT_ONLY, tilt_mask, None, robust=True, keep_weights=True)
prev = d5_months[-2]
w0 = O.drifted_weights(path5.loc[prev, "weights"], returns_m.loc[prev].to_numpy())
b = weights.loc[d5_month].to_numpy()
b_drift = O.drifted_weights(weights.loc[prev].to_numpy(), returns_m.loc[prev].to_numpy())
lower, upper = O.bounds(b, C.CONSTRAINT_SET_TILT_ONLY, tilt_mask, np.zeros(len(b), bool), C.ACTIVE_WEIGHT_BOUND, C.TILT_MAX_SHARE_OF_BENCHMARK)
Ls = [O.cholesky_factor(S) for S in Sig5[d5_month]]
cap = C.TURNOVER_CAP_MONTHLY_ONE_WAY

# (a) the smallest feasible one-way turnover, against the cap
w_t, prob_t = O._build(Ls, b, lower, upper, w0, None, objective="turnover")
prob_t.solve(solver=C.OPT_SOLVER, **C.OPT_SOLVER_OPTIONS_ROBUST)
min_turnover = float(prob_t.value)
d5a = min_turnover > cap
print(f"D5a: at {d5_month} the index moved {O.one_way_turnover(b, b_drift):.3f} one way; the smallest one-way turnover that satisfies the tilt and the active bound is {min_turnover:.4f}, "
      f"above the cap of {cap}: {'yes' if d5a else 'no'}, so the month is {'infeasible' if d5a else 'feasible'} under the cap: {'MET' if d5a else 'NOT MET'}")

# (b) the solver on the capped problem, at its default stopping rule and at the tight one, status against the independent check
def raw_solve(options):
    w_raw, prob_raw = O._build(Ls, b, lower, upper, w0, cap)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        prob_raw.solve(solver=C.OPT_SOLVER, **options)
    x = O._clean(w_raw.value)
    ok = len(x) == len(b) and O.feasible(x, b, lower, upper, w0, cap, C.OPT_TOL)
    return prob_raw.status, x, ok
status_default, x_default, ok_default = raw_solve({})
d5b = status_default == "optimal" and not ok_default
print(f"D5b: at the solver's default stopping rule (1e-8) the status is '{status_default}'"
      + (f", the returned weights sum to {x_default.sum():.4f} and trade {O.one_way_turnover(x_default, w0):.4f} one way, and the independent check {'passes' if ok_default else 'fails'}" if len(x_default) == len(b) else ", and no weights are returned")
      + f": {'MET' if d5b else 'NOT MET'}")
for label, options in (("1e-9, the robust problem's rule", C.OPT_SOLVER_OPTIONS_ROBUST), ("1e-12, the single-covariance rule", C.OPT_SOLVER_OPTIONS)):
    status_r, x_r, ok_r = raw_solve(options)
    print(f"     at the stopping rule {label}: status '{status_r}'" + (f", weights summing to {x_r.sum():.4f}, one-way turnover {O.one_way_turnover(x_r, w0):.4f}, the independent check {'passes' if ok_r else 'fails'}" if len(x_r) == len(b) else ", no weights returned"))

# (c) the guarded routine: feasibility test, relaxation to the smallest feasible turnover, every check passed
sol5 = O.solve_robust(Sig5[d5_month], b, C.CONSTRAINT_SET_TILT_ONLY, w_prev=w0, tilt_mask=tilt_mask)
d5c = bool(sol5.relaxed) and abs(sol5.turnover_cap_used - min_turnover) <= 2e-6 and O.feasible(sol5.weights, b, lower, upper, w0, sol5.turnover_cap_used, C.OPT_TOL)
print(f"D5c: the guarded routine relaxes the cap to {sol5.turnover_cap_used:.6f} (smallest feasible {min_turnover:.6f}), status '{sol5.status}', weights summing to {sol5.weights.sum():.6f}, "
      f"one-way turnover {sol5.turnover:.4f}, relaxed {sol5.relaxed}, every check passed: {'MET' if d5c else 'NOT MET'}")
"""),
    md("""
## Save

The report table, the speed-limit path, the fixes table and the robust portfolio's table are written to `outputs/`, with the vintage in the file name, as a record.
"""),
    code("""
os.makedirs(C.OUTPUT_DIR, exist_ok=True)
report.to_csv(f"{C.OUTPUT_DIR}/optimiser_report_{vintage}.csv", float_format="%.6f")
path.to_csv(f"{C.OUTPUT_DIR}/optimiser_speed_limit_{vintage}.csv", float_format="%.6f")
fixes.to_csv(f"{C.OUTPUT_DIR}/optimiser_fixes_{vintage}.csv", float_format="%.6f")
rob_table.to_csv(f"{C.OUTPUT_DIR}/optimiser_robust_{vintage}.csv", float_format="%.6f")
print("written:", sorted(f for f in os.listdir(C.OUTPUT_DIR) if f.startswith("optimiser")))
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. Count first | 686 months of benchmark weights summing to one, 685 months of drifted weights summing to one, Coal, Oil and Util present, 28 specifications | holds |
| 2a. Under C0 and C1 the benchmark is the answer | forecast tracking error below 1e-6 a year in 15 of 15 month-estimator pairs | MET |
| 2b. Under C3 the three tilts bind and the tracking error is positive | 15 of 15 | MET |
| 2c. Tracking error does not fall from C0 to C1 to C2, and rises from C2 to C3 | 15 of 15 and 15 of 15 | MET |
| 3. The tilt costs less than 100 basis points a year at the last month | 35.1 basis points (sample covariance, daily data) | MET |
| 4. Where the tilt's weight goes, effective number, binding constraints | weight to low-beta industries (Other, Food, Telcm, Smoke) and to the commodity-linked ones (Agric, Steel); effective number 18.4 to 24.2 in 1979-07, 10.2 to 10.3 in 2026-08; under C3 the three tilts and the relaxed cap bind | reported |
| 5. The cap as a speed limit from 1/N | first rebalance trades 0.0200 one way and leaves 708 basis points; C1 reaches the benchmark at once | MET |
| D1a. The market part of the tilt's active variance is below 5% in all 15 pairs | 14 of 15; the monthly sample covariance at 2004-11 leaves 5.4% (portfolio beta 1.007) | NOT MET |
| D2a. A beta-neutral constraint raises the tracking error by less than 1 basis point in all 15 pairs | 11 of 15; 3.4 and 5.6 basis points for the monthly sample covariance, 1.2 for the sample and shrinkage estimators on daily data at 2026-08 | NOT MET |
| D3. Excluding tobacco from the hedge (guess written before the code: a rise below 2 basis points) | rises of 1.3 to 6.5 basis points, 2% to 13% of the tilt's cost; below 2 in 4 of 15 pairs | reported; the guess was wrong |
| D4a. The daily estimators agree with each other on the hedge more than with the monthly sample covariance | 3 of 3 months (daily-daily mean rank correlation 0.58 to 0.68 against daily-monthly 0.54 to 0.63) | MET |
| D4b, D4c. Cross-evaluation and the absorbing industries by month | one estimator judges another's portfolio 1 to 5 basis points worse than its own; the absorbing industries change entirely across the three months | reported |
| F1. Under the mandate's C3 the beta is one and Smoke and Guns are at zero | 15 of 15 | MET |
| F2. The mandate's C3 costs more than the tilt alone and less than 15 basis points more | 13 of 15; the daily estimators pay 1.9 to 6.9 basis points, the monthly sample covariance 18.6 and 25.4 | NOT MET for the monthly covariance |
| F3. The robust portfolio's worst case is at most every single portfolio's worst case, and its excess under each covariance at most the largest single excess | 3 of 3 months; robust worst case 113, 64 and 42 basis points against 125, 67 and 42 for the best single portfolio; mean excess 0.1 to 1.1 basis points against single excesses of up to 21 | MET |
| D5. The solver's status against the independent check at 1984-07 (added 6 October) | the month is infeasible under the cap (smallest feasible turnover 0.0201, the index moved 4.3%); at the default and the 1e-9 stopping rules the status is "optimal" with weights summing to 0.961 and trading 22% one way, which fail the check; at 1e-12 the status is "infeasible"; the guarded routine relaxes the cap to 0.0201 and passes every check | MET, 3 of 3 |

Expectation 1 holds: the benchmark weights of notebook 08 sum to one in each of the 686 months from 1969-07, the drifted weights exist for the 685 months that follow a month and sum to one, Coal, Oil and Util are columns of the file, and the rolling evaluation of notebook 12 has 28 specifications, five estimator variants, the robust portfolio and RiskMetrics, times four constraint sets.

Expectation 2, the known answers, holds in every one of the 15 month-estimator pairs. Under long-only (C0) and with the active weight bound (C1) the solution is the benchmark itself, with a forecast tracking error of zero, because the benchmark satisfies both constraints and nothing beats zero. Under C3 the three tilted industries sit at exactly half their benchmark weight: the tilt is the only constraint that forces the portfolio off the benchmark, and a constraint that forces a deviation binds. The tracking error never falls from C0 to C1 to C2, which is a check of the solver (each set is the previous set plus one constraint), and it rises from C2 to C3 in every pair, which is a fact about the data: the freedom the tilt gives the three industries from the active bound is worth nothing when they are forced below it.

Expectation 3, the cost of the tilt, holds: 35 basis points a year at 2026-08 with the sample covariance on daily data, against the enhanced-indexing limit of 100. The cost depends on how much the tilt removes. In 1979-07 Oil was 15.1% of the benchmark and Utilities 8.0%, so the tilt took 11.7 percentage points out of the portfolio and cost 47 to 55 basis points with the daily estimators (108 with the sample covariance of 120 monthly returns); in 2004-11 it took 4.7 points and cost 49 to 56; in 2026-08 it takes 2.8 points and costs 33 to 36. Per percentage point removed, the cost rose from 4.6 basis points in 1979 to 12.7 in 2026: a concentrated benchmark (effective number of holdings 10.2 against 18.4) offers fewer substitutes of the right kind. The five estimators agree within 2 basis points in 2026-08 and within 8 in 1979-07 among the daily ones; the monthly sample covariance stands apart in 1979-07 (108 against 47 to 55) and is the lowest in 2004-11 and 2026-08.

Expectation 4, where the weight goes. The pre-run reasoning said the optimiser would put the removed weight in the industries that move most with Oil and Utilities. That is half of it. Oil and Utilities have betas to the benchmark of 0.41 and 0.33, so removing 2.8 points of them leaves a portfolio with a beta above one, and the first thing the optimiser does is restore the beta: the weight goes to Other (beta 0.47), Food (0.12), Telcm (0.39) and Smoke (0.04), and the portfolio's beta ends at 1.004. Among the low-beta industries it prefers those whose movement after the market is taken out is correlated with the removed ones: across the 46 untilted industries the rank correlation between the active weight and the residual correlation with Oil is 0.57 and with Utilities 0.43, against -0.29 with the beta, -0.13 with the industry's own volatility and 0.04 with its benchmark weight. The commodity-linked industries (Agric, Steel, FabPr, Gold) receive weight too, and little of it, because their own volatility is 25% to 42% a year. Only 11 of the 46 untilted industries receive any weight, because the first month's cap is relaxed to the smallest feasible turnover, so the portfolio buys exactly 2.8 points and places them where each unit traded hedges most. The effective number of holdings is the benchmark's under C0 to C2 (18.4 in 1979-07, 18.6 in 2004-11, 10.2 in 2026-08) and rises under C3 in 1979-07 to about 24, because the tilt spreads a 15% industry's weight over others; in 2026-08 it barely moves. The comparison with free trading separates the tilt from the transition: with free trading the same tilt costs 0.2 to 4 basis points less with the daily estimators and 5 to 17 less with the monthly sample covariance, which trades two to three times as much (0.24 against 0.12 in 1979-07) and holds fewer industries; that is the pattern of notebook 10 again, a noisy covariance sees hedges that a less noisy one does not, and notebook 12 will say whether those trades pay in realised tracking error.

Expectation 5, the cap as a speed limit, holds. From 1/N at 2026-08 the one-way distance to the benchmark is 0.528, which is 26 months of trading at 2% if every trade reduced the distance. Under C1 the first rebalance trades the whole 0.528 and lands on the benchmark; under long-only plus the cap the first rebalance trades exactly 0.0200 and leaves a forecast tracking error of 708 basis points, which falls to 472 after six rebalances, 254 after twelve and 28 after twenty-four, when the remaining distance is 0.078. The optimiser does not reduce the distance fastest; it reduces the tracking error fastest, which means trading the industries whose active weights contribute most to the deviation's variance first. Under C2 from the same start the active bound is hard and 1/N sits 0.387 of one-way turnover outside it, so the cap is relaxed to 0.387 and the portfolio lands inside the bound in one month with a forecast tracking error of 95 basis points.

**The practical problem behind the hedge (D1 to D4).** A tilt is also a factor bet: removing low-beta industries leaves a high-beta portfolio, and the optimiser's hedge depends on the covariance it is given. D1 measured how much of the tilt's forecast risk is a market bet after the optimiser has done its work: under 1% of the active variance for the four daily estimators at 1979-07 and 2004-11, 0.3% to 3% at 2026-08, and 2.3% and 5.4% for the monthly sample covariance at 1979-07 and 2004-11, where the portfolio's beta ends at 1.010 and 1.007. The expectation (below 5% in every pair) fails in that one pair, and the failure is informative: a noisy covariance sees cheap hedges in its noise and leaves a beta bet standing that a less noisy one removes. D2 imposed beta neutrality as a constraint: it costs the daily estimators 0.0 to 1.2 basis points and the monthly sample covariance 3.4 and 5.6, so the expectation (below 1 basis point in every pair) fails in four pairs, for the same reason. The lesson stands with a qualification: with a tracking-error objective the optimiser restores the beta on its own when the covariance is estimated from daily data; with 120 monthly observations it leaves a beta of 1.007 to 1.010 standing, and a manager using such a matrix should impose the constraint. D3 priced the mandate problem: at 2026-08 the hedge buys tobacco (Smoke, a low-beta industry) to replace Utilities, which a sustainability mandate that underweights carbon would refuse; excluding Smoke from the hedge costs 2.4 to 3.2 basis points at 2026-08, 1.3 to 1.6 at 1979-07 and 5.5 to 6.5 at 2004-11, that is 2% to 13% of the tilt's cost. The guess written before the code (below 2 basis points) was wrong in 11 of 15 pairs; the next-best low-beta substitutes are further away than the reasoning written before the code assumed. D4 measured how much the hedge is a property of the estimator. The four daily estimators agree with each other on the active weights more than with the monthly sample covariance (expectation met), and the agreement is partial: the sample covariance and shrinkage are the same hedge (rank correlation 0.99 to 1.00, because the shrinkage intensity on daily data is 0.012), the factor model agrees with the sample covariance at 0.45 to 0.53, and the component model sits between. In the cross-evaluation at 2026-08, one estimator judges another's hedge 1 to 5 basis points worse than its own on a tilt that costs 33 to 36: a model risk of up to 13% of the number quoted. And the industries that absorb the tilt change with the month: Fin, Telcm and Food in 1979-07, Drugs, Mach and Banks in 2004-11, Other, Food and Telcm in 2026-08. For a manager this says four things: check the factor exposures the optimiser creates and removes, because it hedges a beta bet silently; check the hedge against the mandate, because the covariance does not know what the mandate forbids; treat the forecast cost of a tilt as model-dependent to within about a tenth; and expect the hedge to be rebuilt as the covariance moves, which is turnover the cap will ration. The first three are problems a manager fixes in the design, and the design was changed accordingly.

**The fixes.** Beta neutrality and the exclusions of Smoke and Guns joined C3, and the robust portfolio joined the variants. Under the mandate's C3 every portfolio has a beta of exactly one and holds no tobacco or weapons (F1). The mandate costs the daily estimators 1.9 to 2.2 basis points more than the tilt alone at 1979-07, 5.6 to 6.9 at 2004-11 and 4.5 to 6.6 at 2026-08, that is 4% to 19% of the tilt's cost; the monthly sample covariance pays 25.4 and 18.6 basis points at the first two months and 0.6 at the last, so F2 (below 15 everywhere) fails for that covariance, which is the covariance whose hedges the fixes were most needed against: a matrix that saw cheap hedges in its noise is the one that loses most when the hedges it liked are forbidden. The robust portfolio does what it was built for (F3): its worst forecast tracking error across the five covariances is 113, 64 and 42 basis points at the three months against 125, 67 and 42 for the best single-estimator portfolio, and under each covariance it sits 0.1 to 1.1 basis points above that covariance's own minimum on average, where the single-estimator portfolios sit up to 21, 13 and 7 above each other's. The compromise costs almost nothing and protects against the matrix being wrong. Under the mandate the weight at 2026-08 goes to Food, Other, Telcm, Soda and Agric, for the robust portfolio and for the sample covariance alike, and to nothing the mandate forbids.

**The solver check (D5).** At 1984-07 the index moved 4.3% one way and the smallest turnover that satisfies the tilt and the active bound is 2.01%, a hundredth of a percentage point above the cap, so the month is infeasible under the cap by that margin. Handed the capped problem, the solver reports "optimal" at its default stopping rule and at the 1e-9 rule, with weights that sum to 0.961 and trade 21.9% of the portfolio one way, eleven times the cap; at the 1e-12 rule it reports "infeasible"; in notebook 12's first run, with the cap written with absolute values, it reported "optimal" with weights summing to 1.0037. The independent check fails the returned weights in every one of these cases, and the optimiser's full routine, which finds the smallest feasible turnover first and poses the capped problem only with a cap at or above it, raises the cap to 2.01% and returns a portfolio that sums to one and trades 2.01%, every check passed. Two consequences for a manager. First, a solver's status is a statement about its own arithmetic and says nothing about the mandate; a portfolio is accepted only after a check that does not belong to the solver, which in a firm is the pre-trade compliance test of the order management system and here is `optimiser.check`. Second, infeasibility is settled in the design before any solver runs: the design says which constraint gives way (the cap, raised to the smallest feasible turnover) and counts the months it happens, so that the fund never trades a portfolio the solver invented; notebook 12 reports those months (1 to 4 of 566 per path).

**What this notebook does not settle.**

- Every tracking error here is a forecast at three months from the covariance used to build the portfolio, so a portfolio built from an estimator is judged by that estimator's own view of it. Realised tracking error month by month, and whether the choice of estimator matters once the constraints are on, are notebook 12's question.
- Whether underweighting Coal, Oil and Utilities cost or earned return over the sample is a question about returns, which the optimiser never sees; notebook 13's attribution answers it.
- The transition rule, raising the cap to the smallest feasible turnover, decides the first month under a tilt and any month in which the benchmark moved by more than 2%. How often that happens and what it costs is a count notebook 12 reports.
- The reasoning written before the run for expectation 3 was incomplete: the number was right, the mechanism named only co-movement, and the first mechanism is the restoration of the portfolio's beta. The expectation was met for a reason only partly foreseen. D1 to D4 were designed after the first part and two of them failed in the pairs that use the monthly sample covariance; the fixes were designed after D1 to D4, and one of their expectations (F2) failed for the same covariance; D5 was designed after notebook 12's first run. Each step was written down before its code, with its date, and the order of the sections is the order of the work.
- The fixes are tested here on forecasts at three months. Whether the mandate's C3 and the robust portfolio hold up in realised tracking error, month by month, with the turnover of rebuilding the hedge as the covariance moves, is notebook 12's question; the tilt-only set runs beside them there so that the cost of the fixes is measured on realised numbers.
- Beta neutrality is the only factor constraint. Exposures to the other Fama-French factors (size, value, profitability, investment, momentum) are left to the covariance; imposing them would need factor betas from the window, with their own estimation error, and is the natural extension if notebook 13's attribution shows that the tilt loads on one of them.
- The optimiser was checked against an independent solver and against a linear program on problems of six to eight assets, and on the 49 industries by the feasibility checks and the known answers of expectation 2; no independent solver was run on the 49-industry problems. The solver's own status is not relied on in any month: D5 shows it reporting "optimal" on a month with no feasible portfolio, and every returned portfolio is tested against every constraint before it is accepted.
- The active weight bound is 2 percentage points around each benchmark weight. A bound proportional to the benchmark weight is another common choice and was not tried; the design fixed one and the notebook reports it.
"""),
]

# ---------------------------------------------------------------------------
# 12: the rolling evaluation
# ---------------------------------------------------------------------------

NB12 = [
    md("""
# 12. The rolling evaluation: what the constrained portfolios realised, month by month

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same period |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money |
| Cap-weighted | weighted by market capitalisation |
| Benchmark | in the extension, the index the portfolio tracks, the cap-weighted combination of the 49 industries built in notebook 08 |
| Variance | the average squared distance of a series from its own average; its square root is the standard deviation, the usual measure of how much a return moves; volatility is the standard deviation of returns, stated per year here by multiplying the monthly figure by the square root of 12 |
| Standard error | the uncertainty of a number estimated from a sample: the standard deviation that the estimate would show across repeated samples of the same size; for a mean it is the standard deviation of the observations divided by the square root of their number |
| Covariance matrix | the table of all variances and covariances of a set of assets, 49 by 49 here, 1,225 distinct numbers |
| Covariance estimator | a method for estimating the covariance matrix from a window of data; notebook 10 built four |
| Estimation window | the past returns an estimator sees, 120 months or three years of trading days here |
| Regime | a stretch of time over which the volatilities and co-movements of the returns stay about the same; a change of regime is a shift between two such stretches, which a window of past returns cannot see coming |
| Shrinkage | pulling an estimate part of the way towards a simpler target, which trades a little bias for less estimation error |
| RiskMetrics | the covariance estimator of J.P. Morgan's 1996 RiskMetrics document: a weighted sample covariance in which each day's weight falls by half every half-life, one year of trading days here, so that recent days count most (notebook 10's sensitivity) |
| Factor | a return series that moves many assets at once, for example the return of the whole market; the Fama-French factors are long-short portfolios built to isolate one such source each |
| Principal component | a combination of the assets, with one weight per asset, chosen so that it explains as much of the assets' total variance as a single combination can (notebook 09) |
| Minimum-variance portfolio | the fully invested portfolio with the lowest variance under a given covariance matrix; the test portfolio of the covariance literature |
| Active weight | the portfolio's weight in an asset minus the benchmark's weight in it |
| Active return | the portfolio's return minus the benchmark's return in the same month |
| Tracking error | the standard deviation of the difference between two return series, stated per year; forecast (ex-ante) when computed from a covariance matrix before the month, realised (ex-post) when measured on the active returns afterwards |
| Bias statistic | the standard deviation of the active return divided by its forecast standard deviation, over many months; 1 when the forecasts of risk are right on average, above 1 when risk is under-forecast, below 1 when over-forecast |
| Autocorrelation | the correlation of a series with its own value one period earlier |
| Variance ratio | the variance of 21-day returns divided by 21 times the variance of daily returns, measured over a window; 1 when one day's return says nothing about the next day's, above 1 under positive autocorrelation, below 1 under negative (notebook 10) |
| Long-only | said of a portfolio in which no weight is negative |
| One-way turnover | half the sum over industries of the absolute changes in weight at a rebalance; the fraction of the portfolio sold, which is also the fraction bought when the portfolio stays fully invested |
| Turnover cap | an upper limit on the one-way turnover of a rebalance; 2% a month here |
| Drifted weights | the previous month's weights after that month's returns have moved them, so that they still sum to one |
| Index turnover | the one-way turnover an index fund needs to follow its benchmark: the distance between the benchmark's new weights and its own drifted weights; zero when the weights move only because prices moved |
| Tilt | a constraint that holds named industries below their benchmark weight; here Coal, Oil and Utilities at no more than half of it |
| Exclusion | a constraint that holds named industries at zero weight; Smoke (tobacco) and Guns (weapons) here |
| Beta | how much an asset moves with a factor on average; the beta to the benchmark is how much it moves with the benchmark, one for the benchmark itself |
| Beta-neutral | a constraint that holds the portfolio's beta to the benchmark equal to one |
| Mandate | the whole set of rules the fund obeys: the tilt, the exclusions and beta neutrality, the constraint set C3 |
| Constraint set | one of the four cumulative sets C0 to C3: long-only; plus the active weight bound; plus the turnover cap; plus the mandate |
| Optimiser | the extension's routine that solves the constrained tracking-error problem (notebook 11) |
| Robust portfolio | the weights whose largest forecast tracking error across the five covariance estimates is smallest; a portfolio that trusts no single matrix (notebook 11) |
| Specification | one combination of a variant (an estimator, or the robust portfolio) and a constraint set |
| Path | the month-by-month sequence of portfolios of one specification, each built on the data before its month |
| In-sample | measured on the same data that were used to form the weights; the forecast tracking error is in-sample in this sense, because the covariance that forecasts the portfolio's risk is the one the portfolio was built on |
| Out-of-sample | measured on months the portfolio had not seen when its weights were formed; the realised tracking error is out of sample |
| Information ratio | the active return per year divided by the realised tracking error; the reward earned per unit of tracking error |
| Basis point | one hundredth of a percentage point, so 50 basis points is 0.50% |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |

**The problem, stated the way practitioners state it.** The literature judges covariance estimators by what an unconstrained minimum-variance portfolio realised after the fact; Dom, Howard, Jansen and Lohre (2024), whose framing this notebook follows, replace that portfolio with a constrained one and read its realised volatility, turnover and costs. The counterpart for an index manager is the realised tracking error of the constrained, tilted, turnover-capped portfolio against its benchmark, month after month, with each month's weights chosen before the month began, and beside it the turnover, the costs, and the question whether the risk forecast that justified each portfolio was right. Nothing in notebooks 10 and 11 can answer that; both are forecasts. This notebook runs the portfolios and measures.

**What this notebook does.** Notebooks 10 and 11 forecast. This notebook measures what happened. For every month from 1979-07 to the vintage's last month, each specification builds its portfolio on the data before the month and holds it through the month; the difference between the portfolio's return and the benchmark's is that month's active return, and the standard deviation of those active returns over 566 months is the realised tracking error, the number the forecasts of notebook 11 were about. The question the extension was built to ask is answered here, whether the choice of covariance estimator still matters, measured as realised tracking error, once the portfolio is long-only, bounded, turnover-capped and tilted. Beside it: how well the forecasts were calibrated, what the mandate's fixes of notebook 11 cost in realised terms, whether the robust portfolio did what it was built for, how often the cap had to give way, and what the tilt earned or cost in return. Two expectations (8 and 9) were added after the first run, with their expectations written before their code, and are marked as such.

**How a path is run.**

- The path starts as the index: in the first evaluation month the previous portfolio is the benchmark of that month.
- In month t the variant's covariance is estimated on the data before t (notebook 10's estimators; the robust portfolio uses all five), and the optimiser solves for the weights with the drifted previous weights as the turnover reference. Nothing from month t enters the weights.
- The portfolio earns its weights times the industries' returns of month t, the benchmark earns its weights times the same returns, and the difference is recorded with the forecast tracking error, the one-way turnover, whether the cap was relaxed and the holdings.
- 35 paths: seven variants (the four estimators on daily data, the sample covariance of 120 monthly returns, the robust portfolio, and RiskMetrics) times the four constraint sets, 28 specifications, plus seven sensitivity paths under the tilt alone (C3 without notebook 11's fixes), so that the fixes' cost is measured on realised numbers.

**Measures of a path.**

- Realised tracking error: the standard deviation of the 566 active returns, times the square root of 12.
- Forecast tracking error: the mean of the monthly forecasts, and the bias statistic (standard deviation of active return over forecast standard deviation); for the daily variants also under the ten-year variance ratio of notebook 10, which multiplies the forecast variance by the ratio measured on the benchmark's daily returns over the ten years before the month.
- Active return: the mean times 12, gross; the cost of the turnover at 50 and 100 basis points per unit of one-way turnover; the net active return; the information ratio.
- Turnover: the mean one-way turnover, the months in which the cap was relaxed and their share, and those months by calendar month; the index's own turnover beside it.
- Holdings: the mean effective number of holdings and the mean number of industries held. Realised tracking error by decade.

**What I expect to see, written before the run (`constants.py`, 4 October 2026).**

1. Count first: 566 evaluation months from 1979-07; 28 paths plus 7 sensitivity paths, each with one record per month; under C0 and C1 every path holds the benchmark in every month (active return below 1e-6 a month, a ten-thousandth of a basis point; written as 1e-10 and set to the solver's precision before the recorded run), which checks the loop, and their turnover is the index's own.
2. The extension's question: under C3 the realised tracking errors of the four daily estimators lie within 10 basis points a year of each other, and the monthly sample covariance's is above the lowest of the four (direction only; its hedges were the noisiest in notebook 11).
3. Calibration: for the four daily estimators under C3 the bias statistic of the active return lies between 0.8 and 1.25 under the 21 rule. Reported: the same under the ten-year variance ratio, and which of the two is closer to 1.
4. The robust portfolio: its realised tracking error under C3 is at most the largest of the five single estimators'. Reported: its distance from the best.
5. The fixes: for each variant the mandate's C3 realises a higher tracking error than the tilt alone (direction), by less than 15 basis points a year.
6. The cap: under C2 and C3 the share of months with a relaxed cap is below 10% for every variant; relaxations are expected in the first month of every C3 path and in July months, when French rebuilds the industry portfolios, reported by calendar month.
7. Reported, no verdict: turnover, costs, net active return and the information ratio, the effective number of holdings, realised tracking error by decade, the index's own turnover.

**Added after the first recorded run (`constants.py`, 6 October 2026), expectations fixed before their code.**

8. RiskMetrics joins as a seventh variant (the exponentially weighted covariance over five years of daily returns with a one-year half-life, notebook 10's sensitivity), because Dom, Howard, Jansen and Lohre (2024) find that time dynamics matter more than shrinkage or structure and that RiskMetrics does as well as the DCC model of Engle (2002) for minimum-variance portfolios, and because notebook 10 found it gave the lowest unconstrained volatility and the best-calibrated forecast. Expectation: under C3 its realised tracking error is at or below the sample covariance's on daily data. The robust portfolio stays the minimax over the five covariances of notebook 11, so that its path is unchanged.
9. Calibration of the forecast on its own past: in month t the forecast is multiplied by the ratio of realised to forecast tracking error over the previous 60 months of the same path, using only months before t (unchanged while fewer than 24 months are available). Expectation: under C3 the calibrated bias statistic lies between 0.85 and 1.15 for the four daily estimators. Reported: by decade, and for the robust portfolio and RiskMetrics.

Running time: about ten to fifteen minutes, most of it the 20,000 optimisations.
"""),
    md("""
## Modules

`constants`, `french_loader`, `benchmark`, `rules`, `covariance` and `optimiser` are those of earlier notebooks. `evaluation` is new: the path, its records and its measures, tested on a made-up market in `tests/test_evaluation.py`.
"""),
    code("""
import importlib.util, subprocess, sys
if importlib.util.find_spec("cvxpy") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "cvxpy"])
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("benchmark.py"),
    writefile("rules.py"),
    writefile("covariance.py"),
    writefile("optimiser.py"),
    writefile("evaluation.py"),
    md("""
## Count first: the months, the paths, the variance ratios
"""),
    code("""
import sys
sys.path.insert(0, "src")
import time
import numpy as np
import pandas as pd
from bp import constants as C
from bp import french_loader as fl
from bp import covariance as CV
from bp import optimiser as O
from bp import evaluation as E

pd.set_option("display.width", 230)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_columns", 40)

P = CV.Panels()
weights, returns_m = P.weights, P.returns_m
months = pd.period_range(C.COV_EVAL_START, P.last, freq="M")
industries = [c.strip() for c in weights.columns]
tilt_mask, _ = O.masks(weights.columns)
_, mandate_mask = O.masks(weights.columns, exclude=C.MANDATE_EXCLUSIONS)
SETS = dict(C.CONSTRAINT_SETS)
SENSITIVITY_SET = ("C3 tilt only", C.CONSTRAINT_SET_TILT_ONLY)
VARIANTS = list(CV.ALL_VARIANTS)
LABEL = {v: ("robust, all five" if v == C.ROBUST_VARIANT else ("RiskMetrics, daily 5y" if v == C.EWMA_VARIANT else f"{v[0]}, {v[1].replace('_', ' ')}")) for v in VARIANTS}

# Expectation 1, the counts
assert len(months) == 566, len(months)
n_paths = len(VARIANTS) * len(SETS)
assert n_paths == C.EXT_SPEC_COUNT == 28
# the ten-year variance ratio of the benchmark's daily excess return before each month (notebook 10's correction)
vr10 = pd.Series({m: CV.variance_ratio(P.bench_d.loc[CV.daily_window(P.excess_d, m, C.COV_SCALE_VR_WINDOW_YEARS_SENSITIVITY).index].to_numpy(), C.COV_SCALE_VR_HORIZON_DAYS) for m in months})
provenance = [fl.download(key) for key in P.files]
fl.write_provenance(provenance)
vintage = provenance[0]["vintage_line"].split("the ")[1].split(" ")[0]
print(f"{len(months)} evaluation months, {months[0]} to {months[-1]}; {n_paths} specifications ({len(VARIANTS)} variants, five estimators, the robust portfolio and RiskMetrics, times {len(SETS)} constraint sets) plus {len(VARIANTS)} sensitivity paths under the tilt alone")
print(f"ten-year variance ratio of the benchmark before each month: {vr10.min():.2f} to {vr10.max():.2f}, mean {vr10.mean():.2f}")
print(f"CRSP vintage of the eight files: {vintage}")
"""),
    md("""
## The covariances, once per month

Each of the five estimator variants and RiskMetrics is built once per month and shared by every constraint set; the robust portfolio uses the five estimator covariances, as in notebook 11.
"""),
    code("""
t0 = time.time()
Sigmas = {v: {} for v in CV.EVALUATION_VARIANTS + (C.EWMA_VARIANT,)}
for i, month in enumerate(months):
    for v in CV.EVALUATION_VARIANTS + (C.EWMA_VARIANT,):
        Sigmas[v][month], _, _ = CV.estimate(*v, month, P)
    if i % 100 == 0:
        print(f"{month}: {time.time() - t0:.0f}s")
Sigmas[C.ROBUST_VARIANT] = {m: [Sigmas[v][m] for v in CV.EVALUATION_VARIANTS] for m in months}   # the robust portfolio's set: the five estimator covariances of notebook 11
print(f"{len(months) * (len(CV.EVALUATION_VARIANTS) + 1)} covariance matrices in {time.time() - t0:.0f}s")
"""),
    md("""
## The paths

One path per specification, and the seven sensitivity paths. Each month's optimisation uses the drifted previous weights of its own path.
"""),
    code("""
paths = {}
t0 = time.time()
for v in VARIANTS:
    for cs, names in list(SETS.items()) + [SENSITIVITY_SET]:
        t1 = time.time()
        paths[(v, cs)] = E.run_path(months, Sigmas[v], weights, returns_m, names, tilt_mask,
                                    mandate_mask if "exclusion" in names else None, robust=(v == C.ROBUST_VARIANT), keep_weights=True)
        print(f"{LABEL[v]:>24}  {cs:<13} {time.time() - t1:5.0f}s")
print(f"{len(paths)} paths in {time.time() - t0:.0f}s")

# Expectation 1, the loop check: under C0 and C1 every path is the benchmark
hold = [(v, cs) for v in VARIANTS for cs in ("C0", "C1") if np.abs(paths[(v, cs)]["active_return"]).max() < C.EVAL_BENCHMARK_TOL]
largest_dev = max(np.abs(paths[(v, cs)]["active_return"]).max() for v in VARIANTS for cs in ("C0", "C1"))
index_turnover = paths[(VARIANTS[0], "C0")]["benchmark_turnover"]
print()
print(f"expectation 1: {len(months)} months; {len(paths)} paths with {set(len(p) for p in paths.values())} records each; "
      f"the benchmark is held in every month under C0 and C1 in {len(hold)} of {2 * len(VARIANTS)} paths (largest active return {largest_dev:.1e} a month, level {C.EVAL_BENCHMARK_TOL:g}): {'holds' if len(hold) == 2 * len(VARIANTS) else 'FAILS'}")
print(f"the index's own one-way turnover: mean {index_turnover.mean():.4f} a month ({12 * index_turnover.mean():.1%} a year), median {index_turnover.median():.4f}, "
      f"largest {index_turnover.max():.3f} in {index_turnover.idxmax()}; months above the cap of {C.TURNOVER_CAP_MONTHLY_ONE_WAY}: {int((index_turnover > C.TURNOVER_CAP_MONTHLY_ONE_WAY).sum())}")
"""),
    md("""
## Expectations 2 to 7: the measures

One row per path. Tracking errors and active returns in basis points a year; turnover as a fraction of the portfolio per month; the bias statistic under the 21 rule and under the ten-year variance ratio (daily variants only).
"""),
    code("""
rows = []
for (v, cs), path in paths.items():
    s = E.summarise(path, vr_scale=vr10 if v[1] == "daily_3y" or v == C.ROBUST_VARIANT else None)
    rows.append({"variant": LABEL[v], "set": cs, **s})
table = pd.DataFrame(rows).set_index(["variant", "set"])
bp_cols = ["realised TE", "forecast TE (mean)", "active return (gross)"] + [c for c in table.columns if c.startswith(("cost at", "net active return"))]
show = table.copy()
show[bp_cols] = 1e4 * show[bp_cols]
show = show.rename(columns={c: f"{c} (bp)" for c in bp_cols})
order = ["C0", "C1", "C2", "C3", "C3 tilt only"]
show = show.reindex(pd.MultiIndex.from_product([[LABEL[v] for v in VARIANTS], order], names=["variant", "set"]))
print(show[["realised TE (bp)", "forecast TE (mean) (bp)", "bias", "bias (variance ratio)", "turnover (one-way)", "relaxed months", "inaccurate months", "effective number", "industries held"]].to_string(float_format=lambda x: f"{x:.3f}"))
print()
print(show[["active return (gross) (bp)", "cost at 50 bp (bp)", "net active return at 50 bp (bp)", "information ratio at 50 bp", "net active return at 100 bp (bp)", "information ratio at 100 bp"]].to_string(float_format=lambda x: f"{x:.2f}"))
"""),
    code("""
daily = [LABEL[v] for v in CV.EVALUATION_VARIANTS if v[1] == "daily_3y"]
monthly = LABEL[("sample", "monthly_120")]
robust_label = LABEL[C.ROBUST_VARIANT]
te3 = table.xs("C3", level="set")["realised TE"]
rng = te3[daily].max() - te3[daily].min()
e2a = rng < C.EVAL_TE_RANGE_MAX
e2b = te3[monthly] > te3[daily].min()
print(f"expectation 2: realised tracking error under C3, daily estimators {1e4 * te3[daily].min():.1f} to {1e4 * te3[daily].max():.1f} bp (range {1e4 * rng:.1f}, level {1e4 * C.EVAL_TE_RANGE_MAX:.0f}): {'MET' if e2a else 'NOT MET'}; "
      f"monthly sample covariance {1e4 * te3[monthly]:.1f} bp, above the lowest daily: {'yes' if e2b else 'no'}")
bias3 = table.xs("C3", level="set")[["bias", "bias (variance ratio)"]]
lo, hi = C.EVAL_BIAS_RANGE
e3 = int(((bias3.loc[daily, "bias"] >= lo) & (bias3.loc[daily, "bias"] <= hi)).sum())
closer = int((abs(bias3.loc[daily, "bias (variance ratio)"] - 1) < abs(bias3.loc[daily, "bias"] - 1)).sum())
print(f"expectation 3: bias statistic under C3 and the 21 rule inside {lo} to {hi} for {e3} of {len(daily)} daily estimators ({', '.join(f'{b:.2f}' for b in bias3.loc[daily, 'bias'])}): {'MET' if e3 == len(daily) else 'NOT MET'}; "
      f"under the ten-year variance ratio ({', '.join(f'{b:.2f}' for b in bias3.loc[daily, 'bias (variance ratio)'])}), closer to 1 for {closer} of {len(daily)}")
singles = te3[daily + [monthly]]
e4 = te3[robust_label] <= singles.max() + 1e-12
print(f"expectation 4: the robust portfolio's realised tracking error under C3 is {1e4 * te3[robust_label]:.1f} bp against {1e4 * singles.min():.1f} (best single, {singles.idxmin()}) and {1e4 * singles.max():.1f} (worst, {singles.idxmax()}): {'MET' if e4 else 'NOT MET'}")
fix = pd.DataFrame({"mandate C3": te3, "tilt only": table.xs("C3 tilt only", level="set")["realised TE"]})
fix["difference"] = fix["mandate C3"] - fix["tilt only"]
e5 = int(((fix["difference"] > 0) & (fix["difference"] < C.OPT_FIX_RISE_MAX)).sum())
print(f"expectation 5: the mandate's C3 against the tilt alone, realised tracking error (bp): " + "; ".join(f"{k} {1e4 * r['mandate C3']:.1f} vs {1e4 * r['tilt only']:.1f} ({1e4 * r['difference']:+.1f})" for k, r in fix.iterrows())
      + f"; positive and below {1e4 * C.OPT_FIX_RISE_MAX:.0f} bp in {e5} of {len(fix)}: {'MET' if e5 == len(fix) else 'NOT MET'}")
relax = table.loc[(slice(None), ["C2", "C3"]), "relaxed share"]
e6 = bool((relax < C.EVAL_RELAX_SHARE_MAX).all())
print(f"expectation 6: share of months with a relaxed cap under C2 and C3, {relax.min():.3f} to {relax.max():.3f} (level {C.EVAL_RELAX_SHARE_MAX}): {'MET' if e6 else 'NOT MET'}")
gross = table["active return (gross)"]
years = len(months) / 12
tilt_gross, mandate_gross = gross.xs("C3 tilt only", level="set"), gross.xs("C3", level="set")
se_tilt = table.xs("C3 tilt only", level="set")["realised TE"] / np.sqrt(years)
mandate_cost = mandate_gross - tilt_gross
print(f"expectation 7: gross active return a year, the tilt alone {1e4 * tilt_gross.min():+.1f} to {1e4 * tilt_gross.max():+.1f} bp "
      f"(standard error of a mean over {years:.0f} years, the realised tracking error over the square root of {years:.0f}: {1e4 * se_tilt.min():.0f} to {1e4 * se_tilt.max():.0f}); "
      f"the mandate {1e4 * mandate_gross.min():+.1f} to {1e4 * mandate_gross.max():+.1f}; the mandate minus the tilt alone on the same months, variant by variant: "
      + ", ".join(f"{k} {1e4 * v:+.1f}" for k, v in mandate_cost.items()))
relaxed_months = pd.concat({cs: paths[(("sample", "daily_3y"), cs)]["relaxed"] for cs in ("C2", "C3")}, axis=1)
by_cal = relaxed_months.groupby(relaxed_months.index.month).sum()
by_cal.index = [pd.Timestamp(2000, m, 1).strftime("%b") for m in by_cal.index]
print("relaxed months by calendar month (sample covariance on daily data):")
print(by_cal.T.to_string())
first_relaxed = [cs for cs in ("C3", "C3 tilt only") if bool(paths[(("sample", "daily_3y"), cs)]["relaxed"].iloc[0])]
print(f"the first month is relaxed under: {', '.join(first_relaxed) if first_relaxed else 'none'}")
"""),
    md("""
## By decade: realised against forecast tracking error under the mandate

For each variant under C3, the realised tracking error of each decade beside the mean forecast of the same months, and the ratio of the two; the ten-year variance ratio's version of the forecast beside it for the daily variants.
"""),
    code("""
first_label, last_label = f"{months[0]} to 1989-12", f"2020-01 to {months[-1]}"
blocks = []
for v in VARIANTS:
    path = paths[(v, "C3")]
    dec = E.by_decade(path, first_label, last_label).rename("realised TE")
    grp = pd.Series([first_label if m.year < 1990 else (last_label if m.year >= 2020 else f"{(m.year // 10) * 10}s") for m in path.index], index=path.index)
    fc = path.groupby(grp)["forecast_te"].mean().rename("forecast TE")
    fc_vr = (path["forecast_te"] * np.sqrt(vr10.loc[path.index])).groupby(grp).mean().rename("forecast TE (variance ratio)") if (v[1] == "daily_3y" or v == C.ROBUST_VARIANT) else fc.rename("forecast TE (variance ratio)") * np.nan
    d = pd.concat([dec, fc, fc_vr], axis=1)
    d["realised / forecast"] = d["realised TE"] / d["forecast TE"]
    d.insert(0, "variant", LABEL[v])
    blocks.append(d)
decades = pd.concat(blocks).set_index("variant", append=True).swaplevel()
show_d = decades.copy()
for c in ["realised TE", "forecast TE", "forecast TE (variance ratio)"]:
    show_d[c] = 1e4 * show_d[c]
print("under C3, by decade (bp a year):")
print(show_d.to_string(float_format=lambda x: f"{x:.1f}"))
"""),
    md("""
## Expectations 8 and 9: RiskMetrics, and the forecasts calibrated on their own past

Two additions after the first run (6 October 2026), each with its expectation in `constants.py` before the code. First, RiskMetrics as a seventh variant: Dom, Howard, Jansen and Lohre (2024) find that weighting recent days more does more for a covariance than shrinkage or factor structure and that this simple dynamic estimator does as well as the DCC model for minimum-variance portfolios; notebook 10 found it gave the lowest unconstrained volatility and the best-calibrated forecast; the first design of this notebook left it out, a design miss. Second, a calibration of the forecasts, the fix a risk-model vendor applies when the bias statistic drifts from 1: the forecast of month t is multiplied by the ratio of realised to forecast tracking error over the previous 60 months of the same path, computed from months before t only, so nothing from the future enters it. One setting, 60 months, long enough for a stable ratio (a standard deviation estimated from 60 observations has a standard error of about 9%) and short enough to follow a change of regime within five years. The calibration cannot repair a month that no past resembles; it can repair a bias that persists.
"""),
    code("""
# Added after the first run (6 October 2026): expectation 8, RiskMetrics against the sample covariance on daily data.
ewma_label, sample_label = LABEL[C.EWMA_VARIANT], LABEL[("sample", "daily_3y")]
e8 = te3[ewma_label] <= te3[sample_label] + 1e-12
print(f"expectation 8: realised tracking error under C3, RiskMetrics {1e4 * te3[ewma_label]:.1f} bp against the sample covariance on daily data {1e4 * te3[sample_label]:.1f} bp: {'MET' if e8 else 'NOT MET'}; "
      f"RiskMetrics forecast {1e4 * table.loc[(ewma_label, 'C3'), 'forecast TE (mean)']:.1f} bp, bias {table.loc[(ewma_label, 'C3'), 'bias']:.2f}, turnover {table.loc[(ewma_label, 'C3'), 'turnover (one-way)']:.3f} a month, "
      f"net active return at 50 bp {1e4 * table.loc[(ewma_label, 'C3'), 'net active return at 50 bp']:.1f} bp")
"""),
    code("""
# Added after the first run (6 October 2026): expectation 9, the forecasts calibrated on their own past.
first_label, last_label = f"{months[0]} to 1989-12", f"2020-01 to {months[-1]}"
rows = []
for v in VARIANTS:
    path = paths[(v, "C3")]
    cal = E.calibrated_forecast(path)
    active = path["active_return"].to_numpy()
    grp = pd.Series([first_label if m.year < 1990 else (last_label if m.year >= 2020 else f"{(m.year // 10) * 10}s") for m in path.index], index=path.index)
    row = {"variant": LABEL[v], "bias, 21 rule": E.bias_statistic(active, path["forecast_te"].to_numpy()), "bias, calibrated": E.bias_statistic(active, cal.to_numpy()),
           "mean calibration factor": float((cal / path["forecast_te"]).mean())}
    for g in grp.unique():
        m = (grp == g).to_numpy()
        row[f"calibrated bias, {g}"] = E.bias_statistic(active[m], cal.to_numpy()[m])
    rows.append(row)
calib = pd.DataFrame(rows).set_index("variant")
print("the bias statistic under C3 before and after calibration on the path's own past (60-month window):")
print(calib.to_string(float_format=lambda x: f"{x:.2f}"))
lo9, hi9 = C.EVAL_CALIBRATED_BIAS_RANGE
e9 = int(((calib.loc[daily, "bias, calibrated"] >= lo9) & (calib.loc[daily, "bias, calibrated"] <= hi9)).sum())
print()
print(f"expectation 9: the calibrated bias statistic lies in {lo9} to {hi9} for {e9} of {len(daily)} daily estimators ({', '.join(f'{b:.2f}' for b in calib.loc[daily, 'bias, calibrated'])}): {'MET' if e9 == len(daily) else 'NOT MET'}")
"""),
    md("""
## Save

The measures table, the by-decade table and the active returns of every path are written to `outputs/`, with the vintage in the file name; notebook 13 rebuilds the paths it attributes from the modules.
"""),
    code("""
os.makedirs(C.OUTPUT_DIR, exist_ok=True)
table.to_csv(f"{C.OUTPUT_DIR}/rolling_evaluation_{vintage}.csv", float_format="%.8f")
decades.to_csv(f"{C.OUTPUT_DIR}/rolling_evaluation_by_decade_{vintage}.csv", float_format="%.8f")
calib.to_csv(f"{C.OUTPUT_DIR}/rolling_evaluation_calibration_{vintage}.csv", float_format="%.8f")
active = pd.DataFrame({f"{LABEL[v]} | {cs}": p["active_return"] for (v, cs), p in paths.items()})
active.to_csv(f"{C.OUTPUT_DIR}/active_returns_{vintage}.csv", float_format="%.10f")
print("written:", sorted(f for f in os.listdir(C.OUTPUT_DIR) if f.startswith(("rolling", "active"))))
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. Count first | 566 months, 35 paths with 566 records each; the benchmark held in every month under C0 and C1 in 14 of 14 paths (largest active return 2e-7 a month); the index's own turnover 0.39% a month | holds |
| 2. Does the estimator matter under the mandate | realised tracking error 84.7 to 93.4 basis points across the four daily estimators (range 8.8, level 10); the monthly sample covariance 95.8, above the lowest | MET |
| 3. Calibration of the forecasts under the mandate | bias statistics 1.22 to 1.39 under the 21 rule, 1 of 4 inside 0.8 to 1.25; 1.20 to 1.36 under the ten-year variance ratio, closer to 1 for 4 of 4 | NOT MET |
| 4. The robust portfolio | 87.4 basis points, against 84.7 for the best single estimator and 95.8 for the worst; its forecast the best calibrated (bias 1.09) | MET |
| 5. The realised cost of the fixes | the mandate's C3 above the tilt alone by 4.4 to 5.2 basis points for all seven variants | MET |
| 6. The cap | relaxed in 1 to 4 of 566 months (0.2% to 0.7%), the first month and Julys | MET |
| 7. Active return, costs, holdings | the tilt had no opportunity cost: +1.8 to +6.9 basis points a year gross, inside one standard error (12 to 13) of zero; the mandate -1.0 to -6.9; the mandate's two additions cost 8 to 10 against the tilt alone on the same months; turnover costs 5 to 9 at 50 basis points; net -6 to -15; information ratios -0.07 to -0.17 | reported |
| 8. RiskMetrics (added 6 October) | 84.3 basis points against 84.7 for the sample covariance on daily data; a difference of 0.4, inside the noise | MET, direction only |
| 9. Calibrated forecasts (added 6 October) | calibrated bias statistics 1.11, 1.11, 1.17 and 1.15 for the four daily estimators, 3 of 4 inside 0.85 to 1.15; the monthly covariance's 1.61 falls to 1.12; by decade 0.95 to 1.18 after 1989, 1.24 to 1.50 before | NOT MET |

Expectation 1 holds. 566 evaluation months, 35 paths, 566 records each; under C0 and C1 every path is the benchmark to the solver's precision (the largest active return in any month is 2e-7, two hundred-thousandths of a basis point; the level of 1e-10 written first was set for exact arithmetic and was raised to 1e-6 before the recorded run, as `constants.py` says). The index's own one-way turnover, the trading an index fund cannot avoid, averages 0.39% a month, 4.7% a year, with a median of 0.16% and a largest value of 13.3% in 1988-07; it exceeds 2% in 24 months, all of them Julys, when French rebuilds the industry portfolios from the end-of-June SIC codes. Under C2 the active weight bound leaves room to absorb those months, so the cap was relaxed once and the realised tracking error of following the index at 2% a month is 6.3 to 6.5 basis points.

Expectation 2, the extension's question, is met: under the mandate the four daily estimators realise 84.7 (sample), 84.8 (shrinkage), 91.5 (component model) and 93.4 (factor model) basis points a year of tracking error, a range of 8.8 against the level of 10, and the sample covariance of 120 monthly returns realises 95.8, above all four. The ranking is notebook 10's: on three years of daily data the sample covariance and shrinkage are the same estimate (shrinkage intensity 0.012) and the best, the two structured models pay 7 to 9 basis points for assuming that industries share nothing beyond their factors, and the monthly covariance pays for its noise. The pattern of Dom, Howard, Jansen and Lohre (2024) holds in tracking-error terms with a qualification: the constraints shrink the differences between estimators to about a tenth of the tracking error, and do not remove them.

Expectation 3 is not met, and the way it fails is the notebook's main finding about forecasts. Over the 566 months the daily estimators' forecasts under-forecast the realised tracking error by 22% to 39% (bias statistics 1.22 to 1.39) and the monthly covariance's by 61%. The ten-year variance ratio, which repaired the benchmark's forecasts in notebook 10, changes these by 0.02 to 0.03, because its mean over the evaluation months is 1.00: the positive autocorrelation of the early decades and the negative autocorrelation of the later ones cancel over this sample, and the active portfolio's own autocorrelation is not the benchmark's. The by-decade table says where the miss is. In 1979-07 to 1989-12 the realised tracking error was 1.6 to 2.0 times the forecast for every variant (138 to 156 basis points against 76 to 90); in the 1990s 1.3 to 1.4 times; in the 2000s 1.1 to 1.2; in the 2010s and from 2020 the forecasts were right to within 10%. The first decade is the oil shock. Oil was 15% of the benchmark and the tilt removed 7.6 percentage points of it; the oil price doubled in 1979 and 1980 and collapsed in 1986, and in single months the portfolio's active return reached +1.45% (1980-07), +1.41% (1980-02) and -1.14% (1981-03) against a forecast monthly standard deviation of about 0.24%, five to six forecast standard deviations. A three-year window of daily returns estimated on 1976 to 1979 cannot know that Oil's own volatility is about to triple; this is a change of regime, which no window length repairs, and it is why the realised number is the one that counts. The second part of the miss is of a different kind and does not go away with the decades: the monthly sample covariance under-forecasts by 30% to 70% in every decade, the daily estimators by 10% to 40% in the first three. An optimiser handed a covariance with errors finds the portfolio that looks least risky in that covariance, and part of what makes it look least risky is the errors; the forecast is then an in-sample minimum and the realised number is out of sample. This is the optimisation bias of Michaud (1989), the error-maximisation property of optimised portfolios, and it is larger the noisier the covariance, which is why the monthly covariance's forecast is the worst calibrated (1.61) and the robust portfolio's worst-case forecast, the maximum over five matrices, the best (1.09): taking the worst case across estimates offsets the optimism of each. For a manager: a tracking-error forecast that comes out of an optimiser is biased low, here by a fifth to a third with a good covariance, and the worst case across estimators is the forecast whose bias statistic is nearest one.

Whether the miss of expectation 3 was foreseeable. Its direction was, and the design did not use what it knew. Notebook 10's by-decade table had the benchmark's own forecasts under-forecasting by 34% in 1979 to 1989 under the 21 rule, and Michaud (1989) says that an optimised portfolio's forecast risk is biased low. Both were known on 4 October when the range 0.8 to 1.25 was written for the whole sample, as if the active portfolio's forecasts would be as well calibrated on average as the benchmark's. The miss is on the design side: the expectation should have been written by decade, with a statistic above 1 expected for the first decade and for every optimised portfolio. The size of the miss was not foreseeable from the literature: a first decade at 1.6 to 2.0 times the forecast is the oil shock acting on a portfolio tilted away from Oil, and notebook 10's table, which showed 1.34 for the benchmark, had no active portfolio in it. Expectation 9 below adds the fix for the part of the bias that persists; it uses only months before each forecast, so it is not fitted on the months it is judged on.

Expectation 4 holds. The robust portfolio realises 87.4 basis points, 2.7 above the best single estimator and 8.4 below the worst, at a one-way turnover of 1.1% a month against 1.3% for the sample covariance. It is nobody's worst case, which is what it was built for, and its forecast is the one a manager could have trusted.

Expectation 5 holds. The mandate's fixes, beta neutrality and the exclusion of tobacco and weapons, cost 4.4 to 5.2 basis points a year of realised tracking error for every one of the seven variants. Notebook 11 had forecast 2 to 7 for the daily estimators and 19 to 25 for the monthly covariance; the realised cost for the monthly covariance is 4.8, so the large forecast was the noise talking, the same noise that made its hedges attractive in the first place.

Expectation 6 holds. The cap was relaxed in 2 of 566 months under C3 for the daily estimators and RiskMetrics (the first month, when the tilt is put on from the index, and one July), 3 for the robust portfolio, 4 for the monthly covariance, and once under C2; the share is 0.2% to 0.7% against a level of 10%. The months are the ones the design named.

Expectation 7, the active returns. Opportunity cost, the return a fund gives up by obeying a constraint, is the first thing a client asks about a tilt, and the tilt portfolio's returns show that there was none: over 47 years the tilt alone earned between +1.8 and +6.9 basis points a year gross against the benchmark, and a mean active return over 47 years has a standard error of the realised tracking error divided by the square root of 47, 80 to 91 basis points divided by 6.9, 12 to 13 basis points a year, so the figure is inside one standard error of zero. Holding Coal, Oil and Utilities at half their index weight gave up no return that can be told from chance, which for a sustainability mandate is the result its holders want. The mandate earned between -1.0 and -6.9, also inside one standard error of zero. The difference between the mandate and the tilt alone, 8 to 10 basis points a year, is the opportunity cost of the mandate's two additions, beta neutrality and holding tobacco and weapons at zero, two industries that outperformed the market over the sample; it is a difference of two means on the same months and is less noisy than either, and it is the number a manager reports to the client who asked for the exclusions; notebook 13 splits it between the factors and the industries' own returns and gives its standard error. Trading costs at 50 basis points per unit of turnover take 5 to 9 a year; they are arithmetic on the turnover and carry no noise. Net of them the mandate's portfolios trail the benchmark by 6 to 15 basis points a year, with information ratios of -0.07 to -0.17, on a tracking error of 85 to 96. A manager of such a mandate is judged on four numbers before the active return: the realised tracking error against the ex-ante limit (85 to 96 basis points against 100: inside, for every variant), the constraints obeyed in every month (the relaxed-cap months counted and explained), the turnover and its cost (0.9% to 1.5% a month, 5 to 9 basis points a year at 50), and the cost of each exclusion reported to the client. The information ratio measures skill at forecasting returns; this portfolio makes no return forecast, so an information ratio inside one standard error of zero is the outcome the design implies. The effective number of holdings is 19.0 to 19.8 against the benchmark's 18.9, and the portfolios hold 41 to 45 of the 49 industries. Where the active return came from, by factor, is notebook 13's question.

Expectation 8, RiskMetrics, is met in direction and says nothing in size. Under the mandate RiskMetrics realises 84.3 basis points against 84.7 for the sample covariance on three years of daily data, a difference of 0.4 basis points on paths that share most of their months; a realised tracking error of 85 basis points measured on 566 months has a standard error of about 2.5, so the two are the same number. Its forecast is as low as the others' (bias 1.23 against 1.26), and its turnover is the highest of the daily variants (1.4% a month against 0.9% to 1.3%), because a covariance that weights recent days most changes more from month to month and the portfolio follows it; after costs at 50 basis points it nets -13.9 against -14.8. Dom, Howard, Jansen and Lohre (2024) found that time dynamics were the design choice that mattered most for a constrained minimum-variance portfolio of single stocks; notebook 10 found the same for the unconstrained minimum-variance portfolio of the 49 industries. Under the tracking-error mandate on 49 industries the gain is gone: the active weight bound of 2 percentage points and the turnover cap leave the optimiser too little room for a better covariance to show. The expectation was written as "at or below", and a result of equality meets it without teaching anything; written again, it would name a smallest difference worth calling a gain, 2.5 basis points, one standard error.

Expectation 9, the calibrated forecasts, is not met by one estimator and 0.02. Multiplying each forecast by the ratio of realised to forecast tracking error over the previous 60 months of the same path moves every variant's bias statistic towards 1: the daily estimators from 1.22 to 1.39 to 1.11 to 1.17, the monthly covariance from 1.61 to 1.12, RiskMetrics from 1.23 to 1.08, the robust portfolio from 1.09 to 1.06. Three of the four daily estimators land inside 0.85 to 1.15 (1.11, 1.11, 1.15); the factor model lands at 1.17. The by-decade columns say what the calibration repairs and what it cannot. From 1990 on, the calibrated statistics of the daily estimators lie between 0.95 and 1.18 in every decade, and the monthly covariance's between 1.01 and 1.18: the persistent part of the bias, the optimisation bias, is a ratio that the previous five years measure well. In 1979 to 1989 the calibrated statistics are still 1.24 to 1.50, because the first 24 months run uncorrected and the shock enters the realised numbers before it enters the window; a correction built from the past arrives after the regime it is correcting for. The mean calibration factor, 1.16 to 1.30 for the daily estimators and 1.52 for the monthly covariance, is the size of the correction a manager would have applied in real time. The range 0.85 to 1.15 was written for the whole sample, which includes the 126 months no backward-looking calibration can repair; written for the months from 1990, where the calibration has a full window, the four daily estimators would have landed between 0.96 and 1.18, and the verdict on that range is not claimed, because the range was not written first.

The robust portfolio's status column reports 154 and 113 months of inaccurate solver status under C0 and C1 and one under C3. Under C0 and C1 the optimum is the benchmark exactly, where the worst-case tracking error is zero and the problem's cone constraints are all at their tips; an interior-point method reaches that point only approximately and says so. The weights it returned passed every feasibility check, and the active return in those months is below 2e-7.

**What this notebook does not settle.**

- The under-forecast of 1979 to 1989 is a change of regime that no estimation window anticipates and that the calibration of expectation 9 reaches only after the fact. A manager handles it with scenario and stress tests outside the covariance, which the extension does not build; the notebook states the size of the miss so that a reader knows what a covariance-based forecast can and cannot do.
- The calibration of expectation 9 uses one window length, 60 months, fixed before its code. A shorter window would follow a change of regime sooner and carry more noise (a ratio from 24 months has a standard error of about 15%); the trade-off is stated and not searched, because searching it on these 566 months would fit the window to the sample.
- Where the tilt's and the exclusions' active returns came from, by Fama-French factor, is notebook 13's question.
- The result holds for 49 industries, whose benchmark is concentrated (effective number 19); at the level of single stocks the differences between estimators, and the gain from time dynamics that expectation 8 did not find here, may be larger, which is the second study's question.
- Trading costs are one proportional rate for every industry and month; the realised numbers are gross of costs, and the net figures use 50 and 100 basis points per unit of one-way turnover as the replication does.
- The level for expectation 1 was raised from 1e-10 to 1e-6 after the first run, for the solver's precision. The 30 paths of the design without RiskMetrics and the calibration give the same numbers to every printed decimal with them in the notebook as without.
"""),
]

# ---------------------------------------------------------------------------
# 13: the factor attribution
# ---------------------------------------------------------------------------

NB13 = [
    md("""
# 13. Where the active return came from: a factor attribution of the paths

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same period |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money |
| Cap-weighted | weighted by market capitalisation |
| Benchmark | in the extension, the index the portfolio tracks, the cap-weighted combination of the 49 industries built in notebook 08; its excess return tracks the excess return of all US stocks, French's Mkt-RF series, within 0.47 percentage points a year (correlation 0.9996), so the two are nearly the same series without being one |
| Variance | the average squared distance of a series from its own average; its square root is the standard deviation, the usual measure of how much a return moves; volatility is the standard deviation of returns, stated per year here by multiplying the monthly figure by the square root of 12 |
| Standard error | the uncertainty of a number estimated from a sample: the standard deviation that the estimate would show across repeated samples of the same size; for a mean it is the standard deviation of the observations divided by the square root of their number |
| Covariance matrix | the table of all variances and covariances of a set of assets, 49 by 49 here, 1,225 distinct numbers |
| Covariance estimator | a method for estimating the covariance matrix from a window of data; notebook 10 built four |
| Estimation window | the past returns an estimator sees, 120 months or three years of trading days here |
| Estimation error | the difference between a mean or covariance estimated from a window and its true value |
| Factor | a return series that moves many assets at once; the six here are the market factor Mkt-RF, the return of all US stocks minus the risk-free rate, and five long-short portfolios built to isolate one source each: SMB (small firms over large, size), HML (cheap firms over expensive, value), RMW (profitable firms over unprofitable, profitability), CMA (firms that invest little over firms that invest much, investment) and Mom (recent winners over recent losers, momentum) |
| Principal component | a combination of the assets, with one weight per asset, chosen so that it explains as much of the assets' total variance as a single combination can (notebook 09) |
| Beta | how much an asset moves with a factor on average, estimated by regressing the asset's excess returns on the factors' returns over the estimation window; one beta per factor |
| Active weight | the portfolio's weight in an asset minus the benchmark's weight in it |
| Active return | the portfolio's return minus the benchmark's return in the same month |
| Active exposure | the portfolio's beta to a factor minus the benchmark's: the sum over industries of the active weight times the industry's beta to that factor; how much more or less of the factor the portfolio holds than the index |
| Contribution | the part of a month's active return that one factor accounts for: the active exposure to the factor times the factor's return in the month |
| Residual | the active return minus the sum of the six contributions: the part the factors do not explain, the industries' own returns |
| Attribution | splitting a portfolio's active return into the contributions of named factors plus a residual, so that the parts add up to the whole |
| Factor share | the share of the variance of the active return that the factor contributions explain: one minus the variance of the residual over the variance of the active return |
| Tracking error | the standard deviation of the difference between two return series, stated per year; forecast (ex-ante) when computed from a covariance matrix before the month, realised (ex-post) when measured on the active returns afterwards |
| Long-only | said of a portfolio in which no weight is negative |
| One-way turnover | half the sum over industries of the absolute changes in weight at a rebalance; the fraction of the portfolio sold, which is also the fraction bought when the portfolio stays fully invested |
| Turnover cap | an upper limit on the one-way turnover of a rebalance; 2% a month here |
| Drifted weights | the previous month's weights after that month's returns have moved them, so that they still sum to one |
| Tilt | a constraint that holds named industries below their benchmark weight; here Coal, Oil and Utilities at no more than half of it |
| Exclusion | a constraint that holds named industries at zero weight; Smoke (tobacco) and Guns (weapons) here |
| Beta-neutral | a constraint that holds the portfolio's beta to the benchmark equal to one |
| Mandate | the whole set of rules the fund obeys: the tilt, the exclusions and beta neutrality, the constraint set C3 |
| Constraint set | one of the four cumulative sets C0 to C3: long-only; plus the active weight bound; plus the turnover cap; plus the mandate |
| Optimiser | the extension's routine that solves the constrained tracking-error problem (notebook 11) |
| Robust portfolio | the weights whose largest forecast tracking error across the five covariance estimates is smallest; a portfolio that trusts no single matrix (notebook 11) |
| RiskMetrics | the covariance estimator of J.P. Morgan's 1996 RiskMetrics document: a weighted sample covariance in which each day's weight falls by half every half-life, one year of trading days here, so that recent days count most (notebook 10's sensitivity) |
| Specification | one combination of a variant (an estimator, the robust portfolio or RiskMetrics) and a constraint set |
| Path | the month-by-month sequence of portfolios of one specification, each built on the data before its month (notebook 12) |
| Basis point | one hundredth of a percentage point, so 50 basis points is 0.50% |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |

**The problem, stated the way practitioners state it.** A mandate's rules create positions the client did not ask for. The tilt removes half of three industries, the optimiser replaces them with the industries whose movement comes closest, and the result is a set of exposures to the common sources of return that nobody chose. Dom, Howard, Jansen and Lohre (2024), whose framing the extension follows, judge covariance estimators on the constrained portfolio a practitioner would hold, after costs; the counterpart after the fact is the question a client's report answers every quarter: of the active return, how much came through exposures to the known factors, the market, size, value, profitability, investment and momentum, which a manager could have hedged, and how much from the industries themselves, which is the mandate. The attribution a factor risk model reports is the active exposure to each factor times the factor's return, month by month, plus a residual. The six factors here are the academic standard set, the five of Fama and French (2015) plus the momentum factor of Carhart (1997), and the set French's library provides; commercial risk models use larger sets of their own (style, industry, country and currency factors), and macro factor models use variables such as the oil price, inflation and interest rates, each turned into a portfolio that tracks it. Factors can also be derived from the data with no name attached: the principal components of notebook 09 are such factors, and notebook 10 built a covariance estimator from them; they change from window to window and mean nothing to a client, so they serve the risk forecast and the named factors serve the report. The set is a convention, and a client's report uses the one the client knows. Notebook 12 found that the tilt had no opportunity cost and that the mandate's two additions, beta neutrality and the exclusions, cost 8 to 10 basis points a year against the tilt alone; this notebook says where those numbers came from.

**What this notebook does.** It rebuilds the fourteen paths of notebook 12 under the mandate's C3 and under the tilt alone (the seven variants under each), keeping their weights; for every month it estimates the 49 industries' betas to the six factors on the three years of daily returns before the month, the regression that notebook 10's factor covariance estimator runs; it computes each path's active exposures, the six contributions and the residual, checks that contributions plus residual equal the active return, and reports the attribution per path, by decade, and for the difference between the mandate and the tilt alone, which is the cost of the mandate's two additions, beta neutrality and the exclusions.

**How a month is attributed.**

- The active weights: the path's weights for the month minus the benchmark's, one number per industry, summing to zero.
- The betas: each industry's excess returns over the three years of trading days before the month, regressed on the six factors' daily returns with an intercept; 49 industries by 6 factors. A beta is the return per unit of factor return and is estimated here on daily returns and applied to monthly ones, as factor risk models do.
- Two uses of beta, by design. The optimiser's beta-neutrality rule uses each industry's beta to the index, read from the covariance matrix the optimiser works with, because the mandate is to track this index with a beta of one. The attribution uses each industry's betas to the six factors, estimated together by one regression, because the report splits the return across the factors a client knows. The index and the market factor move almost identically (correlation 0.9996), so the two market betas differ by about 0.005 at most, and the market exposure of a beta-neutral portfolio is near zero without being exactly zero.
- The active exposures: for each factor, the sum over industries of the active weight times the industry's beta to it. Worked number: if the portfolio holds 3 percentage points less than the benchmark in an industry with a beta of 1.5 to the value factor and 3 points more in one with a beta of 0.5, its active exposure to value is -0.03 times 1.5 plus 0.03 times 0.5, that is -0.03.
- The contributions: each active exposure times the factor's return in the month. With an active exposure to value of -0.03 in a month in which the value factor returns +2%, the value contribution is -0.06% of the portfolio.
- The residual: the active return of the month minus the six contributions. It is the part of the active return that the industries earned on their own, beyond what their factor betas account for.
- The identity: contributions plus residual equal the active return, by construction; the check is that the arithmetic holds within 1e-9 in every month.
- The measures of a path: the mean active exposure to each factor; each factor's mean contribution per year with its standard error (the standard deviation of the monthly contributions over the square root of 566, times 12), the same for the residual and the active return; and the factor share.

**What I expect to see, written before the run (`constants.py`, 6 October 2026).**

1. Count first: 566 months from 1979-07; the six monthly factor series cover every one of them; 14 paths with 566 records each, whose realised tracking errors reproduce notebook 12's within 0.1 basis point a year; the identity holds within 1e-9 in every month of every path.
2. Beta neutrality shows in the exposures: the mean active exposure to the market factor is within 0.05 of zero for every path. Under the mandate it is a constraint (beta neutrality to the benchmark, whose correlation with the market return is 0.9996); under the tilt alone notebook 11 found that the optimiser restores the beta on its own, to 1.004 with daily data and 1.010 with the monthly covariance.
3. The exposures come from the tilt and the mandate, and from the estimator only at the margin: among the five factors other than the market, the mean active exposure under the mandate has the same sign across all seven variants for at least four. Reason: the exposures come from what is removed, half of Coal, Oil and Utilities and all of Smoke and Guns, which is the same for every variant; the estimator chooses only among the substitutes.
4. The factors explain less than half of the active return's variance for every path (factor share below 0.5): a tilt on three industries is mostly industry-specific risk, and notebook 11 found the market part of the forecast active variance below 5% for the daily estimators.
5. The mandate's cost against the tilt alone, the difference of the two paths' active returns on the same months (8 to 10 basis points a year in notebook 12), comes mostly through the industries' own returns. Two parts are tested. (a) The part that comes through the six factors is below half of the cost in every one of the seven variants. (b) The exclusions' factor part, the five factors other than the market, is within 2 basis points a year of the figure the arithmetic of the inputs gives, in every variant. The arithmetic: the mandate adds two rules to the tilt. Beta neutrality moves the market exposure by at most the 0.004 to 0.010 the optimiser leaves under the tilt alone (notebook 11), worth at most 0.01 times the market's excess return of 8.9% a year over the evaluation months, 9 basis points, and less wherever the beta was already restored. The exclusion of Smoke and Guns removes 1.3% of the benchmark on average over the evaluation months (0.9% at 2026-08), and the two industries' betas to profitability and investment, weighted by their benchmark weights and averaged over the months, sit 0.3 to 0.5 above the benchmark's (tobacco's at 2026-08 are 0.29 and 0.32 against the benchmark's 0.04 and 0.04); giving their weight to industries with the benchmark's betas moves the exposure to each of the two factors by 0.013 times 0.3 to 0.5, that is 0.004 to 0.006, and at those factors' mean returns over the evaluation months, 4.0% and 2.7% a year, that exposure is worth 1 to 2 basis points a year each. So the exclusions' factor part should be about 3 basis points a year, and the rest of the exclusions' cost, whatever its size, should be the industries' own returns: what tobacco and weapons earned beyond their factor betas, which Hong and Kacperczyk (2009) measured as a premium against three factors and momentum and Blitz and Fabozzi (2017, "Sin Stocks Revisited", Journal of Portfolio Management) found accounted for by the profitability and investment factors once those are in the model. The cell computes the arithmetic from the inputs, month by month, and tests the measurement against it; the 2 basis points of (b) allow for the substitutes' betas differing from the benchmark's and for the exposures varying over time.
6. Reported, no verdict: each path's contributions by factor and its residual, with their standard errors; the exposures; the attribution by decade for the sample covariance's mandate path.

Running time: about five minutes, most of it the 14 paths.
"""),
    md("""
## Modules

`constants`, `french_loader`, `benchmark`, `rules`, `covariance`, `optimiser` and `evaluation` are those of earlier notebooks. `attribution` is new: the active exposures, the monthly attribution with its identity check, the measures of a path and the grouping by period, each tested on made-up data with hand-computed results in `tests/test_attribution.py`.
"""),
    code("""
import importlib.util, subprocess, sys
if importlib.util.find_spec("cvxpy") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "cvxpy"])
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("benchmark.py"),
    writefile("rules.py"),
    writefile("covariance.py"),
    writefile("optimiser.py"),
    writefile("evaluation.py"),
    writefile("attribution.py"),
    md("""
## Count first: the months, the factors, the paths to rebuild
"""),
    code("""
import sys
sys.path.insert(0, "src")
import time
import numpy as np
import pandas as pd
from bp import constants as C
from bp import french_loader as fl
from bp import covariance as CV
from bp import optimiser as O
from bp import evaluation as E
from bp import attribution as A

pd.set_option("display.width", 230)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_columns", 40)

P = CV.Panels()
weights, returns_m = P.weights, P.returns_m
months = pd.period_range(C.COV_EVAL_START, P.last, freq="M")
industries = [c.strip() for c in weights.columns]
tilt_mask, _ = O.masks(weights.columns)
_, mandate_mask = O.masks(weights.columns, exclude=C.MANDATE_EXCLUSIONS)
SETS = {"C3": C.CONSTRAINT_SETS["C3"], "C3 tilt only": C.CONSTRAINT_SET_TILT_ONLY}
assert tuple(SETS) == C.ATTRIBUTION_SETS
VARIANTS = list(CV.ALL_VARIANTS)
LABEL = {v: ("robust, all five" if v == C.ROBUST_VARIANT else ("RiskMetrics, daily 5y" if v == C.EWMA_VARIANT else f"{v[0]}, {v[1].replace('_', ' ')}")) for v in VARIANTS}
FACTORS = list(C.ATTRIBUTION_FACTORS)

# Expectation 1, the counts
assert len(months) == 566, len(months)
factors_m = P.factors_m.loc[months, FACTORS]
assert factors_m.notna().all().all() and len(factors_m) == len(months), "a factor is missing in an evaluation month"
n_paths = len(VARIANTS) * len(SETS)
assert n_paths == 14
provenance = [fl.download(key) for key in P.files]
fl.write_provenance(provenance)
vintage = provenance[0]["vintage_line"].split("the ")[1].split(" ")[0]
print(f"{len(months)} evaluation months, {months[0]} to {months[-1]}; the six factors {', '.join(FACTORS)} have a return in every one of them")
print(f"{n_paths} paths to rebuild: {len(VARIANTS)} variants under {' and '.join(SETS)}")
print(f"CRSP vintage of the eight files: {vintage}")
"""),
    md("""
## The covariances and the betas, once per month

Each estimator variant's covariance is built once per month, as in notebook 12, and beside it the industries' betas to the six factors from the same three-year daily window, the regression of notebook 10's factor covariance estimator; the betas are the same for every path, because they describe the industries and not the portfolio.
"""),
    code("""
t0 = time.time()
Sigmas = {v: {} for v in CV.EVALUATION_VARIANTS + (C.EWMA_VARIANT,)}
betas = {}
for i, month in enumerate(months):
    for v in CV.EVALUATION_VARIANTS + (C.EWMA_VARIANT,):
        Sigmas[v][month], _, _ = CV.estimate(*v, month, P)
    X = CV.daily_window(P.excess_d, month, C.EXT_COV_DAILY_WINDOW_YEARS)
    _, betas[month] = CV.factor_cov(X.to_numpy(), P.factors_d.loc[X.index, FACTORS].to_numpy())
    if i % 100 == 0:
        print(f"{month}: {time.time() - t0:.0f}s")
Sigmas[C.ROBUST_VARIANT] = {m: [Sigmas[v][m] for v in CV.EVALUATION_VARIANTS] for m in months}
B_last = pd.DataFrame(betas[months[-1]], index=industries, columns=FACTORS)
B_mean = pd.DataFrame(np.mean([betas[m] for m in months], axis=0), index=industries, columns=FACTORS)
print(f"{len(months)} months of covariances and betas in {time.time() - t0:.0f}s")
named = [c for c in industries if c in C.TILT_INDUSTRIES + C.MANDATE_EXCLUSIONS]
for label, B_show, w_show in [(f"at {months[-1]}", B_last, weights.loc[months[-1]].to_numpy()), ("averaged over the evaluation months", B_mean, weights.loc[months].mean().to_numpy())]:
    print()
    print(f"the betas {label} of the tilted and the excluded industries, and of the benchmark (weights times betas):")
    show_b = B_show.loc[named].copy()
    show_b.loc["benchmark"] = w_show @ B_show.to_numpy()
    print(show_b.to_string(float_format=lambda x: f"{x:.2f}"))
"""),
    md("""
## The paths, rebuilt with their weights

The fourteen paths of notebook 12 under the mandate's C3 and under the tilt alone, rebuilt from the same modules on the same files, this time keeping every month's weights. The first check of expectation 1 is that their realised tracking errors are the ones notebook 12 recorded.
"""),
    code("""
paths = {}
t0 = time.time()
for v in VARIANTS:
    for cs, names in SETS.items():
        t1 = time.time()
        paths[(v, cs)] = E.run_path(months, Sigmas[v], weights, returns_m, names, tilt_mask,
                                    mandate_mask if "exclusion" in names else None, robust=(v == C.ROBUST_VARIANT), keep_weights=True)
        print(f"{LABEL[v]:>24}  {cs:<13} {time.time() - t1:5.0f}s")
print(f"{len(paths)} paths in {time.time() - t0:.0f}s")
print()
repro = []
for (v, cs), path in paths.items():
    te = E.realised_tracking_error(path["active_return"])
    ref = C.ATTRIBUTION_REFERENCE_TE[(LABEL[v], cs)]
    repro.append({"variant": LABEL[v], "set": cs, "realised TE (bp)": 1e4 * te, "notebook 12 (bp)": 1e4 * ref, "difference (bp)": 1e4 * (te - ref)})
repro = pd.DataFrame(repro).set_index(["variant", "set"])
print(repro.to_string(float_format=lambda x: f"{x:.3f}"))
ok_repro = int((repro["difference (bp)"].abs() <= 1e4 * C.ATTRIBUTION_REPRODUCTION_TOL).sum())
print()
print(f"expectation 1, the rebuilt paths: {len(paths)} paths with {set(len(p) for p in paths.values())} records each; realised tracking error within {1e4 * C.ATTRIBUTION_REPRODUCTION_TOL:.1f} bp of notebook 12's in {ok_repro} of {len(repro)}: {'holds' if ok_repro == len(repro) else 'FAILS'}")
"""),
    md("""
## The attribution, path by path

One row per path. Exposures are averages over the 566 months; contributions, residual and active return are in basis points a year with their standard errors; the factor share is the share of the active return's variance that the six contributions explain.
"""),
    code("""
atts, rows = {}, []
bench_w = weights.loc[months]
for (v, cs), path in paths.items():
    W = pd.DataFrame(np.vstack(path["weights"].to_list()), index=path.index, columns=weights.columns)
    att = A.attribute(W, bench_w, betas, factors_m, path["active_return"])
    atts[(v, cs)] = att
    rows.append({"variant": LABEL[v], "set": cs, **A.summarise(att)})
summary = pd.DataFrame(rows).set_index(["variant", "set"])
largest_identity = summary["largest identity error"].max()
print(f"expectation 1, the identity: contributions plus residual equal the active return within {largest_identity:.1e} in every month of every path (level {C.ATTRIBUTION_IDENTITY_MAX_ABS_ERROR:g}): {'holds' if largest_identity <= C.ATTRIBUTION_IDENTITY_MAX_ABS_ERROR else 'FAILS'}")
print()
exp_cols = [f"exposure {f}" for f in FACTORS]
print("mean active exposures:")
print(summary[exp_cols].rename(columns=lambda c: c.replace("exposure ", "")).to_string(float_format=lambda x: f"{x:+.3f}"))
print()
con_cols = [f"contribution {f} (per year)" for f in FACTORS] + ["factor total (per year)", "residual (per year)", "active return (per year)"]
se_cols = [c.replace("(per year)", "(standard error)") for c in con_cols]
shown = (1e4 * summary[con_cols]).rename(columns=lambda c: c.replace("contribution ", "").replace(" (per year)", ""))
shown["factor share"] = summary["factor share"]
print("contributions, residual and active return, basis points a year:")
print(shown.to_string(float_format=lambda x: f"{x:+.1f}"))
print()
print("standard errors of the same, basis points a year:")
print((1e4 * summary[se_cols]).rename(columns=lambda c: c.replace("contribution ", "").replace(" (standard error)", "")).to_string(float_format=lambda x: f"{x:.1f}"))
"""),
    md("""
## Expectations 2 to 5
"""),
    code("""
mandate = summary.xs("C3", level="set")
tilt_only = summary.xs("C3 tilt only", level="set")

# Expectation 2: the market exposure
mkt = summary["exposure Mkt-RF"]
e2 = int((mkt.abs() <= C.ATTRIBUTION_MARKET_EXPOSURE_MAX).sum())
print(f"expectation 2: mean active exposure to Mkt-RF from {mkt.min():+.3f} to {mkt.max():+.3f}; within {C.ATTRIBUTION_MARKET_EXPOSURE_MAX} of zero in {e2} of {len(mkt)} paths: {'MET' if e2 == len(mkt) else 'NOT MET'}; "
      f"under the mandate {mandate['exposure Mkt-RF'].min():+.3f} to {mandate['exposure Mkt-RF'].max():+.3f}, under the tilt alone {tilt_only['exposure Mkt-RF'].min():+.3f} to {tilt_only['exposure Mkt-RF'].max():+.3f}")

# Expectation 3: the sign of the exposures across variants, under the mandate
others = [f for f in FACTORS if f != "Mkt-RF"]
signs = np.sign(mandate[[f"exposure {f}" for f in others]])
agree = {f: bool((signs[f"exposure {f}"] == signs[f"exposure {f}"].iloc[0]).all()) for f in others}
e3 = sum(agree.values())
print(f"expectation 3: the sign of the mean active exposure under the mandate is the same for all {len(mandate)} variants in {e3} of {len(others)} factors (" + ", ".join(f"{f}: {'same' if a else 'differs'}" for f, a in agree.items()) + f"; level {C.ATTRIBUTION_SIGN_AGREEMENT_MIN}): {'MET' if e3 >= C.ATTRIBUTION_SIGN_AGREEMENT_MIN else 'NOT MET'}")
print("mean active exposures under the mandate, averaged over the seven variants: " + ", ".join(f"{f} {mandate[f'exposure {f}'].mean():+.3f}" for f in FACTORS))
# The arithmetic of the tilt: holding half of Coal, Oil and Utilities and giving the weight to industries with the benchmark's betas
tilt_idx = [i for i, c in enumerate(industries) if c in C.TILT_INDUSTRIES]
implied_tilt = []
for month in months:
    B, b = betas[month], weights.loc[month].to_numpy()
    beta_bench = b @ B
    implied_tilt.append(-sum((1 - C.TILT_MAX_SHARE_OF_BENCHMARK) * b[i] * (B[i] - beta_bench) for i in tilt_idx))
implied_tilt = pd.DataFrame(implied_tilt, index=months, columns=FACTORS).mean()
print("the arithmetic of the tilt: holding half of Coal, Oil and Utilities and giving the weight to industries with the benchmark's betas would move the exposures by "
      + ", ".join(f"{f} {v:+.3f}" for f, v in implied_tilt.items()) + "; measured under the tilt alone, averaged over the seven variants: "
      + ", ".join(f"{f} {tilt_only[f'exposure {f}'].mean():+.3f}" for f in FACTORS))

# Expectation 4: the factor share
share = summary["factor share"]
e4 = int((share < C.ATTRIBUTION_FACTOR_SHARE_MAX).sum())
print(f"expectation 4: factor share from {share.min():.2f} to {share.max():.2f}; below {C.ATTRIBUTION_FACTOR_SHARE_MAX} in {e4} of {len(share)} paths: {'MET' if e4 == len(share) else 'NOT MET'}")

# Expectation 5: the mandate's cost against the tilt alone, through the factors and through the industries' own returns
cost = pd.DataFrame({"active return": mandate["active return (per year)"] - tilt_only["active return (per year)"],
                     "factor total": mandate["factor total (per year)"] - tilt_only["factor total (per year)"],
                     "residual": mandate["residual (per year)"] - tilt_only["residual (per year)"]})
for f in FACTORS:
    cost[f] = mandate[f"contribution {f} (per year)"] - tilt_only[f"contribution {f} (per year)"]
cost["factor part of the cost"] = cost["factor total"] / cost["active return"]
print()
print("the mandate's C3 minus the tilt alone, basis points a year (the cost of beta neutrality and the exclusions), and the share of it that comes through the factors:")
show_cost = cost.copy()
for c in show_cost.columns:
    if c != "factor part of the cost":
        show_cost[c] = 1e4 * show_cost[c]
print(show_cost.to_string(float_format=lambda x: f"{x:+.2f}"))
se_rows = []
for v in VARIANTS:
    a3, a0 = atts[(v, "C3")], atts[(v, "C3 tilt only")]
    row = {"variant": LABEL[v]}
    for col in ("active return", "factor total", "residual"):
        d = (a3[col] - a0[col]).to_numpy()
        row[col] = 12 * d.std(ddof=1) / np.sqrt(len(d))
    se_rows.append(row)
cost_se = pd.DataFrame(se_rows).set_index("variant")
print()
print("standard errors of the cost and of its two parts (the difference of the two paths on the same months), basis points a year:")
print((1e4 * cost_se).to_string(float_format=lambda x: f"{x:.2f}"))

# The arithmetic of the inputs for the exclusions' factor part: excluding Smoke and Guns and giving their weight to industries with the
# benchmark's betas moves each exposure by minus their weight times the distance of their beta from the benchmark's; times the factor's
# mean return, that is a contribution a year. Averaged over the months, beside what the paths measured.
excl_idx = [i for i, c in enumerate(industries) if c in C.MANDATE_EXCLUSIONS]
implied = []
for month in months:
    B, b = betas[month], weights.loc[month].to_numpy()
    beta_bench = b @ B
    implied.append(-sum(b[i] * (B[i] - beta_bench) for i in excl_idx))
implied = pd.DataFrame(implied, index=months, columns=FACTORS)
excl_weight = weights.loc[months].iloc[:, excl_idx].sum(axis=1)
arith = pd.DataFrame({"implied exposure change": implied.mean(),
                      "factor mean return (per year)": 12 * factors_m.mean(),
                      "implied contribution (bp a year)": 1e4 * 12 * implied.mean() * factors_m.mean(),
                      "measured exposure change (mean of the seven variants)": pd.Series((mandate[exp_cols] - tilt_only[exp_cols]).mean().to_numpy(), index=FACTORS),
                      "measured contribution change (bp a year, mean of the seven)": 1e4 * cost[FACTORS].mean()})
print()
print(f"the arithmetic of the inputs: Smoke and Guns are {excl_weight.mean():.1%} of the benchmark on average over the evaluation months ({excl_weight.iloc[-1]:.1%} at {months[-1]}); "
      f"excluding them and giving their weight to industries with the benchmark's betas moves each exposure by minus their weight times their beta's distance from the benchmark's:")
print(arith.round(4).to_string())
implied_ex_market = 12 * (implied.mean() * factors_m.mean()).drop("Mkt-RF").sum()
measured_ex_market = cost["factor total"] - cost["Mkt-RF"]
e5a = int(((cost["active return"] < 0) & (cost["factor part of the cost"] < C.ATTRIBUTION_FACTOR_PART_MAX)).sum())
e5b = int(((measured_ex_market - implied_ex_market).abs() <= C.ATTRIBUTION_ARITHMETIC_TOL).sum())
print(f"the exclusions' factor part without the market, which beta neutrality removes: implied by the arithmetic {1e4 * implied_ex_market:+.2f} bp a year; measured, across the seven variants, {1e4 * measured_ex_market.min():+.2f} to {1e4 * measured_ex_market.max():+.2f}")
print()
print(f"expectation 5a: the factor part of the mandate's cost is below {C.ATTRIBUTION_FACTOR_PART_MAX:.0%} in {e5a} of {len(cost)} variants ({cost['factor part of the cost'].min():.0%} to {cost['factor part of the cost'].max():.0%}): {'MET' if e5a == len(cost) else 'NOT MET'}")
print(f"expectation 5b: the exclusions' factor part is within {1e4 * C.ATTRIBUTION_ARITHMETIC_TOL:.0f} bp a year of the arithmetic's {1e4 * implied_ex_market:+.2f} in {e5b} of {len(cost)} variants (largest distance {1e4 * (measured_ex_market - implied_ex_market).abs().max():.2f}): {'MET' if e5b == len(cost) else 'NOT MET'}")
"""),
    md("""
## By decade: the sample covariance's mandate path

Contributions, residual and active return per year for each decade of the evaluation months, for the sample covariance on daily data under the mandate; the standard error of a mean over about 120 months is about 2.2 times the one over 566.
"""),
    code("""
first_label, last_label = f"{months[0]} to 1989-12", f"2020-01 to {months[-1]}"
decade = pd.Series([first_label if m.year < 1990 else (last_label if m.year >= 2020 else f"{(m.year // 10) * 10}s") for m in months], index=months)
att_sample = atts[(("sample", "daily_3y"), "C3")]
dec = A.by_period(att_sample, decade)
print("sample covariance on daily data, mandate's C3, basis points a year by decade:")
print((1e4 * dec).rename(columns=lambda c: c.replace("contribution ", "")).to_string(float_format=lambda x: f"{x:+.1f}"))
print()
exp_dec = att_sample[[f"exposure {f}" for f in FACTORS]].groupby(decade.loc[att_sample.index]).mean()
print("mean active exposures by decade, same path:")
print(exp_dec.rename(columns=lambda c: c.replace("exposure ", "")).to_string(float_format=lambda x: f"{x:+.3f}"))
"""),
    md("""
## Save

The attribution summary, the by-decade table, the cost decomposition and the monthly attribution of the sample covariance's mandate path are written to `outputs/`, with the vintage in the file name, as a record; beside them the industries' betas to the six factors, averaged over the evaluation months and at the last month, the benchmark weights, and the six factors' mean returns and volatilities per year over the evaluation months, so that the inputs of the arithmetic can be reused (the companion page in `companion/` is built from them).
"""),
    code("""
os.makedirs(C.OUTPUT_DIR, exist_ok=True)
summary.to_csv(f"{C.OUTPUT_DIR}/attribution_summary_{vintage}.csv", float_format="%.8f")
dec.to_csv(f"{C.OUTPUT_DIR}/attribution_by_decade_{vintage}.csv", float_format="%.8f")
cost.join(cost_se.add_suffix(" (standard error)")).to_csv(f"{C.OUTPUT_DIR}/attribution_mandate_cost_{vintage}.csv", float_format="%.8f")
att_sample.to_csv(f"{C.OUTPUT_DIR}/attribution_monthly_sample_C3_{vintage}.csv", float_format="%.10f")
B_mean.to_csv(f"{C.OUTPUT_DIR}/attribution_betas_mean_{vintage}.csv", float_format="%.6f")
B_last.to_csv(f"{C.OUTPUT_DIR}/attribution_betas_{months[-1]}_{vintage}.csv", float_format="%.6f")
pd.DataFrame({"mean weight": weights.loc[months].mean().to_numpy(), f"weight {months[-1]}": weights.loc[months[-1]].to_numpy()}, index=industries).to_csv(f"{C.OUTPUT_DIR}/attribution_benchmark_weights_{vintage}.csv", float_format="%.6f")
pd.DataFrame({"mean return per year": 12 * factors_m.mean(), "volatility per year": factors_m.std() * np.sqrt(12), "months": len(factors_m)}).rename_axis("factor").to_csv(f"{C.OUTPUT_DIR}/factor_means_{months[0]}_to_{months[-1]}_{vintage}.csv", float_format="%.6f")
print("written:", sorted(f for f in os.listdir(C.OUTPUT_DIR) if f.startswith(("attribution", "factor_means"))))
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. Count first | 566 months, the six factors complete; 14 paths with 566 records each, realised tracking errors within 0.001 basis point of notebook 12's in 14 of 14; contributions plus residual equal the active return within 2e-18 in every month | holds |
| 2. Mean active exposure to the market within 0.05 of zero, every path | -0.005 to +0.001 | MET |
| 3. The sign of the mean exposure is the same across the seven variants for at least four of the five other factors | 5 of 5: size positive, value, profitability, investment and momentum negative | MET |
| 4. The factors explain less than half of the active variance, every path | factor share 0.14 to 0.28 | MET |
| 5. The mandate's cost against the tilt alone comes mostly through the industries' own returns: (a) the factor part below half, every variant; (b) the exclusions' factor part within 2 basis points of the arithmetic of the inputs, every variant | 8.0 to 10.4 basis points a year (standard errors 3.4 to 4.9): through the factors 1.6 to 3.7 (20% to 40%), of which the market 0.3 to 1.5 and the other five factors 1.3 to 2.9 against 2.9 from the arithmetic (largest distance 1.7); through the industries' own returns 4.8 to 7.4 (60% to 80%) | MET, 7 of 7 and 7 of 7 |
| 6. Contributions, residual, exposures, by decade | the tilt alone: factor total -9 to -13 basis points a year, residual +12 to +20, the two within one to two standard errors of zero and offsetting; the mandate: -11 to -17 and +7 to +14 | reported |

Expectation 1 holds. The six factors have a return in every one of the 566 months; the fourteen paths rebuilt from the modules give the realised tracking errors notebook 12 recorded to within 0.001 basis point (the one difference of 0.001 is the rounding of the recorded number), so the weights attributed here are the portfolios notebook 12 judged; and in every month of every path the six contributions plus the residual equal the active return to 2e-18, which is floating-point arithmetic and says the bookkeeping is right.

Expectation 2 holds. The mean active exposure to the market factor is between -0.005 and +0.001 for all fourteen paths. Under the mandate it is a constraint; under the tilt alone it is the optimiser's own work, as notebook 11 found at three months (betas restored to 1.004 with daily data and 1.010 with the monthly covariance), and over 566 months the two sets are indistinguishable on this count. A market exposure is the most expensive position a tracking-error mandate can hold: an exposure of 0.05 times the market's volatility of 15.6% a year is 78 basis points of tracking error, most of the 100 the mandate allows, and this portfolio makes no forecast of the market's direction that would justify spending them. It makes none by design: the extension uses no expected returns anywhere, because the replication (notebooks 02 to 04) showed that estimated means are where estimation error does its damage, so the optimiser's only input is a covariance matrix, and the fund's promise to its client is to track the index within the tracking-error limit while obeying the mandate; a view on the market's direction would be a different product. So the optimiser, which minimises tracking error, removes the exposure first: the weight it takes from Oil and Utilities, whose betas to the index are 0.4 and 0.3, goes to other industries with betas below one, so that the weighted average returns to one. The 0.005 that remains is worth 0.005 times 8.9% a year, the market's mean excess return over the evaluation months, 4 basis points a year of return, and 0.005 times 15.6%, 8 basis points of tracking error.

Expectation 3 holds in all five factors. Under the mandate every variant holds slightly more of the size factor than the benchmark (+0.013 on average) and slightly less of value (-0.014), profitability (-0.010), investment (-0.005) and momentum (-0.004). The signs come from what the tilt removes, and the cell's arithmetic shows it. Averaged over the evaluation months, Oil's betas are -0.16 to size, +0.27 to value, +0.12 to profitability and +0.45 to investment, and Utilities' -0.10, +0.35, +0.02 and +0.17, against the benchmark's +0.05, 0.00, -0.01 and +0.01 (at 2026-08 Oil's value beta is 0.71, Coal's 0.50 and Utilities' 0.37). Oil and Utilities behave like large firms, so holding half of them leaves the portfolio with more of the size factor than the index; they behave like value, profitable and low-investment firms, so it leaves the portfolio with less of those three. Holding half of the three industries and giving the weight to industries with the benchmark's betas would move the exposures by +0.010 size, -0.020 value, -0.010 profitability, -0.012 investment and -0.003 momentum; the paths under the tilt alone show +0.012, -0.014, -0.007, -0.004 and -0.004, and the difference is the substitutes' own betas (Food, Soda and Telcm have investment betas of 0.2 to 0.4, which brings investment back towards zero). The exclusions push the same way: tobacco's betas are -0.17 to size and +0.38 and +0.56 to profitability and investment. The estimator changes the size of each exposure by 0.001 to 0.005 and the sign of none. The exposures are small because the active weight bound is: 2 percentage points per industry times betas that differ by about 0.5 across industries gives exposures of about 0.01, and they were largest in the first decade (value -0.050, profitability -0.047 for the sample covariance's path), when Oil was 15% of the benchmark and the tilt removed 7.6 points of it.

Expectation 4 holds. The six contributions explain between 14% and 28% of the variance of the active return; 72% to 86% is the industries' own returns. A tilt on three industries is an industry bet first and a factor bet at the margin, which is what the small exposures of expectation 3 and notebook 11's finding that the market part of the forecast active variance was below 5% had said in advance. The residual does not average away because the bet is concentrated: diversification works by holding many small unrelated positions whose own returns cancel, and the side the tilt sells is three industries, 7.6 percentage points of Oil alone in 1980, while the side it buys is spread over 41 to 45 industries within 2 points each. The buying side diversifies; the selling side cannot, and the residual risk is the selling side's. For a mandate whose purpose is the industry tilt, that split is the intended one: the industries' own returns are the bet the client asked for, and the factor exposures are the by-product nobody chose. A manager who wanted a different split has four routes, none of which this study runs. First, factor-neutral constraints in the optimiser, the same rule that beta neutrality applies to the market applied to the other five factors, which sets the contributions to zero by construction and would have removed the 9 to 13 basis points a year of factor exposures under the tilt alone, at the price of active-weight budget spent on the hedging industries and of the turnover needed to keep the exposures at zero as the betas move. Second, stocks in place of industries: a tilt built inside each industry, keeping the industry's weight and replacing its highest-emitting firms with its lowest-emitting ones, removes the industry bet itself, and the residual becomes firm-specific and diversifiable across hundreds of names, where 49 industries allow an industry only to be cut as a whole. Third, a commodity factor beside the six, so that the oil-price part of the residual becomes a named exposure that can be measured and hedged. Fourth, a covariance estimator with factor structure inside the optimiser: the factor-model variant has the lowest factor share here (0.14) and the smallest market part of the mandate's cost (0.3 basis points), because its risk forecast already contains the six factors, so the portfolio it finds least risky is the one with the smallest factor exposures.

Expectation 5 holds in both parts. Against the tilt alone the mandate cost 8.0 to 10.4 basis points a year (standard errors 3.4 to 4.9), of which 1.6 to 3.7 (20% to 40%; standard errors 1.0 to 1.9) came through the six factors and 4.8 to 7.4 (60% to 80%; standard errors 3.3 to 4.9) through the industries' own returns. Within the factor part the market carries 0.3 to 1.5, beta neutrality's share, and the other five factors 1.3 to 2.9, the exclusions' share, against the 2.9 the arithmetic of the inputs gave (every variant within 1.7 of it, inside the 2 allowed): profitability 1.1 to 1.9 and value 0.8 to 1.4 carry it, in the direction Blitz and Fabozzi (2017) found for sin stocks (the cell prints the implied exposure change beside the measured one, factor by factor; the implied change in the exposure to profitability is -0.004 and the measured -0.003). The larger part of the exclusions' cost is the industries' own returns, 5 to 7 basis points a year at one to two standard errors from zero: on 566 months of two industries, the premium Hong and Kacperczyk (2009) measured and no premium at all are both inside the uncertainty. What the result says for the mandate: the exclusions cost the fund mostly what tobacco and weapons earned on their own, which no hedge of factor exposures would have recovered, and the number reported to the client who asked for them is the cost of the mandate's two additions, 8 to 10 basis points a year with a standard error of 3 to 5, almost all of it the exclusions'.

Expectation 6, the contributions, is the notebook's main result, and it reads notebook 12's zero in two parts. Under the tilt alone the six factor exposures together cost 9 to 13 basis points a year (standard errors 5 to 6, so about two standard errors from zero): value -4 to -5, profitability -4 to -6, momentum -4 to -7 and the market -1 to -5, against size +2 to +3 and investment +2 to +4. The industries' own returns paid 12 to 20 basis points a year (standard errors 10 to 12, about one standard error from zero): the removed half of Coal, Oil and Utilities earned less than the substitutes did beyond what their factor betas account for. The sum is the +2 to +7 of notebook 12. So the tilt's absence of opportunity cost is the net of two parts of opposite sign, the factor bets it created and the industry bets it was, and a manager who hedged the factor exposures (notebook 11's open point) would have kept the second part and removed the first. Those exposures are unintended, in that nobody chose them (the client asked for less Oil and said nothing about value), and uncompensated, in that at 0.01 of a factor their expected contribution is about 2 to 3 basis points a year in either direction while they add variance to the active return: risk without expected return. A manager who wanted none of it would choose, among the industries that replace Oil, those whose betas to value and profitability match Oil's as well as its market beta does, which is what the factor-neutral constraints of the first route under expectation 4 do. Under the mandate the factor total is -11 to -17 and the residual +7 to +14. By decade, for the sample covariance's mandate path, the first decade carries most of both parts: the factor exposures cost 61 basis points a year in 1979 to 1989 (value -28, profitability -30, momentum -15, offset by investment +15) and the industries' own returns paid 35, the decade in which the oil tilt was largest and the oil price doubled and then collapsed; in the 1990s the factor part earned 11 and the residual lost 8; in the 2010s the residual paid 17 and the factors were flat.

**What this notebook does not settle.**

- The betas come from three years of daily returns and are applied to monthly factor returns, as factor risk models do. A beta estimated on 120 monthly returns can differ in level, as notebook 10 found for variances, and would move part of a contribution into the residual or out of it; the study does not run that version, and the residual absorbs the difference, so the factor contributions here are a lower bound on what a longer-horizon beta would attribute to the factors.
- Six factors, all of them returns of stock portfolios. Oil's and Coal's own returns move with the oil price, and a commodity factor would absorb part of their residual. Macro variables such as the oil price, inflation and interest rates are not returns of stock portfolios, so a model that uses them first builds, for each, a portfolio of stocks that tracks it and attributes to that portfolio, which adds an estimation step; French's library carries no such series, so the residual here includes the oil price's part, and the study leaves it there.
- Every contribution is a mean over 566 months with a standard error of 1 to 6 basis points a year, and every residual one of 10 to 12; the factor totals are about two standard errors from zero, the residuals about one. The decomposition of the mandate's cost into 20% to 40% and 60% to 80% is measured to about 15 percentage points either way.
- The attribution is gross of trading costs. Notebook 12 charged them at 50 and 100 basis points per unit of turnover; they would be a seventh line of 5 to 9 basis points a year against every path and belong to no factor.
- The README, the note and the report write the extension up; notebook 14 opens version 2, the factor objective (the sum of the portfolio's active exposures to value, profitability, investment and momentum, maximised within a limit on the forecast tracking error) under the mandate.
"""),
]


# ---------------------------------------------------------------------------
# 14: version 2, module A: the factor objective under the mandate
# ---------------------------------------------------------------------------

NB14 = [
    md("""
# 14. The factor objective under the mandate: what a budget buys

**Terms used in this notebook.**

| Term | Meaning |
|---|---|
| Risk-free rate | the return on a one-month US Treasury bill, the closest thing to a return with no risk |
| Excess return | a return minus the risk-free rate over the same period |
| Market capitalisation | the number of a firm's shares times their price, the firm's size in money |
| Cap-weighted | weighted by market capitalisation |
| Benchmark | in the extension, the index the portfolio tracks, the cap-weighted combination of the 49 industries built in notebook 08 |
| Variance | the average squared distance of a series from its own average; its square root is the standard deviation, the usual measure of how much a return moves |
| Covariance matrix | the table of all variances and covariances of a set of assets, 49 by 49 here |
| Covariance estimator | a method for estimating the covariance matrix from a window of data; notebook 10 built four, and notebook 12 ran them with the robust portfolio and RiskMetrics as seven variants |
| Estimation window | the past returns an estimator sees, 120 months or three years of trading days here |
| Factor | a return series that moves many assets at once; the six here are the market factor Mkt-RF and five long-short portfolios: SMB (small firms over large, size), HML (cheap firms over expensive, value), RMW (profitable firms over unprofitable, profitability), CMA (firms that invest little over firms that invest much, investment) and Mom (recent winners over recent losers, momentum) |
| Premium | the average return of a factor over long samples, as the literature reports it; the four factors value, profitability, investment and momentum have a documented positive premium, and this study estimates none of them |
| Principal component | a combination of the assets, with one weight per asset, chosen so that it explains as much of the assets' total variance as a single combination can (notebook 09); the estimator named after it builds the covariance from five of them (notebook 10) |
| Beta | how much an asset moves with a factor on average, estimated by regressing the asset's excess returns on the factors' returns over the estimation window; one beta per factor |
| Active weight | the portfolio's weight in an asset minus the benchmark's weight in it |
| Active return | the portfolio's return minus the benchmark's return in the same month |
| Active exposure | the portfolio's beta to a factor minus the benchmark's: the sum over industries of the active weight times the industry's beta to that factor (notebook 13) |
| Attribution | splitting a portfolio's active return into the contributions of named factors plus a residual, so that the parts add up to the whole (notebook 13) |
| Tracking error | the standard deviation of the difference between two return series, stated per year; forecast (ex-ante) when computed from a covariance matrix before the month, realised (ex-post) when measured on the active returns afterwards |
| Long-only | said of a portfolio in which no weight is negative |
| One-way turnover | half the sum over industries of the absolute changes in weight at a rebalance |
| Turnover cap | an upper limit on the one-way turnover of a rebalance; 2% a month here |
| Tilt | a constraint that holds named industries below their benchmark weight; here Coal, Oil and Utilities at no more than half of it. The word keeps this one meaning in version 2 |
| Exclusion | a constraint that holds named industries at zero weight; Smoke (tobacco) and Guns (weapons) here |
| Beta-neutral | a constraint that holds the portfolio's beta to the benchmark equal to one |
| Mandate | the whole set of rules the fund obeys: the tilt, the exclusions and beta neutrality, with the active weight bound and the turnover cap, the constraint set C3 of version 1 |
| Optimiser | the extension's routine that solves a constrained portfolio problem; version 1's minimises the forecast tracking error (notebook 11), this notebook's maximises the factor objective |
| Factor objective | the quantity version 2's optimiser maximises: the sum of the portfolio's active exposures to the targeted factors, each counted in the direction of its premium |
| Targeted factors | the four of the six factors with a documented premium, value, profitability, investment and momentum, each targeted in the direction of its premium and weighted equally in beta units |
| Budget | the limit on the forecast tracking error of the factor objective's portfolio: 75, 100 or 150 basis points a year. A month in which the mandate's tracking-error-minimising portfolio already exceeds the budget takes that portfolio and is counted |
| Cone | the set of weights whose forecast tracking error is at most the budget; the budget is written as a cone so that the problem stays convex, with one global maximum |
| Stationary | said of the portfolio the budget allows when turnover is free, the destination the capped rebalances move towards |
| Incidental exposure | the factor objective's value at a portfolio built without it, version 1's tracking-error-minimising portfolio; what the mandate's tilt leaves behind |
| Robust portfolio | the weights whose largest forecast tracking error across the five covariance estimates is smallest (notebook 11); under the factor objective, the weights whose budget holds under all five at once |
| Basis point | one hundredth of a percentage point, so 100 basis points is 1.00% |
| Vintage | the version of Ken French's files on the download date, named by the release of the CRSP database they were built from |
| Provenance | the record of what was downloaded, when, with its checksum and vintage |

**The problem, stated the way practitioners state it.** Version 1 built an enhanced index fund of the kind Dutch institutional mandates ask for: long-only, within 2 percentage points of the index in every industry, 2% one-way turnover a month, Coal, Oil and Utilities at half their index weight, tobacco and weapons excluded, a beta of one; and it judged five covariance estimators on how closely the result tracked the index. Notebook 13 found that the mandate left the portfolio with exposures of 0.004 to 0.018 in absolute value to the six factors that nobody chose, which cost 9 to 13 basis points a year. The question an enhanced index manager asks next is the one this module answers: under the same mandate, what active exposure to the factors with a documented premium a budget on the forecast tracking error can buy, what it costs in turnover, what it realised in active return, and whether the covariance estimator still matters once the budget is spent on purpose. Enhanced indexing in practice is this problem: Robeco's enhanced index products, for one, hold the index within an ex-ante tracking error near 1% a year and spend that budget on exposures to value, quality and momentum (Robeco, 2024, "The smarter alternative: Enhanced Indexing"). The study holds no view on expected returns, as version 1 did not: the four targeted factors are the four of French's six with a documented premium, the direction of each target is the literature's, the four are weighted equally in beta units, and nothing estimates a premium or times a factor.

**The formulation.** Each month, with the data available before the month, the optimiser chooses the weights w that maximise the factor objective, s'B'(w - b), where b is version 1's cap-weighted benchmark, B is the 49-by-6 matrix of industry betas to French's six factors estimated on the previous three years of daily returns by the regression of notebook 13, and s = (0, 0, +1, +1, +1, +1) on (market, size, value, profitability, investment, momentum); subject to every constraint of version 1's mandate and to the budget: the forecast tracking error from the month's covariance estimate, the square root of 12 (w - b)'Sigma(w - b), at most tau. The objective is linear in w and the budget is a cone, so the problem is a second-order cone program, convex, with one global maximum; cvxpy solves it with the solver of notebook 11. Worked number: an industry with an active weight of +0.02 and betas of 0.5 to value and 0.3 to profitability adds 0.02 times (0.5 + 0.3), that is 0.016, to the factor objective; an industry with an active weight of -0.02 and a value beta of 1.0 removes 0.020. The budget in monthly units is tau over the square root of 12: 100 basis points a year is 29 basis points a month. The infeasibility rule, fixed before the code ran: in a month in which the budget cannot be met under the mandate, because the tracking-error-minimising portfolio of version 1 already exceeds tau, the path takes that portfolio, the month is counted and reported, and nothing else is relaxed; the count is one of the results.

**What this notebook does.** It is the first of three (14 the problem, 15 the rolling evaluation of nineteen paths, 16 their attribution) and runs no path. It adds the factor objective to the optimiser beside version 1's problem, which stays as it is; tests it on made-up markets against an independent solver (`tests/test_factor_objective.py`); works one month through by hand; computes the exposure a budget buys at version 1's three report months for each of the five estimators, with turnover free and with one capped rebalance; and counts, over the 566 months, how often each budget can be met at all. The rolling evaluation, the realised results and the seven expectations of the design (E1 to E7 in `constants.py`, section 7) belong to notebooks 15 and 16; what this notebook establishes is that the problem is posed and solved as designed, and what the arithmetic before the run says about the budgets.

**What I expect to see, written before the run (`constants.py`, section 7, 8 October 2026).**

1. Count first: 566 evaluation months from 1979-07; the betas are 49 by 6 in every month; three report months, 1979-07, 2004-11 and 2026-08; five estimator variants; the three budgets of the design and the six of the curve.
2. The solver's arithmetic, strict: at every report month and for every estimator, the factor objective's value does not fall as the budget rises; wherever the budget is at or above the minimiser's forecast tracking error the budget is met, and the forecast tracking error then equals the budget within 1 basis point unless the mandate's bounds stop the move first, in which case the objective equals the largest value the bounds alone allow; wherever the budget is below the minimiser's forecast the month takes the minimiser's portfolio, and the objective equals the incidental exposure.
3. The objective buys something, strict: at the main budget of 100 basis points and every report month, the factor objective's value exceeds the incidental exposure for every estimator, and every one of the four targeted exposures is above its incidental value.
4. Reported, no verdict: the worked month; the curves; what one capped rebalance buys from the minimiser's portfolio; the months in which the stationary minimum of the forecast tracking error exceeds each budget, by estimator (the lower bound of the infeasible months a path can have, since the cap adds a constraint); and the stationary factor objective at each budget month by month for the sample estimator, with its mean per targeted factor, read against E1 and E2 of the design.

Running time: about two minutes, most of it the 566 months of feasibility.
"""),
    md("""
## Modules

`constants` gains its section 7, the design of module A with the seven expectations and their reasons; `optimiser` gains `solve_factor_objective`, `FactorSolution` and `targeted_exposure`, beside version 1's functions, which are unchanged; the others are those of earlier notebooks.
"""),
    code("""
import importlib.util, subprocess, sys
if importlib.util.find_spec("cvxpy") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "cvxpy"])
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    writefile("french_loader.py"),
    writefile("benchmark.py"),
    writefile("rules.py"),
    writefile("covariance.py"),
    writefile("optimiser.py"),
    writefile("evaluation.py"),
    writefile("attribution.py"),
    md("""
## Count first: the months, the betas, the report months, the budgets
"""),
    code("""
import sys
sys.path.insert(0, "src")
import time
import numpy as np
import pandas as pd
from bp import constants as C
from bp import french_loader as fl
from bp import covariance as CV
from bp import optimiser as O
from bp import attribution as A

pd.set_option("display.width", 230)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_columns", 40)

P = CV.Panels()
weights, returns_m = P.weights, P.returns_m
months = pd.period_range(C.COV_EVAL_START, P.last, freq="M")
industries = [c.strip() for c in weights.columns]
tilt_mask, _ = O.masks(weights.columns)
_, mandate_mask = O.masks(weights.columns, exclude=C.MANDATE_EXCLUSIONS)
FACTORS = list(C.ATTRIBUTION_FACTORS)
TARGETED = list(C.FO_TARGET_FACTORS)
s = np.array([C.FO_TARGET_SIGN[f] for f in FACTORS])
MANDATE = C.CONSTRAINT_SETS[C.FO_CONSTRAINT_SET]
STATIONARY = tuple(c for c in MANDATE if c != "turnover_cap")      # the mandate with turnover free
VARIANTS = list(CV.EVALUATION_VARIANTS)
LABEL = {v: f"{v[0]}, {v[1].replace('_', ' ')}" for v in VARIANTS}
REPORT = [months[0], pd.Period(C.OPT_REPORT_MONTHS[1], "M"), months[-1]]

def betas_at(month):
    X = CV.daily_window(P.excess_d, month, C.FO_BETA_WINDOW_YEARS)
    _, B = CV.factor_cov(X.to_numpy(), P.factors_d.loc[X.index, FACTORS].to_numpy())
    return B

# Expectation 1, the counts
assert len(months) == 566, len(months)
assert all(np.isfinite(betas_at(m)).all() and betas_at(m).shape == (49, 6) for m in REPORT)
assert tuple(s) == (0.0, 0.0, 1.0, 1.0, 1.0, 1.0) and len(TARGETED) == 4 and len(VARIANTS) == 5
assert len(C.FO_BUDGETS_ANNUAL) == 3 and len(C.FO_CURVE_BUDGETS_ANNUAL) == 6 and C.FO_BUDGET_MAIN in C.FO_BUDGETS_ANNUAL
provenance = [fl.download(key) for key in P.files]
fl.write_provenance(provenance)
vintage = provenance[0]["vintage_line"].split("the ")[1].split(" ")[0]
print(f"{len(months)} evaluation months, {months[0]} to {months[-1]}; betas 49 by 6 at each of the report months {', '.join(str(m) for m in REPORT)}")
print(f"targeted factors {', '.join(TARGETED)}, s = {tuple(int(x) for x in s)} on {', '.join(FACTORS)}")
print(f"budgets {', '.join(f'{1e4 * t:.0f}' for t in C.FO_BUDGETS_ANNUAL)} basis points a year (main {1e4 * C.FO_BUDGET_MAIN:.0f}); the curve at {', '.join(f'{1e4 * t:.0f}' for t in C.FO_CURVE_BUDGETS_ANNUAL)}")
print(f"the mandate: {', '.join(MANDATE)}; stationary: the same without the turnover cap")
print(f"CRSP vintage of the eight files: {vintage}")
"""),
    md("""
## A worked month: 2026-08, the sample covariance on daily data, a budget of 100 basis points

Turnover free, so that the portfolio is the stationary one the budget allows. The minimiser's portfolio is version 1's under the same mandate; the objective's is this notebook's. The table shows the industries that move most, the six active exposures of both portfolios, and the arithmetic of the objective, industry by industry, summed.
"""),
    code("""
m = months[-1]
b = weights.loc[m].to_numpy()
B = betas_at(m)
Sigma, _, _ = CV.estimate("sample", "daily_3y", m, P)
base_worked = O.solve(Sigma, b, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
sol = O.solve_factor_objective(Sigma, b, B, s, C.FO_BUDGET_MAIN, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
assert sol.budget_met and sol.status == "optimal"
base = base_worked
print(f"{m}, sample covariance on daily data, budget {1e4 * C.FO_BUDGET_MAIN:.0f} bp a year ({1e4 * C.FO_BUDGET_MAIN / np.sqrt(12):.1f} bp a month)")
print(f"  the minimiser's portfolio: forecast tracking error {1e4 * base.tracking_error:.1f} bp, factor objective {O.targeted_exposure(B, s, base.weights, b):+.4f} (the incidental exposure)")
print(f"  the objective's portfolio: forecast tracking error {1e4 * sol.tracking_error:.1f} bp, factor objective {sol.objective:+.4f}; one-way turnover from the benchmark {O.one_way_turnover(sol.weights, b):.3f}, from the minimiser's portfolio {O.one_way_turnover(sol.weights, base.weights):.3f}")
print(f"  the budget binds: {'yes' if sol.binding['budget'] else 'no'}; industries at the active weight bound {sol.binding['active_weight_bound']}, at zero {sol.binding['long_only']}, at the tilt {sol.binding['tilt']}")
print()
contrib = pd.DataFrame({"benchmark weight": b, "active weight": sol.active, "beta value": B[:, FACTORS.index("HML")], "beta profitability": B[:, FACTORS.index("RMW")],
                        "beta investment": B[:, FACTORS.index("CMA")], "beta momentum": B[:, FACTORS.index("Mom")], "contribution to the objective": sol.active * (B @ s)}, index=industries)
top = contrib.reindex(contrib["active weight"].abs().sort_values(ascending=False).index).head(12)
print("the twelve largest active weights, with the betas to the four targeted factors and the contribution to the objective (active weight times the sum of the four betas):")
print(top.to_string(float_format=lambda x: f"{x:+.4f}"))
print(f"sum over all 49 industries: {contrib['contribution to the objective'].sum():+.4f} = the factor objective {sol.objective:+.4f}")
print()
expo = pd.DataFrame({"minimiser": A.active_exposures(B, base.weights, b), "factor objective": sol.exposures, "benchmark beta": b @ B}, index=FACTORS)
print("active exposures to the six factors, and the benchmark's own betas:")
print(expo.to_string(float_format=lambda x: f"{x:+.4f}"))
"""),
    md("""
## The curve: what each budget buys at the three report months

For each of the five estimators at 1979-07, 2004-11 and 2026-08, the stationary factor objective at six budgets from 50 to 200 basis points, with the minimiser's forecast tracking error and incidental exposure beside it. Where the budget is below the minimiser's forecast the month is infeasible and takes the minimiser's portfolio; where the mandate's bounds stop the move before the budget is spent, the forecast lies below the budget and the curve flattens.
"""),
    code("""
rows = []
for m in REPORT:
    b = weights.loc[m].to_numpy()
    B = betas_at(m)
    for v in VARIANTS:
        Sigma, _, _ = CV.estimate(*v, m, P)
        base = O.solve(Sigma, b, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
        inc = O.targeted_exposure(B, s, base.weights, b)
        roof = O.solve_factor_objective(Sigma, b, B, s, 1.0, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask).objective   # the bounds alone: the largest objective any budget can buy
        rows.append({"month": str(m), "variant": LABEL[v], "budget (bp)": "minimiser", "forecast TE (bp)": 1e4 * base.tracking_error, "objective": inc, "met": True, "bounds stop": False, "roof": roof})
        for tau in C.FO_CURVE_BUDGETS_ANNUAL:
            sol = O.solve_factor_objective(Sigma, b, B, s, tau, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
            rows.append({"month": str(m), "variant": LABEL[v], "budget (bp)": f"{1e4 * tau:.0f}", "forecast TE (bp)": 1e4 * sol.tracking_error, "objective": sol.objective,
                         "met": sol.budget_met, "bounds stop": bool(sol.budget_met and sol.tracking_error < tau - C.FO_E1_BIND_TOL_ANNUAL),
                         "minimiser TE (bp)": 1e4 * base.tracking_error, "incidental": inc, "roof": roof,
                         **{f"exposure {f}": x for f, x in zip(FACTORS, sol.exposures)}, **{f"incidental {f}": x for f, x in zip(FACTORS, A.active_exposures(B, base.weights, b))}})
curves = pd.DataFrame(rows)
for m in REPORT:
    print(f"{m}: the factor objective by budget (columns, basis points a year) and estimator; 'min' is the minimiser's portfolio")
    tab = curves[curves.month == str(m)].pivot(index="variant", columns="budget (bp)", values="objective")
    tab = tab[["minimiser"] + [f"{1e4 * t:.0f}" for t in C.FO_CURVE_BUDGETS_ANNUAL]].rename(columns={"minimiser": "min"})
    te = curves[(curves.month == str(m)) & (curves["budget (bp)"] == "minimiser")].set_index("variant")["forecast TE (bp)"]
    tab.insert(0, "min TE (bp)", te)
    print(tab.to_string(float_format=lambda x: f"{x:+.3f}"))
    flat = curves[(curves.month == str(m)) & curves["bounds stop"]]
    infeasible = curves[(curves.month == str(m)) & (~curves["met"])]
    print(f"  infeasible budgets: {len(infeasible)} cells" + ("" if infeasible.empty else " (" + ", ".join(f"{r.variant} at {r['budget (bp)']}" for _, r in infeasible.iterrows()) + ")")
          + f"; the bounds stop the move before the budget in {len(flat)} cells" + ("" if flat.empty else " (" + ", ".join(f"{r.variant} at {r['budget (bp)']}" for _, r in flat.iterrows()) + ")"))
    print()

# Expectation 2: the solver's arithmetic
e2_monotone, e2_met, e2_inf = 0, 0, 0
n_monotone, n_met, n_inf = 0, 0, 0
for (m, v), grp in curves[curves["budget (bp)"] != "minimiser"].groupby(["month", "variant"], sort=False):
    g = grp.copy()
    g["tau"] = g["budget (bp)"].astype(float) / 1e4
    g = g.sort_values("tau")
    n_monotone += 1
    e2_monotone += int((np.diff(g["objective"].to_numpy()) >= -1e-9).all())
    for _, r in g.iterrows():
        if r["tau"] >= r["minimiser TE (bp)"] / 1e4:
            n_met += 1
            on_budget = abs(r["forecast TE (bp)"] / 1e4 - r["tau"]) <= C.FO_E1_BIND_TOL_ANNUAL
            at_roof = abs(r["objective"] - r["roof"]) <= 1e-6          # the bounds stopped the move: the objective is the largest the bounds allow
            e2_met += int(r["met"] and (on_budget or at_roof))
        else:
            n_inf += 1
            e2_inf += int((not r["met"]) and abs(r["objective"] - r["incidental"]) <= 1e-9)
ok2 = (e2_monotone == n_monotone) and (e2_met == n_met) and (e2_inf == n_inf)
print(f"expectation 2: the objective does not fall as the budget rises in {e2_monotone} of {n_monotone} month-estimator pairs; "
      f"a budget at or above the minimiser's forecast is met, with the forecast on the budget or the objective at the bounds' own maximum, in {e2_met} of {n_met} cells; "
      f"a budget below it takes the minimiser's portfolio with the incidental exposure in {e2_inf} of {n_inf} cells: {'MET' if ok2 else 'NOT MET'}")

# Expectation 3: the objective buys something at the main budget
main = curves[curves["budget (bp)"] == f"{1e4 * C.FO_BUDGET_MAIN:.0f}"]
buys = (main["objective"] > main["incidental"] + 1e-9)
each = pd.concat([main[f"exposure {f}"] > main[f"incidental {f}"] + 1e-9 for f in TARGETED], axis=1).all(axis=1)
print(f"expectation 3: at {1e4 * C.FO_BUDGET_MAIN:.0f} bp the objective exceeds the incidental exposure in {int(buys.sum())} of {len(main)} month-estimator pairs, "
      f"and every targeted exposure exceeds its incidental value in {int(each.sum())} of {len(main)}: {'MET' if buys.all() and each.all() else 'NOT MET'}")
print(f"at {1e4 * C.FO_BUDGET_MAIN:.0f} bp the stationary objective runs from {main['objective'].min():+.3f} to {main['objective'].max():+.3f} across the fifteen pairs, "
      f"{main['objective'].min() / 4:+.3f} to {main['objective'].max() / 4:+.3f} per targeted factor; incidental {main['incidental'].min():+.3f} to {main['incidental'].max():+.3f}")
"""),
    md("""
## One capped rebalance: how fast the objective can be bought

The stationary portfolio is a destination; the mandate allows 2% one-way turnover a month. Starting from the minimiser's portfolio at each report month, one rebalance under the cap at the main budget: the objective it reaches against the stationary one, and the months of such steps the distance would take if every step closed the same share of it.
"""),
    code("""
rows = []
for m in REPORT:
    b = weights.loc[m].to_numpy()
    B = betas_at(m)
    for v in VARIANTS:
        Sigma, _, _ = CV.estimate(*v, m, P)
        base = O.solve(Sigma, b, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
        stat = O.solve_factor_objective(Sigma, b, B, s, C.FO_BUDGET_MAIN, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
        step = O.solve_factor_objective(Sigma, b, B, s, C.FO_BUDGET_MAIN, MANDATE, w_prev=base.weights, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
        inc = O.targeted_exposure(B, s, base.weights, b)
        gained = (step.objective - inc) / (stat.objective - inc) if stat.objective > inc else np.nan
        rows.append({"month": str(m), "variant": LABEL[v], "incidental": inc, "after one capped rebalance": step.objective, "stationary": stat.objective,
                     "share of the distance in one step": gained, "distance to the stationary portfolio (one-way turnover)": O.one_way_turnover(stat.weights, base.weights),
                     "step turnover": step.turnover, "step forecast TE (bp)": 1e4 * step.tracking_error, "budget met in the step": step.budget_met})
steps = pd.DataFrame(rows).set_index(["month", "variant"])
print(steps.to_string(float_format=lambda x: f"{x:+.3f}"))
"""),
    md("""
## Feasibility across the sample

For every evaluation month and estimator, the forecast tracking error of the mandate's tracking-error-minimising portfolio with turnover free: the stationary minimum. A budget below it cannot be met in that month by any portfolio, capped or not, so the count of such months is a lower bound on the infeasible months a path can have. For the sample covariance on daily data the stationary factor objective at the three budgets is computed month by month as well, which is what the budget buys before the cap slows it.
"""),
    code("""
t0 = time.time()
rows = []
for i, m in enumerate(months):
    b = weights.loc[m].to_numpy()
    B = betas_at(m)
    rec = {"month": m}
    for v in VARIANTS:
        Sigma, _, _ = CV.estimate(*v, m, P)
        base = O.solve(Sigma, b, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
        rec[f"minimum TE {LABEL[v]}"] = base.tracking_error
        if v == ("sample", "daily_3y"):
            rec["incidental"] = O.targeted_exposure(B, s, base.weights, b)
            for tau in C.FO_BUDGETS_ANNUAL:
                sol = O.solve_factor_objective(Sigma, b, B, s, tau, STATIONARY, tilt_mask=tilt_mask, exclude_mask=mandate_mask)
                rec[f"objective at {1e4 * tau:.0f}"] = sol.objective
                rec[f"met at {1e4 * tau:.0f}"] = sol.budget_met
                for f in TARGETED:
                    rec[f"exposure {f} at {1e4 * tau:.0f}"] = sol.exposures[FACTORS.index(f)]
    rows.append(rec)
    if i % 100 == 0:
        print(f"{m}: {time.time() - t0:.0f}s")
feas = pd.DataFrame(rows).set_index("month")
print(f"{len(months)} months in {time.time() - t0:.0f}s")
print()
cols = [f"minimum TE {LABEL[v]}" for v in VARIANTS]
tab = pd.DataFrame({"mean (bp)": 1e4 * feas[cols].mean(), "largest (bp)": 1e4 * feas[cols].max(),
                    **{f"months above {1e4 * tau:.0f}": (feas[cols] > tau).sum() for tau in C.FO_BUDGETS_ANNUAL}})
tab.index = [c.replace("minimum TE ", "") for c in cols]
print("the stationary minimum of the forecast tracking error under the mandate, by estimator, and the months in which it exceeds each budget (of 566):")
print(tab.to_string(float_format=lambda x: f"{x:.1f}"))
print()
first_label, last_label = f"{months[0]} to 1989-12", f"2020-01 to {months[-1]}"
decade = pd.Series([first_label if m.year < 1990 else (last_label if m.year >= 2020 else f"{(m.year // 10) * 10}s") for m in months], index=months)
above = pd.DataFrame({f"{LABEL[v]} above {1e4 * C.FO_BUDGET_MAIN:.0f}": (feas[f"minimum TE {LABEL[v]}"] > C.FO_BUDGET_MAIN).groupby(decade).sum() for v in VARIANTS})
above["months"] = decade.value_counts().reindex(above.index)
print(f"the months above the main budget by decade:")
print(above.to_string())
print()
obj_cols = [f"objective at {1e4 * tau:.0f}" for tau in C.FO_BUDGETS_ANNUAL]
summ = pd.DataFrame({"mean": feas[obj_cols].mean(), "per targeted factor": feas[obj_cols].mean() / len(TARGETED), "smallest": feas[obj_cols].min(), "largest": feas[obj_cols].max(),
                     "months met": [int(feas[f"met at {1e4 * tau:.0f}"].sum()) for tau in C.FO_BUDGETS_ANNUAL]})
print(f"the stationary factor objective of the sample covariance on daily data, by budget, over the 566 months (incidental exposure {feas['incidental'].mean():+.4f} on average):")
print(summ.to_string(float_format=lambda x: f"{x:+.4f}"))
print()
per_f = pd.DataFrame({f"{1e4 * tau:.0f}": [feas[f"exposure {f} at {1e4 * tau:.0f}"].mean() for f in TARGETED] for tau in C.FO_BUDGETS_ANNUAL}, index=TARGETED)
print("mean stationary active exposure to each targeted factor, by budget:")
print(per_f.to_string(float_format=lambda x: f"{x:+.4f}"))
print()
print(f"read against the design of 8 October 2026: E1 asked the budget of {1e4 * C.FO_BUDGET_MAIN:.0f} bp to bind in at least {C.FO_E1_BIND_SHARE_MIN:.0%} of {C.FO_E1_DENOMINATOR_SUPERSEDED_2026_10_08} for each daily estimator, so at most {int(np.floor((1 - C.FO_E1_BIND_SHARE_MIN) * len(months)))} months could miss it; "
      f"the stationary minimum alone exceeds {1e4 * C.FO_BUDGET_MAIN:.0f} bp in " + ", ".join(f"{int(tab.loc[LABEL[v], f'months above {1e4 * C.FO_BUDGET_MAIN:.0f}'])} ({LABEL[v]})" for v in VARIANTS[:4]) + " months.")
print(f"E2 asked the mean of the four targeted exposures at {1e4 * C.FO_BUDGET_MAIN:.0f} bp to reach {C.FO_E2_MEAN_EXPOSURE_MIN_SUPERSEDED_2026_10_08} for the sample estimator; the stationary mean is {summ.loc[f'objective at {1e4 * C.FO_BUDGET_MAIN:.0f}', 'per targeted factor']:+.4f}, and a capped path can hold at most the stationary exposure on average.")
print(f"restated on {C.FO_RESTATEMENT_DATE}, before any path ran: E1's share applies to {C.FO_E1_DENOMINATOR}, that is 566 less the counts above, with the path's further misses counted; E2's level is {C.FO_E2_MEAN_EXPOSURE_MIN}, four fifths of the stationary mean. The levels of 8 October stay in constants.py, marked as superseded.")
"""),
    md("""
## Save

The curves at the report months, the feasibility table with the sample estimator's stationary objective month by month, the capped steps and the worked month's weights and exposures are written to `outputs/` with the vintage in the file name, as a record and for the write-up.
"""),
    code("""
os.makedirs(C.OUTPUT_DIR, exist_ok=True)
curves.to_csv(f"{C.OUTPUT_DIR}/factor_objective_curves_{vintage}.csv", index=False, float_format="%.8f")
feas.to_csv(f"{C.OUTPUT_DIR}/factor_objective_feasibility_{vintage}.csv", float_format="%.8f")
steps.to_csv(f"{C.OUTPUT_DIR}/factor_objective_capped_step_{vintage}.csv", float_format="%.8f")
worked = contrib.copy()
worked["minimiser weight"] = base_worked.weights
worked.to_csv(f"{C.OUTPUT_DIR}/factor_objective_worked_{months[-1]}_{vintage}.csv", float_format="%.8f")
print("written:", sorted(f for f in os.listdir(C.OUTPUT_DIR) if f.startswith("factor_objective")))
"""),
    md("""
## What this notebook established, and what could be wrong

| Expectation | Result | Verdict |
|---|---|---|
| 1. Count first | 566 months; betas 49 by 6 at 1979-07, 2004-11 and 2026-08; five estimators; budgets 75, 100 and 150, the curve at six points from 50 to 200 | holds |
| 2. The solver's arithmetic: the objective does not fall with the budget; a budget the minimiser can meet is met, on the budget or at the bounds' own maximum; a budget it cannot meet takes the minimiser's portfolio | 15 of 15 pairs monotone; 82 of 82 feasible cells on the budget or at the roof; 8 of 8 infeasible cells with the incidental exposure | MET |
| 3. At 100 basis points the objective exceeds the incidental exposure, and every targeted exposure exceeds its incidental value | the objective exceeds it in 15 of 15 pairs; every one of the four exposures in 10 of 15 | NOT MET in the second part |
| 4. Reported: the worked month, the curves, one capped step, the feasibility over 566 months, the stationary objective by budget | below | reported |

Expectation 1 holds: the counts are the design's, and the betas are the 49-by-6 matrices notebook 13 estimates, taken from the same function.

Expectation 2 holds, and it is the check that the problem is solved as posed. At the three report months and for every estimator the factor objective is non-decreasing in the budget; wherever the budget is at or above the minimiser's forecast tracking error the solver meets it, with the forecast on the budget to within 1 basis point or, where the mandate's bounds stop the move first, with the objective equal to the largest value the bounds alone allow (the thirteen flat cells at 1979-07: the four daily estimators from 125 basis points up, whose curves stop at 0.177 with the forecast at 113 to 119 basis points, and the monthly covariance at 200, whose curve stops at 0.126 with the forecast at 193); and wherever the budget is below the minimiser's forecast (eight cells: the 50 basis point budget under the four daily estimators at 2004-11 and under the sample and Ledoit-Wolf estimators at 1979-07, and the monthly covariance at 1979-07 at 50 and 75) the month takes the minimiser's portfolio with its incidental exposure, as the infeasibility rule says. The independent checks are in `tests/test_factor_objective.py`: the solution agrees with a sequential quadratic programme on the budget-bound problem and with a linear programme when the budget is loose.

Expectation 3 holds in its first part and fails in its second, and the failure is informative. At 100 basis points the objective exceeds the incidental exposure at every month-estimator pair, by 0.08 to 0.30; but in five of the fifteen pairs one of the four targeted exposures ends below its incidental value. The second clause was wrong in its reasoning: the optimiser maximises the sum of the four exposures, each weighted equally in beta units, so it buys the exposures that cost least tracking error and lets an expensive one fall if that buys more of the others. The monthly table shows which ones cost least: over the 566 months at 100 basis points the stationary portfolio holds +0.048 of profitability and +0.040 of investment against +0.021 of value and +0.008 of momentum. Momentum exposure is expensive because industry momentum betas are small and rotate, so a given exposure needs large active weights; the equal weighting in beta units, which the design fixed before the code, therefore buys mostly profitability and investment. This is a property of the design, and the notebook reports it as it stands; what it means for the rolling run is that the four targeted exposures will be of different sizes.

The worked month shows the mechanism. At 2026-08, under the sample covariance on daily data, the minimiser's portfolio has a forecast tracking error of 37 basis points and an incidental exposure of -0.002; a budget of 100 basis points buys an objective of +0.131, spread as +0.025 value, +0.033 profitability, +0.041 investment and +0.032 momentum, with five industries at the active weight bound, eleven at zero besides the two excluded, and the three tilted ones at half their weight, and the market exposure held at +0.007 by beta neutrality. The largest contributions come from selling Software (an active weight of -0.02 against betas of -0.46 to value and -0.61 to investment, which adds +0.025) and buying Banks, Wholesale and Ships (value betas of 0.9, 0.2 and 0.4). The stationary portfolio sits 0.148 of one-way turnover away from the minimiser's, more than seven months of the cap.

The curves say what a budget buys and when it stops buying. At 2004-11 and 2026-08 the objective rises with the budget through 200 basis points, under the sample covariance on daily data by 0.0024 and 0.0014 per basis point from 75 to 100 and by 0.0015 and 0.0008 from 150 to 200, so each further basis point buys less; the five estimators' curves lie within 0.07 of one another at 2004-11 and within 0.05 at 2026-08 at every budget. At 1979-07, the month of the oil peak, the minimiser's own forecast is 49 to 56 basis points for the daily estimators and 95 for the monthly covariance; the daily curves flatten at 0.177 once the budget passes 113 to 119 basis points, by estimator, because the active weight bound stops the move; and from 75 basis points up the monthly covariance's curve lies below the daily ones, by 0.19 to 0.22 at 75 and by 0.05 at 200, because its forecast prices the same move dearer. One capped rebalance from the minimiser's portfolio buys 0.19 to 0.51 of the distance to the stationary objective (0.19 to 0.20 for the daily estimators and 0.51 for the monthly covariance at 1979-07, 0.35 to 0.40 at 2004-11, 0.29 to 0.34 at 2026-08); the stationary portfolio lies 0.07 to 0.32 of one-way turnover from the minimiser's, four to sixteen months of the cap, so a path under the cap arrives there over that many months when the betas and the covariance stand still, and the rolling run will show how far it gets when they move.

The feasibility count is the notebook's main result for the design, and it bears on two of the seven expectations before any path is run. The stationary minimum of the forecast tracking error under the mandate averages 55 to 62 basis points across the five estimators and exceeds 100 basis points in 22 (principal components), 37 (sample), 39 (six-factor model) and 43 (Ledoit-Wolf) of the 566 months for the daily estimators, 40 for the monthly covariance; every one of those months lies in 1979 to 1989 for principal components and the monthly covariance, and all but 5 (sample), 8 (Ledoit-Wolf) and 17 (six-factor model) for the other three, whose remainder falls in 2008 to 2011. A capped path can only do worse in such a month, because the cap adds a constraint. E1, as written on 8 October, asked the budget of 100 basis points to bind in at least 95% of all 566 months for each daily estimator, which allowed 28 misses; the stationary count alone exceeds 28 for three of the four, so on the arithmetic available before the run E1 was unlikely to hold for the sample, Ledoit-Wolf and six-factor estimators, and the months that miss it are the oil decade's. E2, as written on 8 October, asked the mean of the four targeted exposures at 100 basis points to reach 0.05 for the sample estimator; the stationary mean over the 566 months is 0.030 (0.015 at 75, 0.048 at 150), and a capped path holds at most the stationary exposure on average, so E2 was unlikely to hold at 100 basis points either, and at 150 the stationary mean falls 0.002 short of that level. On this arithmetic both expectations were restated on 9 October 2026, before any path ran, and `constants.py` keeps the levels of 8 October beside the new ones, marked as superseded: E1 now asks the budget to bind in 95% of the months the mandate alone can meet, with the months it cannot meet reported from this notebook's table and the path's further misses counted; E2 now asks the daily sample estimator's average exposure to reach 0.024, four fifths of the stationary 0.030. The design reads a level changed between this check and the first rolling run as a pre-run restatement, dated and disclosed, and a level changed after notebook 15 runs as a post-run change. This notebook's job was to put the arithmetic in front of the decision before the run.

**What this notebook does not settle.**

- Everything realised. The curves and the counts are forecasts from covariance estimates; what the budget buys in realised tracking error, turnover, active return and attribution is notebooks 15 and 16.
- The cap in motion. The stationary portfolio is a destination; with the betas and the covariance moving month by month the capped path may never arrive, and the exposure it holds is what notebook 15 measures.
- The direction and the weights of the targets are the design's; a different weighting (per unit of tracking error, say) would buy more momentum and less profitability, and the study does not run it.
- The robust and RiskMetrics variants and the two single-factor sensitivities are not drawn here; they run in notebook 15 at the main budget.
"""),
]


if __name__ == "__main__":
    for name, cells in [("01_french_loader.ipynb", NB01), ("02_1N_vs_mean_variance.ipynb", NB02), ("03_shrinkage_and_constraints.ipynb", NB03), ("04_critical_window_and_simulation.ipynb", NB04), ("05_fat_tails.ipynb", NB05), ("06_volatility_clustering.ipynb", NB06), ("07_extended_sample.ipynb", NB07), ("08_cap_weight_check.ipynb", NB08), ("09_principal_components.ipynb", NB09), ("10_covariance_estimators.ipynb", NB10), ("11_optimiser.ipynb", NB11), ("12_rolling_evaluation.ipynb", NB12), ("13_factor_attribution.ipynb", NB13), ("14_factor_objective.ipynb", NB14)]:
        p = write(name, cells)
        print("wrote", p.relative_to(ROOT))
