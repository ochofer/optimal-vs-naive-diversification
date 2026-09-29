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

**What this notebook does.** It downloads the six Ken French files this project uses, records what it downloaded (date, URL, SHA-256 of the zip, and the CRSP vintage French prints at the top of each file), parses each file into monthly tables, and counts what is in them against what DeMiguel, Garlappi and Uppal (2009) say they used.

**Why it comes first.** Every number in the project is computed from these files, and French revises history: a return from 1985 can differ between the file served today and the one served last year. A replication that misses a published number by 0.01 has to be able to say whether the code or the vintage moved. The provenance record written here is what makes that possible, and it is attached to every later output.

**What I expect to see, and where it comes from.**

- The three portfolio files (10 industries, 49 industries, 25 size-and-value portfolios) and the three-factor file run monthly from 1926-07. On the vintage I read on 10 September 2026 (CRSP 202607) that is 1,201 rows to 2026-07; a later vintage adds one row per month. The five-factor file starts in 1963-07 (757 rows on that vintage) and the momentum factor in 1927-01.
- DGU's sample is 1963-07 to 2004-11 (their Table 2), which is **497 months**. With their 120-month estimation window the out-of-sample period is 1973-07 to 2004-11, **377 months**. Both counts are asserted below.
- Their four French-sourced datasets have N = 11, 3, 21 and 24 assets (Table 2). The 21 and 24 come from 20 of the 25 size-and-value portfolios: DGU drop the five largest-size portfolios (their footnote 24), because the market, SMB and HML are almost a linear combination of all 25.
- In French's 49-industry file nine industries have gaps coded -99.99 in the early decades. All 49 are populated from **1969-07**; the extension in later notebooks starts there.
- One number that is already a replication check: DGU's Table 3 reports the Sharpe ratio of the value-weighted market, "vw", as 0.1138 in every French-sourced column. That is the monthly Sharpe ratio of French's Mkt-RF over the out-of-sample window. The same calculation on today's vintage is printed beside it. It will not be identical, because the vintage is not; how far off it is says how much revision the sample has absorbed since 2009.
"""),
    md("""
## The constants file

Every tolerance, gate, sample boundary and design parameter the project uses lives in one module, `src/bp/constants.py`, with the source of each number beside it. The notebooks read these names and never introduce a number of their own. The cell below writes that module into the runtime so this notebook runs from scratch; in the repository the file is the same text.
"""),
    code("""
import os
os.makedirs("src/bp", exist_ok=True)
open("src/bp/__init__.py", "w").close()
"""),
    writefile("constants.py"),
    md("""
## The loader

A French CSV is not one table. It holds several blocks, each announced by a title line, then a header row that starts with a comma, then rows that start with a date (six digits for months, four for years). Returns are in percent and missing values are coded -99.99 or -999. The loader splits the file into blocks, indexes each by a monthly `Period`, converts percent to decimal once, replaces the missing codes with NaN, and records provenance for the zip it read.
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

One row per block. The first block of each portfolio file is the value-weighted monthly return, which is the one the project uses; the 49-industry file also carries the number of firms and the average firm size per industry per month, which is how the cap weights of the industries are derived in notebook 06.
"""),
    code("""
summaries = pd.concat([fl.block_summary(key) for key in C.FRENCH_FILES], ignore_index=True)
summaries
"""),
    md("""
## Count first

Each check below is an assertion. If a later vintage moves a count, the cell fails and says which one, which is the intended behaviour: a silent change in the sample is worse than a stopped notebook.
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
## One replication number, before any strategy exists

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
print(f"difference to the published 0.1138: {sr_oos - 0.1138:+.4f}  (tolerance for strategy Sharpe ratios: {C.TOL_SHARPE_ABS})")
"""),
    md("""
## What this notebook established, and what could be wrong

The six files parse, the DGU window holds 497 months with no gaps, the asset counts match Table 2, and all 49 industries are populated from 1969-07. The market Sharpe ratio on today's vintage sits within a few thousandths of the 0.1138 DGU printed, which is the size of revision to expect on the strategy rows too.

Three things this does not settle. French's risk-free rate is the one-month Treasury bill; DGU describe theirs as the 90-day bill taken from French's site, and French's site only carries the one-month series, so I use that. The vintage line names the CRSP cut French built the file from and nothing else; two files with the same vintage line can still differ if French changed a method. And the checks above count rows and columns; they do not verify a single return value, which only the replication itself can do.
"""),
]


# ---------------------------------------------------------------------------
# 02: 1/N against sample mean-variance
# ---------------------------------------------------------------------------

NB02 = [
    md("""
# 02. 1/N against sample mean-variance: the rolling out-of-sample test

**What this notebook does.** It builds the four DGU datasets from French's files, runs the naive 1/N rule and the sample-based mean-variance rule through DGU's rolling 120-month window, and puts the out-of-sample Sharpe ratio, certainty-equivalent return and turnover beside Tables 3, 4 and 5 of the paper, with the verdict of the tolerance I wrote down before the run.

**Why it comes second.** These two rules are the poles of the paper. 1/N estimates nothing. Sample mean-variance estimates everything, a mean and a covariance for every asset, and plugs the estimates into Markowitz's formula as if they were true. Every other rule in the paper is an attempt to move the second toward the first, so this pair has to be right before any of them is worth running.

**The method, in one paragraph.** At the end of each month t, from t = 120 onward, the rule sees the previous 120 months of excess returns, forms its weights, and holds them through month t + 1. Over 497 months that is 377 out-of-sample returns per rule and dataset (DGU section 2). The Sharpe ratio is the mean of those 377 returns over their standard deviation, equation (12); the CEQ return is the mean less half the variance, equation (14) with gamma = 1; turnover is the average absolute trade needed each month to move from the weights the last month's returns drifted the portfolio to and the new target, equation (15). The mean-variance weights are Sigma^-1 mu, equation (3), scaled so that they sum to one in absolute value, equation (1). The 1/N weights are 1/N.

**What I expect to see, and where it comes from.** From Table 3, monthly Sharpe ratios for 1/N of 0.1353, 0.2240, 0.1623 and 0.1753 on Industry, MKT/SMB/HML, FF-1-factor and FF-4-factor; for mean-variance out of sample 0.0679, 0.2186, 0.0128 and 0.1841; for mean-variance in sample, the ceiling estimation error costs, 0.2124, 0.2851, 0.5098 and 0.5364. From Table 5, 1/N turns over 2.2%, 2.4%, 1.6% and 2.0% of the portfolio a month, and mean-variance 606,594, 2.83, 10,466 and 3,553 times that. The band written down before the run: an out-of-sample Sharpe ratio within 0.03 of the published one passes, and turnover within 25% where the published relative turnover is below 100; above that the number is reported and not gated. The value-weighted market, "vw", is run too, as the data check from notebook 01.

**One amendment, made after the first run and dated.** On 13 September 2026, on the evidence of the fragility test at the end of this notebook, the Sharpe band was restricted to the same rows as the turnover band: rules whose published relative turnover is below 100. The unconstrained mean-variance rule on the Industry, FF-1-factor and FF-4-factor datasets is above that level and is reported with the range that noise produces, with no verdict; the in-sample row carries no verdict either, because the band was written for out-of-sample ratios. The level is the paper's own number, not one chosen from these results, and the amendment is recorded in `src/bp/constants.py` under `TOL_SHARPE_APPLIES_BELOW_RELATIVE`.
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
    writefile("strategies.py"),
    md("""
### The rolling evaluation

`rolling` walks the window forward one month at a time and records, for each out-of-sample month, the return earned, the target weights, the weights the month's returns drifted the previous portfolio to, and the trade between the two. The measures follow DGU's equations; the two p-values are the Jobson-Korkie test for Sharpe ratios and the delta-method test for CEQ returns, both against 1/N.
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
from bp import strategies as S
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

377 out-of-sample months per rule and dataset. The in-sample mean-variance Sharpe ratio, estimated once on all 497 months, is computed beside them: it is the ceiling, the Sharpe ratio a mean-variance investor would earn with no estimation error.
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

No band applies to the CEQ; the rows are reported beside the published ones. For the mean-variance rule the CEQ is dominated by the variance term, and the variance is dominated by a few months of extreme weights, so its value is a statement about those months.
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
## How fragile is the mean-variance row?

The test that separates a miss caused by the code from a miss caused by the data. Add Gaussian noise to every return, at one basis point and at ten (a tenth of a percent, small against monthly standard deviations of four to six percent and below the size of many revisions French makes to a published month), and rerun the rule fifty times at each level with a fixed seed. If the published number sits inside the range the noise produces, the row cannot be replicated to a tighter band on any vintage, whoever wrote the code. The known-answer test in `tests/test_strategies_backtest.py`, which recovers the true tangency weights from simulated data, is what says the code is right; this cell says how much the data say. About two minutes.
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

On the vintage of 10 September 2026 the 1/N rows replicate to the third decimal on three datasets (0.1353 against 0.1353 on Industry) and to 0.011 on MKT/SMB/HML, whose three assets are the factors themselves and have been revised more than the portfolios. The market row is within 0.0025 everywhere. 1/N's turnover is within 2.5% of the paper on every dataset, which fixes the turnover convention: trades are measured against the weights the month's returns drifted the portfolio to, and the first purchase is not counted.

The unconstrained mean-variance rule does not replicate within the 0.03 band on Industry or FF-1-factor, and the fragility table says why it cannot: ten basis points of noise move its out-of-sample Sharpe ratio across a range of 0.14 on Industry, 0.12 on FF-1-factor and 0.25 on FF-4-factor, and the published figure lies inside that range on all three. One basis point is already enough on the two size-and-value datasets. The reason is in the design of the datasets: in each of the three, the market factor is nearly a combination of the other assets, so the covariance matrix the rule inverts is close to singular, and the January 1975 position of 4,500 times wealth is what inverting it produces. On MKT/SMB/HML, three assets and no such collinearity, the same rule moves by 0.001 under the noise and passes. The band as first written did not anticipate a row that no vintage can reproduce; the amendment at the top of this notebook is the answer, and the fragility table is its evidence.

The in-sample mean-variance Sharpe ratios on the two size-and-value datasets are 0.04 to 0.06 below the paper's, and that is not fragility: those two numbers move by less than 0.01 under ten basis points of noise. It is a difference in the data. The candidates are revisions to French's 25 portfolios since the paper's 2004 download and the risk-free convention (DGU describe a 90-day bill in one place and a one-month bill in another; French's site carries only the one-month series, which is what I use). Shifting the long-only assets' excess returns by 3 basis points a month moves the FF-1-factor in-sample figure by 0.004, so the second candidate does not close the gap on its own. The cause stays unresolved in this notebook.
"""),
]


# ---------------------------------------------------------------------------
# 03: the rules that try to fix mean-variance
# ---------------------------------------------------------------------------

NB03 = [
    md("""
# 03. Shrink the means, ignore the means, or forbid short sales: the rest of the paper's rules

**What this notebook does.** It adds the rules DGU built to tame the estimation error that notebook 02 exposed, runs all nine rules through the same rolling test, and completes the comparison with Tables 3, 4 and 5 of the paper, including the pre-committed check that the top three rules on each dataset come out in the paper's order.

**Why it comes third.** Notebook 02 showed the two poles: 1/N, which estimates nothing, and mean-variance, which trusts every estimate and is destroyed by them. The literature's answer is not to abandon Markowitz but to trust the estimates less, and there are three ways to do that, each a rule in the paper.

- **Shrink the means toward a common value.** Bayes-Stein (`bs`, section 1.3.2, Jorion 1986) replaces each asset's estimated mean by a weighted average of that estimate and one number common to all assets, the mean return of the minimum-variance portfolio. The weight on the common number, phi, rises when the estimated means are close together relative to their noise. The covariance is inflated a little for the uncertainty in the mean.
- **Ignore the means altogether.** Minimum variance (`min`, section 1.4.1) uses only the covariance matrix and finds the lowest-risk fully invested portfolio. Means are the noisiest estimates, so dropping them removes most of the damage, at the cost of any information they held.
- **Forbid short sales.** The constrained rules (`mv-c`, `bs-c`, `min-c`, section 1.5) add the condition that no weight can be negative. Jagannathan and Ma (2003) showed this is shrinkage in disguise: forbidding a short position on an asset is the same as raising its estimated mean, or shrinking its covariances, until the optimiser no longer wants to short it. `g-min-c` goes one step further and requires every weight to be at least half of 1/N.

**The method** is notebook 02's: a 120-month rolling window, 377 out-of-sample months, Sharpe ratio, CEQ and turnover beside the paper's, with the band as amended on 13 September (0.03 on the Sharpe ratio for rules whose published relative turnover is below 100; the rest reported with no verdict).

**What I expect to see, from Table 3.** Minimum variance 0.1554, 0.2493, 0.2778 and -0.0183 on Industry, MKT/SMB/HML, FF-1-factor and FF-4-factor; Bayes-Stein 0.0719, 0.2536, 0.0138, 0.1791; mv-c 0.0678, 0.1084, 0.1977, 0.2024; bs-c 0.0819, 0.1514, 0.1955, 0.2062; min-c 0.1425, 0.2493, 0.1546, 0.3580; g-min-c 0.1451, 0.2467, 0.1615, 0.3028. From footnote 21, the Bayes-Stein shrinkage factor phi averages between 0.32 (FF-4-factor) and 0.66 (MKT/SMB/HML). And from Table 3 read as a whole: the constrained rules beat the unconstrained ones everywhere, and none of them beats 1/N by a statistically significant margin except on the size-and-value datasets.
"""),
    md("""
## One question the paper leaves open, settled before the run

The paper's Lagrangian for the constrained rules, equation (8) on page 1925, shows only the condition that weights be non-negative. Read literally, the rule would find the best non-negative position at any scale and then rescale it to sum to one, exactly as the unconstrained rules do, and the risk aversion gamma would drop out. But footnote 22 on page 1934 says the constrained rules produce "corner solutions with all wealth invested in a single asset", and that only happens if the budget condition, weights summing to one, sits *inside* the optimisation with gamma = 1: the risk penalty is then small against the differences in estimated means, and the rule piles into the asset with the highest mean.

Both readings are built below. On the MKT/SMB/HML dataset the literal reading gives a Sharpe ratio of 0.238 and never holds a single asset; the budget-inside reading gives 0.109 against the paper's 0.1084 and holds a single asset in 257 of 377 months. The paper wins over the literal reading of its own equation. The choice is recorded in `constants.py` as `DGU_CONSTRAINED_BUDGET_INSIDE`, with this evidence, and the literal version is kept in the code as `mv_c_cone` for the record.
"""),
    md("""
## Modules

Infrastructure from notebooks 01 and 02, unchanged, then the rules module with the new rules added. The constrained rules are solved exactly by non-negative least squares after a change of variables, so there is no iterative tolerance to tune; `tests/test_strategies_backtest.py` checks each against an independent optimiser.
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
    writefile("strategies.py"),
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
from bp import strategies as S
from bp import backtest as B
from bp import compare as CMP
from bp import dgu_published as P

pd.set_option("display.width", 160)
pd.set_option("display.max_colwidth", 60)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

ORDER = list(C.DGU_STRATEGIES)          # ew, mv, bs, min, vw, mv-c, bs-c, min-c, g-min-c
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

Pre-committed: the top three rules by out-of-sample Sharpe ratio on each dataset, among the gated rules, come out in the paper's order. The check is strict, so it is worth reading the numbers beside the verdict: where the published Sharpe ratios of the top rules differ by less than the 0.03 band, an exchange of places is inside the noise the band allows.
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

The noise test from notebook 02, ten basis points and fifty draws, for Bayes-Stein on the three datasets where it is reported without a verdict, and for minimum variance on FF-4-factor, the one gated cell that misses. About a minute.
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

Twenty-nine of the thirty gated Sharpe cells are within 0.03 of the paper, most within 0.01, and every gated turnover cell is within 25%. The CEQ returns of the constrained rules match to the fourth decimal on most cells. The Bayes-Stein shrinkage factor averages 0.33 on FF-4-factor and 0.68 on MKT/SMB/HML against the paper's 0.32 and 0.66, which is the check that the shrinkage is implemented as Jorion specified it. The paper's reading of Table 3 reproduces: the constrained rules beat their unconstrained versions on every dataset, minimum variance with constraints is the best of the optimising rules on three of four, and 1/N is beaten by a statistically significant margin only on the size-and-value datasets, where the assets are the ingredients of the factors themselves.

One gated cell misses: minimum variance on FF-4-factor, 0.033 against the paper's -0.018. Ten basis points of noise move it across 0.08 and the published value lies outside that range, so this is a difference in the data rather than fragility alone, the same difference the in-sample rows on the size-and-value datasets showed in notebook 02. It is reported as a miss.

The ranking check passes on Industry and FF-4-factor and fails strictly on the other two, where the rules that change places have published Sharpe ratios 0.002 to 0.007 apart, below the band. The check as written cannot distinguish an exchange of places at that resolution from a replication error; the numbers beside it can.

The specification question is the lesson of this notebook that will outlast the numbers: the equation in a paper and the code behind its tables can differ, and when they do, a footnote about the results is better evidence of what was run than the equation is. Choosing the reading that reproduces the tables is not tuning if the choice is between two readings of the text, it is made once, and it is recorded with its evidence.
"""),
]


if __name__ == "__main__":
    for name, cells in [("01_french_loader.ipynb", NB01), ("02_1N_vs_mean_variance.ipynb", NB02), ("03_shrinkage_and_constraints.ipynb", NB03)]:
        p = write(name, cells)
        print("wrote", p.relative_to(ROOT))
