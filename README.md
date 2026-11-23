# Optimal versus naive diversification: a replication, and what a tracking-error mandate changes

DeMiguel, Garlappi and Uppal (2009) find that no optimised portfolio beats the naive 1/N rule out of sample. This repository replicates their study on Ken French's data and then asks their question of an index fund, i.e., whether the choice of covariance estimator still matters when a long-only portfolio must track its benchmark under a mandate. The study's third part spends a budget of tracking error on four factors under the same mandate and measures the exposure obtained and what it contributed to the return.

The results are on the [dashboard](https://www.carlohofer.com/optimal-vs-naive-diversification/dashboard/B-P_dashboard.html) and in two notes, [the replication and the mandate](note/B-P_note_2026-10.pdf) and [the factor objective](note/B-P_note_moduleA_2026-11.pdf). The project page is [carlohofer.com/projects/optimal-vs-naive-diversification](https://www.carlohofer.com/projects/optimal-vs-naive-diversification/).

## Findings

The study has three parts, the replication, the mandate and the factor objective.

- **The replication.** On the paper's sample, July 1963 to November 2004, 29 of the 30 out-of-sample Sharpe ratios tested are within 0.03 of the published values, and all 30 turnover figures are within 25 per cent. The one miss, minimum variance on the FF-4-factor dataset, points to a revision of French's size and book-to-market portfolios. In the 261 months since the paper's sample, to August 2026, no optimising rule's Sharpe ratio exceeds 1/N's by a margin that is statistically significant at the 5 per cent level on the two-sided Jobson-Korkie test, on any of the four datasets.
- **The mandate.** On French's 49 industries from July 1979 to August 2026, an optimiser holds the long-only portfolio with the smallest forecast tracking error under a mandate: each industry within 2 percentage points of its benchmark weight, one-way turnover of at most 2 per cent a month, Coal, Oil and Utilities at no more than half their benchmark weight, tobacco and weapons excluded, and a beta of one. The four estimators built from three years of daily returns realise 84.7 to 93.4 basis points a year of tracking error. The factor and principal-component models realise 7 to 9 basis points more than the sample covariance and shrinkage, each difference statistically significant at the 5 per cent level on a paired test after Holm's correction across nine comparisons. Every estimator's forecast underestimates the realised tracking error, the realised active return being 22 to 61 per cent more volatile than forecast. The tilt is associated with an active return of +2 to +7 basis points a year, which is not statistically significant at the 5 per cent level, and the data rule out a cost of more than about 25 basis points a year.
- **The factor objective.** With a budget of 100 basis points a year of forecast tracking error spent on value, profitability, investment and momentum, the optimiser obtains 0.109 to 0.140 of combined exposure, 74 to 85 per cent of it in profitability and investment, at a realised tracking error 19 to 50 per cent above the budget. The targeted factors contributed +26.7 to +35.5 basis points a year, statistically significant at the 5 per cent level, and the six factors together +37 to +47. The residual, i.e., the part of the active return the factors do not explain, was −31 to −37, so no path's active return is statistically significant at that level.

## The notes, the dashboard and the companion page

Each note is a PDF with its HTML source beside it in `note/`. `B-P_note_2026-10.pdf` gives the replication and the mandate in full, and `B-P_note_moduleA_2026-11.pdf` the factor objective. The dashboard, `dashboard/B-P_dashboard.html`, shows the results in five views, *Summary*, *Replication*, *Tracking error*, *Factor exposure* and *Method and terms*. The last lists the committed table each exhibit is drawn from. The companion page, `companion/industry_tilts_factor_exposures.html`, explains how holding some industries below their benchmark weight creates exposures to the common factors.

## How to run

Each notebook runs from a blank Google Colab runtime: upload it and run all cells. It writes the code it needs into `src/bp/` and downloads French's files when it runs, so nothing from his library is stored here. From a checkout, run `pip install -r requirements.txt`, then `python3 -m pytest tests`, then the notebooks in order. `build_notebooks.py` writes the notebooks from their text and the modules in `src/bp/`, and they are committed without outputs.

Each notebook writes its tables to `outputs/`, with a record of each file's download date, hash and CRSP vintage. The tables the notes and the dashboard cite are committed in `results/202608/`, computed on the files French built from the CRSP database of August 2026. The figures of notebooks 04, 05, 06 and 09 are not in committed tables and come from rerunning those notebooks. To rebuild the dashboard, run `cp results/202608/* outputs/` and then `python3 dashboard/build_dashboard.py` from the repository root. The build stops unless each table matches its committed copy. French revises his files, so a run on a later vintage reproduces the comparisons and not every digit.

`checks/crsp_direct_test.py` checks the benchmark against the CRSP monthly stock file, where that file is held under a WRDS subscription. Only its aggregate results are committed, and no notebook depends on it.

## What is fixed in advance

The bands of the replication, the sample boundaries and every setting of the mandate and the factor objective are in `src/bp/constants.py`, each with its source, and the paper's published figures are in `src/bp/dgu_published.py`. Each notebook opens with the expectations it tests, written before its code ran, and marks the comparisons added after the results were known.

## The notebooks

One idea per notebook, run in order: the replication in 01 to 07, the mandate in 08 to 13 and 17 to 18, and the factor objective in 14 to 16.

| Notebook | What it does |
|---|---|
| 01 `french_loader` | Loads French's six monthly files, records their vintage, and checks the counts the paper's Table 2 implies |
| 02 `1N_vs_mean_variance` | Runs 1/N and sample mean-variance through the rolling evaluation, beside the paper's Tables 3 to 5 |
| 03 `shrinkage_and_constraints` | Adds Bayes-Stein, minimum variance and the constrained rules, and compares all nine with the paper: 29 of 30 Sharpe ratios and 30 of 30 turnover figures within their bands |
| 04 `critical_window_and_simulation` | Reproduces the paper's Proposition 1 (all 13 values) and its simulation (77 of 81 cells within 0.03) |
| 05 `fat_tails` | Reruns the simulation with fat-tailed returns: the estimated rules lose at most 0.002 in Sharpe ratio |
| 06 `volatility_clustering` | Reruns the simulation with volatility that clusters over time: the comparison with 1/N does not change |
| 07 `extended_sample` | Runs the nine rules on every month to August 2026 and compares the 261 months since the paper with its period |
| 08 `cap_weight_check` | Builds the benchmark from the 49 industries' cap weights and checks that it tracks French's market return within 47 basis points a year |
| 09 `principal_components` | Finds the principal components of the 49 industries and shows that the first is the market, with a correlation of 0.956 with the benchmark |
| 10 `covariance_estimators` | Compares the four estimators on monthly and daily data, by their forecasts and by their minimum-variance portfolios |
| 11 `optimiser` | Builds the constrained tracking-error optimiser and checks it against known answers and an independent solver |
| 12 `rolling_evaluation` | Runs every estimator month by month, 1979 to 2026: realised tracking error, forecast bias, active return and trading |
| 13 `factor_attribution` | Splits each month's active return into the contributions of six factors and a residual |
| 14 `factor_objective` | Sets up the factor objective: the largest exposure to four factors within a budget of forecast tracking error |
| 15 `factor_objective_evaluation` | Runs the nineteen paths of the factor objective month by month and judges six of its seven expectations |
| 16 `factor_objective_attribution` | Splits the factor objective's active return into factor contributions and a residual, and judges the seventh expectation |
| 17 `paired_tests` | Compares the realised tracking errors of two paths with the paired variance test of Ledoit and Wolf (2011) |
| 18 `daily_tracking_error` | Measures every path's tracking error on daily returns and repeats the paired tests on them |

## Terms

- **1/N**: the rule that holds every asset at the same weight and rebalances to it each month.
- **Sharpe ratio**: the mean monthly excess return divided by its standard deviation.
- **Band**: the distance from a published figure within which a replicated figure counts as a match, fixed before the code ran.
- **Tracking error**: the standard deviation of the monthly difference between the portfolio's return and the benchmark's, times the square root of 12. It is forecast before the month and realised after it.
- **Active return**: the portfolio's return minus the benchmark's.
- **Mandate**: the rules the portfolio obeys, set out under Findings.
- **Tilt**: holding Coal, Oil and Utilities at no more than half their benchmark weight.
- **Bias statistic**: the standard deviation of the realised active return divided by its forecast, 1 for an accurate forecast and above 1 when the forecast is too low.
- **Residual**: the part of the active return the six factors do not explain.

Each note opens with the full list of the terms it uses.

## Layout

```
build_notebooks.py      writes notebooks/ from their text and the modules in src/bp/
src/bp/                 the code: French's files, the datasets, the nine rules, the backtest, the simulations,
                        the benchmark, the covariance estimators, the optimiser, the evaluation,
                        the attribution, the paired test and the daily returns
notebooks/              one idea per notebook, run in order, committed without outputs
results/202608/         the tables the notes and the dashboard cite, with the record of French's files and the solver
note/                   the two notes, as PDF and HTML
dashboard/              the dashboard, its template, its build script and its static figures
companion/              the companion page, its template and its build script
checks/                 the direct test against CRSP with its aggregate results, and a pilot of the daily test on made-up data
tests/                  known-answer tests that run without a network connection
outputs/                written when the notebooks run, and not committed
index.html, .nojekyll   the GitHub Pages site, which opens the dashboard
LICENSE                 the MIT licence
```

## Other projects

**Climate risk as an equity signal.** An ownership graph linking 328 ownership entities in the US and developed Europe, 302 of them listed companies with a price series, to 5,115 asset holdings, built from Global Energy Monitor's free tracker. Of 19 apparent ownership changes drawn at random and checked by hand, 12 had no corporate event behind them. [Page](https://www.carlohofer.com/projects/climate-risk-equity-signal/), [note](https://github.com/ochofer/paper1-hazard-exposure-data/releases/download/note-v1.3/what-a-vintage-difference-measures.pdf), [code](https://github.com/ochofer/paper1-hazard-exposure-data)

**Volatility-managed portfolios: a replication, the real-time critique, and the months after the sample.** Volatility estimation and position sizing on Ken French's equity factors, replicating Moreira and Muir (2017) and the real-time critique of Cederburg, O'Doherty, Wang and Yan (2020). Scaled by the inverse of last month's realised variance, a factor's Sharpe ratio is higher than the original's by a margin that is statistically significant at the 5 per cent level for momentum alone when each of the six factors is tested on its own, and for no factor after Holm's correction for the six tests. In the 136 months after Moreira and Muir's sample no factor's difference is statistically significant, and the intervals are too wide to rule out the differences found on their sample. [Page](https://www.carlohofer.com/projects/volatility-managed-portfolios/), [dashboard](https://www.carlohofer.com/volatility-managed-portfolios/dashboard/B-Q_dashboard.html), [note](https://www.carlohofer.com/volatility-managed-portfolios/note/B-Q_note_2026-11.pdf), [code](https://github.com/ochofer/volatility-managed-portfolios)

**Stock-level index tracking: a point-in-time benchmark, a long-only mandate, and its performance attribution by sector.** Rebuilds the S&P 500 month by month from CRSP's list of members, at a tracking error of 11.5 basis points a year against CRSP's own return of the same list, and runs a long-only index-tracking mandate on it from 1999 to 2024, with its active return attributed by sector. The portfolios realise 78.9 to 83.6 basis points a year of tracking error, and each of four covariance estimators forecasts less: the realised active return is 48 to 85 per cent more volatile than forecast. Index changes require 11.4 per cent of the turnover of the portfolio built with Ledoit-Wolf shrinkage. [Page](https://www.carlohofer.com/projects/stock-level-tracking/), [dashboard](https://www.carlohofer.com/stock-level-tracking/dashboard/), [note](https://www.carlohofer.com/stock-level-tracking/note/stock-level-tracking_note_2026-11.pdf), [code](https://github.com/ochofer/stock-level-tracking)

**Rules-based portfolio.** Runs a real-money portfolio under rules published before the first order, with every later change dated in the repository: two UCITS ETFs at 70/30, a monthly cycle with pre-trade checks, look-through exposure and ex-ante risk on a public dashboard. [Page](https://www.carlohofer.com/projects/rules-based-portfolio/), [dashboard](https://www.carlohofer.com/rules-based-portfolio/), [guide](https://www.carlohofer.com/rules-based-portfolio/guide/guide.pdf), [code](https://github.com/ochofer/rules-based-portfolio)

The code, the notebooks and the text are released under the MIT licence (`LICENSE`). French's data are his and are downloaded from his library at run time.

Carlo Hofer, 2026.
