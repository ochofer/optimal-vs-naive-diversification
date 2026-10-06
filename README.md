# Optimal versus naive diversification: a replication, and what a tracking-error mandate changes

Work in progress. The replication (notebooks 01 to 07) is complete: its table was produced on the CRSP 202607 vintage of French's files and reproduces on the 202608 vintage (notebook 07). Of the extension, the benchmark (08), the principal components (09), the covariance estimators (10), the optimiser (11) and the rolling evaluation (12) are built; the factor attribution (13) and the write-up (14) are to come.

I replicate DeMiguel, Garlappi and Uppal (2009), "Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?" (Review of Financial Studies 22(5), 1915-1953), on the four of their datasets that come from Ken French's library, and then ask their question of a long-only index-tracking mandate: once a portfolio has to stay close to its benchmark under a weight bound, a turnover cap and an industry tilt, does the choice of covariance estimator still matter? The extension compares four estimators (sample, Ledoit-Wolf shrinkage, a Fama-French factor model, a principal-component factor model) on French's 49 industry portfolios and reports what each constraint costs in ex-ante tracking error, with a factor-based attribution of the realised active return.

## Status

| Notebook | What it establishes | State |
|---|---|---|
| 01 `french_loader` | The six French files, their vintage, and the counts DGU's Table 2 implies | built |
| 02 `1N_vs_mean_variance` | 1/N and sample-based mean-variance through the rolling evaluation, beside Tables 3 to 5; the fragility of the mean-variance rows | built |
| 03 `shrinkage_and_constraints` | Bayes-Stein, minimum variance and the short-sale-constrained rules; the full comparison: 29 of 30 gated Sharpe cells and 30 of 30 turnover cells within the bands | built |
| 04 `critical_window_and_simulation` | DGU's Proposition 1 (all 13 stated values reproduced) and their Table 6 simulation (77 of 81 cells within 0.03, the sign pattern of mean-variance against 1/N reproduced, and every rule rerun on eight further draws) | built |
| 05 `fat_tails` | Beyond the paper: the same simulated market with Student-t shocks. The paper's conclusion does not rest on normality: the estimated rules lose 0.002 in Sharpe ratio at 5 degrees of freedom and nothing detectable at 10, because the cost of estimation sits in the means and the sampling error of a mean does not depend on the tails. A test added after the run gives each asset its own scale factor, so that the shape of the estimated covariance moves as well as its level; the change stays inside one-draw noise at both levels | built |
| 06 `volatility_clustering` | Beyond the paper: the same market with GARCH(1,1) volatility, so that months are no longer independent and the correlations between assets move. The paper's comparison does not change, and an oracle check says why: knowing each month's covariance exactly is worth 0.003 to 0.005 in Sharpe ratio to a rule that only splits wealth between assets, while scaling the whole position by the inverse of current variance is worth 0.010, which is what the next study is about | built |
| 07 `extended_sample` | The nine rules on every month French's files carry, to 2026-08: the paper's period reproduces on the 202608 vintage (29 of 30 gated Sharpe cells, 30 of 30 turnover cells), no optimising rule beats 1/N significantly in the 261 months since the paper, and minimum variance collapses on the factor datasets because the size and value premia did | built |
| 08 `cap_weight_check` | The benchmark of the extension: each industry's firm count times average firm size gives its cap weight, and the cap-weighted combination of the 49 industries tracks French's market return within 47 basis points a year over 686 months (gate: 50, fixed before the run), with the timing of the weights checked against the alternative reading. The gap comes from French's end-of-June formation: firms listed since June are in the market and in no industry until the next July. A direct test on the CRSP monthly stock file (run where that file is; aggregates only in `checks/`) accounts for 84% of the gap's variance, all four pre-registered expectations met | built |
| 09 `principal_components` | The principal components of the 49 industries' excess returns, 1969-07 to 2026-08. The first explains 55% of the total variance, loads on every industry positively and by beta, and is the market: correlation 0.956 with the benchmark's excess return over the full sample, met in two of three windows fixed in advance and missed in the window from 2023 (0.837), when two industries hold a third of the cap-weighted benchmark; the pre-registered consequence is that notebook 10's PCA estimator takes the market as its first factor. Two components exceed what independent noise produces; the smaller components do not carry over between periods | built |
| 10 `covariance_estimators` | Four covariance estimators (sample, Ledoit-Wolf shrinkage, a six-factor model, a principal-component model with the market first) on 120 monthly returns and on three years of daily returns, judged over 566 months by the calibration of their risk forecasts and by the minimum-variance portfolios built from them. Without constraints and on monthly data, structure matters (14.1% realised volatility for the sample covariance against 12.1% to 12.8%); on daily data the sample covariance is as good as any; with the long-only constraint every estimator at either frequency lands within 0.2 points (12.1% to 12.3%), the finding of Dom, Howard, Jansen and Lohre (2024). The scaling from daily to monthly variance holds on average and fails by decade, with the sign of the daily autocorrelation. Three tests added after the run: a variance-ratio correction of the scale (the ten-year ratio holds the benchmark's bias statistic within 0.09 of 1 in every decade, against 0.78 to 1.34 under the 21 rule), bias statistics by decade, and trading costs (at 50 basis points the unconstrained minimum-variance portfolios pay 1.3% to 4.6% a year and earn less net than the long-only ones in all eight variants) | built |
| 11 `optimiser` | The constrained tracking-error minimiser: the weights closest to the benchmark, in forecast tracking error, under long-only, an active weight bound of 2 percentage points, a one-way turnover cap of 2% a month and a 50% tilt against Coal, Oil and Utilities, each switchable; a convex quadratic program solved with cvxpy. Checked against answers known by hand and an independent solver, then run at three months with the five estimator variants: the tilt costs 35 basis points a year of forecast tracking error in 2026-08 (108 at most in 1979-07, when Oil was 15% of the benchmark), the weight goes to the industries that restore the portfolio's beta and then to those that move with the removed ones, and the turnover cap acts as a speed limit (26 months from 1/N to the benchmark). Four checks added after the first run found the practical problem behind the hedge, and the design was fixed: the tilt's hedge left a beta bet standing with a noisy covariance (now beta neutrality is part of the mandate), bought tobacco and weapons (now excluded), and differed across estimators by 1 to 5 basis points (now a robust portfolio, the minimax across the five covariances, runs beside them; it sits 0.1 to 1.1 basis points above each estimator's own best). The fixes cost the daily estimators 2 to 7 basis points. A fifth check reruns a month in which the solver reported "optimal" for a problem with no feasible portfolio (the index moved 4.3% against a 2% cap): the returned weights summed to 0.96 and traded 22% one way, the independent check of every returned portfolio fails them, and the relaxation rule raises the cap to the smallest feasible turnover, 2.01%; since then the optimiser finds that turnover first, by a linear program, and never poses a capped problem that has no solution | built |
| 12 `rolling_evaluation` | Every specification run month by month from 1979-07 to 2026-08, 566 months, 28 specifications (five estimators, the robust portfolio and RiskMetrics times four constraint sets) plus the tilt alone as a sensitivity, each portfolio built on the data before its month. Under the mandate the four daily estimators realise 85 to 93 basis points a year of tracking error (range 9), the monthly sample covariance 96, the robust portfolio 87: the estimator still matters, by about a tenth. The forecasts under-forecast the realised tracking error by a fifth to a third (the oil shock of 1979 to 1986 and the optimisation bias of a noisy covariance), the robust worst-case forecast being the best calibrated; the direction of the miss was foreseeable from notebook 10 and Michaud (1989), the size was not. The mandate's fixes cost 4 to 5 basis points realised; the cap was relaxed in 1 to 4 of 566 months; the tilt had no opportunity cost (+2 to +7 basis points a year gross, inside one standard error of 12 to 14 of zero) and the exclusions cost 3 to 9. Two additions after the first run, each with its expectation written first: RiskMetrics realises 84.3 basis points against the sample covariance's 84.7, so the gain from time dynamics that Dom, Howard, Jansen and Lohre (2024) found does not survive the mandate on 49 industries; and calibrating each forecast on the previous 60 months of its own path, with nothing from the future, moves the daily estimators' bias statistics from 1.22 to 1.39 to 1.11 to 1.17 and the monthly covariance's from 1.61 to 1.12, repairing the persistent part of the bias from 1990 on | built |
| 13 | Attribution | not started |

## How to run

Each notebook runs from a blank Google Colab runtime: upload it and run all cells. It writes the code it needs into `src/bp/` and downloads French's files at run time; notebooks 11 to 13 use cvxpy, which Colab carries and which the notebook installs if it is missing. The six monthly files and four daily files are downloaded at run time (notebooks 10 to 13 add the daily 49-industry and factor files). Nothing from French's library is committed; `outputs/provenance_french.json` records the date, the SHA-256 of each zip and the CRSP vintage every output was computed on. One check, `checks/crsp_direct_test.py`, reads the CRSP monthly stock file on the machine that holds it (accessed through WRDS under an institutional subscription); no CRSP data are committed, only its aggregate results, and no notebook depends on it. French revises history, so a rerun on a later vintage will not reproduce every digit, and the provenance file is what says why.

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
- **benchmark**: in the extension, the index the portfolio tracks: the cap-weighted combination of the 49 industries built in notebook 08.
- **market capitalisation**: the number of a firm's shares times their price; market equity is the same quantity.
- **value-weighted return**: the return of a group of firms in which each firm counts in proportion to its market capitalisation at the start of the month; French's industry returns are value-weighted.
- **cap-weighted**: weighted by market capitalisation; said of the benchmark's industry weights.
- **tracking error**: the standard deviation of the monthly difference between two return series, times the square root of 12.
- **look-ahead**: using, for month t, a number that was not known when month t began.
- **variance ratio**: the variance of 21-day returns divided by 21 times the variance of daily returns; 1 when one day's return says nothing about the next day's, above 1 under positive autocorrelation.
- **optimiser**: the extension's routine that solves the constrained tracking-error problem; the word is not used for the replication's rules.
- **one-way turnover**: half the sum of absolute weight changes at a rebalance, the fraction of the portfolio sold (and bought); the replication's turnover is the full sum.
- **turnover cap**: an upper limit on one-way turnover per rebalance, 2% a month in the extension.
- **tilt**: a constraint holding named industries below their benchmark weight; the extension holds Coal, Oil and Utilities at no more than half of it, a 50% reduction relative to the benchmark.
- **drifted weights**: the previous month's weights after that month's returns have moved them.
- **effective number of holdings**: one divided by the sum of squared weights; 49 for 1/N over 49 industries.
- **constraint set**: one of the cumulative sets C0 to C3: long-only; plus the active weight bound; plus the turnover cap; plus the mandate (the tilt with beta neutrality and the exclusions).
- **mandate**: the whole set of rules the extension's portfolio obeys: the carbon tilt, the exclusions of tobacco and weapons, beta neutrality.
- **robust portfolio**: the weights whose largest forecast tracking error across the five covariance estimates is smallest; the sixth variant of the rolling evaluation.
- **path**: the month-by-month sequence of portfolios of one specification in the rolling evaluation, each built on the data before its month.
- **index turnover**: the one-way turnover an index fund needs to follow its benchmark, the distance between the benchmark's new weights and its own drifted weights.
- **information ratio**: the active return per year divided by the realised tracking error.

## Layout

```
build_notebooks.py      generates notebooks/ from prose here and code in src/bp/
src/bp/constants.py     every pre-committed number, with its source
src/bp/french_loader.py download, provenance, parsing of French's files
src/bp/dgu_published.py DGU's Tables 3, 4, 5 and 6, transcribed and tested
src/bp/rules.py         the nine portfolio rules
src/bp/backtest.py      the rolling evaluation and the performance measures
src/bp/simulate.py      the one-factor market: normal, fat-tailed, clustered volatility
src/bp/benchmark.py     the extension's benchmark: cap weights of the 49 industries and their tracking error
src/bp/direct_test.py   the two firm universes behind notebook 08's direct test, on any monthly stock file
src/bp/pca.py           principal components: fit with a sign rule, scores, stability, parallel analysis, rolling view
src/bp/covariance.py    the four covariance estimators, the sensitivities, the windows at both frequencies, the panels and the tests
src/bp/optimiser.py     the constrained tracking-error minimiser and its robust version, drifted weights, feasibility checks, effective number of holdings
src/bp/evaluation.py    the rolling evaluation: one path per specification, its records and its measures
checks/                 the direct test's script and its aggregate results (the data stay where they are)
notebooks/              one concept per notebook, run in order
outputs/                portfolio-level tables and provenance records
tests/                  known-answer checks that run without network
```

Carlo Hofer, 2026.
