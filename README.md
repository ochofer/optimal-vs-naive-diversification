# Optimal versus naive diversification: a replication, and what a tracking-error mandate changes

Work in progress. The replication table (notebooks 02 and 03) was produced on the CRSP 202607 vintage of French's files and reproduces on the 202608 vintage (notebook 07); the extension has not started.

I replicate DeMiguel, Garlappi and Uppal (2009), "Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?" (Review of Financial Studies 22(5), 1915-1953), on the four of their datasets that come from Ken French's library, and then ask their question of a long-only index-tracking mandate: once a portfolio has to stay close to its benchmark under a weight bound, a turnover cap and an industry tilt, does the choice of covariance estimator still matter? The extension compares four estimators (sample, Ledoit-Wolf shrinkage, a Fama-French factor model, a principal-component factor model) on French's 49 industry portfolios and reports what each constraint costs in ex-ante tracking error, with a factor-based attribution of the realised active return.

## Status

| Notebook | What it establishes | State |
|---|---|---|
| 01 `french_loader` | The six French files, their vintage, and the counts DGU's Table 2 implies | built |
| 02 `1N_vs_mean_variance` | 1/N and sample-based mean-variance through the rolling evaluation, beside Tables 3 to 5; the fragility of the mean-variance rows | built |
| 03 `shrinkage_and_constraints` | Bayes-Stein, minimum variance and the short-sale-constrained rules; the full comparison: 29 of 30 gated Sharpe cells and 30 of 30 turnover cells within the bands | built |
| 04 `critical_window_and_simulation` | DGU's Proposition 1 (all 13 stated values reproduced) and their Table 6 simulation (77 of 81 cells within 0.03, the sign pattern of mean-variance against 1/N reproduced, and every rule rerun on eight further draws) | built |
| 05 `fat_tails` | Beyond the paper: the same simulated market with Student-t shocks. The paper's conclusion does not rest on normality: the estimated rules lose 0.002 in Sharpe ratio at 5 degrees of freedom and nothing detectable at 10, because the cost of estimation sits in the means and the sampling error of a mean does not depend on the tails | built |
| 06 `volatility_clustering` | Beyond the paper: the same market with GARCH(1,1) volatility, so that months are no longer independent and the correlations between assets move. The paper's comparison does not change, and an oracle check says why: knowing each month's covariance exactly is worth 0.003 to 0.005 in Sharpe ratio to a rule that only splits wealth between assets, while scaling the whole position by the inverse of current variance is worth 0.010, which is what the next study is about | built |
| 07 `extended_sample` | The nine rules on every month French's files carry, to 2026-08: the paper's period reproduces on the 202608 vintage (29 of 30 gated Sharpe cells, 30 of 30 turnover cells), no optimising rule beats 1/N significantly in the 261 months since the paper, and minimum variance collapses on the factor datasets because the size and value premia did | built |
| 08 | The cap-weight check | not started |
| 09 to 13 | PCA, the four estimators, the optimiser, the rolling evaluation, attribution | not started |

## How to run

Each notebook runs from a blank Google Colab runtime: upload it and run all cells. It writes the code it needs into `src/bp/` and downloads French's files at run time. Nothing from French's library is committed; `outputs/provenance_french.json` records the date, the SHA-256 of each zip and the CRSP vintage every output was computed on. French revises history, so a rerun on a later vintage will not reproduce every digit, and the provenance file is what says why.

From a checkout: `pip install -r requirements.txt`, then `python3 -m pytest tests`, then open the notebooks. `build_notebooks.py` regenerates every notebook from its prose and the modules in `src/bp/`; the notebooks are build artefacts and are committed without outputs.

## What is pre-committed

The bands the replication has to meet, the sample boundaries and every design parameter of the extension are in `src/bp/constants.py`, each with its source, written before any of the rules' code ran. The published numbers I compare against are in `src/bp/dgu_published.py`; `tests/test_dgu_published.py` re-reads them digit by digit from the journal PDF when the PDF is present on the machine (it is not in the repository).

## Terms

One word per idea, used the same way in every notebook, module and comment.

- **1/N**: the rule that puts weight 1/N on each of the N assets and rebalances to it every month (`ew` in the code).
- **sample-based mean-variance**: the rule that plugs the estimation window's sample mean and covariance into Markowitz's formula (`mv`); mean-variance for short. "Unconstrained" is added only where it has to be told apart from its short-sale-constrained version.
- **rule**: any of the portfolio rules compared. The paper says "strategy".
- **short-sale-constrained**: a rule whose weights may not be negative (`mv-c`, `bs-c`, `min-c`, `g-min-c`); constrained for short.
- **estimation window**: the M months a rule sees when it forms its weights; window for short.
- **rolling evaluation**: moving the estimation window forward one month at a time and recording the return of the month after it; the procedure of DGU section 2 and of the `backtest` module.
- **estimation error**: the difference between the estimated moments and the true ones. Everything the paper documents follows from it.
- **tangency portfolio**: the portfolio with the highest Sharpe ratio when the true mean and covariance are known; `mv (true)` in the paper's Table 6.
- **band**: a pre-committed interval within which a replicated number counts as matching the published one (the `BAND_` constants).
- **gated**: said of a cell a band applies to.
- **verdict**: pass or MISS for a gated cell. A cell with no band is reported beside the published number and has no verdict.
- **fragility test**: rerunning a rule after adding small Gaussian noise to every return, to see how far its published number could move on another vintage of the data.
- **vintage**: the version of French's files on the download date, named by the CRSP cut French built them from.
- **simulated history**: the 24,000 months of returns the simulation produces.
- **draw**: one simulated history from one seed.
- **critical window**: the estimation window at which sample-based mean-variance starts to beat 1/N on average (DGU Proposition 1).
- **crossing**: the simulated counterpart of the critical window, the first window at which mean-variance's out-of-sample Sharpe ratio reaches 1/N's.
- **fat tails**: extreme months more frequent and more extreme than a normal distribution allows (notebook 05); fat-tailed is the adjective.
- **volatility clustering**: volatility that persists from month to month, so that months are not independent (notebook 06); volatility that changes through time.
- **benchmark**: in the extension, the index the portfolio tracks.
- **optimiser**: the extension's routine that solves the constrained tracking-error problem; the word is not used for the replication's rules.

## Layout

```
build_notebooks.py      generates notebooks/ from prose here and code in src/bp/
src/bp/constants.py     every pre-committed number, with its source
src/bp/french_loader.py download, provenance, parsing of French's files
src/bp/dgu_published.py DGU's Tables 3, 4, 5 and 6, transcribed and tested
src/bp/rules.py         the nine portfolio rules
src/bp/backtest.py      the rolling evaluation and the performance measures
src/bp/simulate.py      the one-factor market: normal, fat-tailed, clustered volatility
notebooks/              one concept per notebook, run in order
outputs/                portfolio-level tables and provenance records
tests/                  known-answer checks that run without network
```

Carlo Hofer, 2026.
