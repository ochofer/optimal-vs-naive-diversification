# Optimal versus naive diversification: a replication, and the same question under an index mandate

The study asks DeMiguel, Garlappi and Uppal's question, whether an optimised portfolio does better than a naive portfolio, in two places.

- **The replication.** DeMiguel, Garlappi and Uppal (2009) find that none of the optimised portfolios they test is consistently better than the naive 1/N rule out of sample, because the error in the estimated inputs costs more than optimising gains. The study replicates their comparison on Ken French's data and runs it on the 261 months since their sample.
- **Under an index mandate.** An index fund's mandate fixes most of the portfolio and needs no return forecast, so what the fund decides is where to put the weight the mandate moves away from the benchmark. The study compares an optimiser that places it with a covariance estimate with two naive portfolios that place it by a fixed rule: the naive tilt when Coal, Oil and Utilities are held at half their benchmark weight, and the tilted index when a budget of tracking error is spent on four factors.

The results are on the [dashboard](https://www.carlohofer.com/optimal-vs-naive-diversification/dashboard/B-P_dashboard.html) and in the [note](note/B-P_note_2026-11.pdf). The project page is [carlohofer.com/projects/optimal-vs-naive-diversification](https://www.carlohofer.com/projects/optimal-vs-naive-diversification/). The optimised portfolios and the comparison of covariance estimators behind them are the companion study's, [risk-models-for-index-tracking](https://github.com/ochofer/risk-models-for-index-tracking).

## Findings

- **The replication.** On the paper's sample, July 1963 to November 2004, the replication matches the paper: 29 of the 30 Sharpe ratios tested are within 0.03 of the published values, and all 26 turnover figures of the portfolios that trade are within 25 per cent. The one Sharpe ratio more than 0.03 away, minimum variance on the FF-4-factor dataset, is consistent with French having revised his size and book-to-market portfolios since the paper. In the 261 months since the paper's sample, to August 2026, no optimising rule's Sharpe ratio exceeds 1/N's by a margin that is statistically significant at the 5 per cent level on the two-sided Jobson-Korkie test, on any of the four datasets.
- **Under the tilt alone.** On French's 49 industries from July 1979 to August 2026, with Coal, Oil and Utilities held at no more than half their benchmark weight, every other industry within 2 percentage points of its benchmark weight, and the optimised portfolios at one-way turnover of at most 2 per cent a month, the naive tilt realises 105.6 basis points a year of tracking error and the seven optimised portfolios 79.7 to 90.9: one for each of six covariance estimators, and one for a robust portfolio built from five of them. The naive tilt's tracking error is 14.7 to 25.9 basis points a year higher than each optimised portfolio's. Each difference is statistically significant at the 5 per cent level on the paired variance test of Ledoit and Wolf (2011), after Holm's correction for the seven comparisons made together.
- **Under the factor objective.** With tobacco and weapons excluded as well, a beta of one, and a budget of 100 basis points a year of forecast tracking error spent on value, profitability, investment and momentum, the optimiser's forecast exposure per basis point of realised tracking error is 0.000824 to 0.000979, the exposure its own betas give, and the tilted index's 0.000185, at tracking errors of the same size. The optimiser's is 4.5 to 5.3 times the tilted index's. Each difference is statistically significant at the 5 per cent level on a paired bootstrap that resamples blocks of 12 months, after Holm's correction for the seven comparisons. Measured on the returns, the optimiser's realised exposure per basis point is 1.06 to 1.48 times the tilted index's, and no difference is statistically significant at the 5 per cent level after Holm's correction, with intervals from about 0.4 to about 2.7 times.
- **The active returns.** Both naive portfolios earned more active return over the sample than the optimised portfolios they are compared with, before and after costs. Before costs the naive tilt earned +13.5 basis points a year against +1.8 to +6.9, and the tilted index +16.4 against +2.3 to +15.5. On a paired test of the information ratios, i.e., the active return divided by the tracking error, no difference is statistically significant at the 5 per cent level before costs. At 100 basis points per unit of turnover under the tilt alone four of the seven are statistically significant tested on their own, and none after Holm's correction. Under the factor objective none is, at any cost. The gap has two sources. The first is the spread between the other industries' return and that of Coal, Oil and Utilities: month by month, the naive tilt's active return is the weight removed from the three times this spread. The spread averaged +1.22 per cent a year, with a standard deviation of 15.28 per cent. The optimised portfolios hedge part of it away, and how much it earned in this sample is a property of the period. The second is the naive portfolios' lower turnover, 0.42 per cent a month against 0.81 to 1.50 under the tilt alone and 0.77 against 1.78 to 2.00 under the factor objective, which widens the gap after costs.

## The note and the dashboard

The note is a PDF with its HTML source beside it in `note/`, built by `note/build_note.py` from `note/template.html` and the committed tables. The dashboard, `dashboard/B-P_dashboard.html`, built by `dashboard/build_dashboard.py`, shows the results in five views, *Summary*, *Replication*, *Tracking error*, *Factor exposure* and *Method*. The last lists the committed tables each exhibit is drawn from.

## How to run

Notebooks 01 to 07 run from a blank Google Colab runtime: upload one and run all cells. It writes the code it needs into `src/bp/` and downloads French's files when it runs, so nothing from his library is stored here. Notebooks 08 and 09 also read the code and the tables copied from the companion study, so they run from the root of a checkout. From a checkout, run `pip install -r requirements.txt`, then `python3 -m pytest tests`, then the notebooks in order. `build_notebooks.py` writes the notebooks from their text and the modules in `src/bp/`, and they are committed without outputs.

Each notebook writes its tables to `outputs/`, with a record of each file's download date, hash and CRSP vintage. The tables the note and the dashboard cite are committed in `results/202608/`, computed on the files French built from the CRSP database of August 2026. The figures of notebooks 04, 05 and 06 are not in committed tables and come from rerunning those notebooks. To rebuild the note and the dashboard, run `python3 note/build_note.py` and `python3 dashboard/build_dashboard.py` from the repository root. The note's PDF also needs Playwright with Chromium and pypdf, and `--no-pdf` builds its HTML alone. The dashboard's build stops unless each table it reads is the file at the current commit. French revises his files, so a run on a later vintage reproduces the comparisons and not every digit.

## What is fixed in advance

The margins of the replication, the sample boundaries and every setting of the two comparisons are in `src/bp/constants.py`, each with its source. The margins were fixed before the code ran, except the limit on which Sharpe ratios are tested, set after the first replication results. The paper's published figures are in `src/bp/dgu_published.py`. Notebooks 01 to 07 open with the expectations they test, written before their code ran. Notebooks 08 and 09 report their comparisons as results.

## The notebooks

One idea per notebook, run in order: the replication in 01 to 07, and the comparisons under the mandate in 08 and 09.

| Notebook | What it does |
|---|---|
| 01 `french_loader` | Loads French's monthly and daily files, records their vintage, and checks the counts the paper's Table 2 implies |
| 02 `1N_vs_mean_variance` | Runs 1/N and sample mean-variance through the rolling evaluation, beside the paper's Tables 3 to 5 |
| 03 `shrinkage_and_constraints` | Adds Bayes-Stein, minimum variance and the constrained rules, and compares all nine with the paper: 29 of the 30 Sharpe ratios tested within 0.03 of the published values, and all 26 turnover figures of the portfolios that trade within 25 per cent |
| 04 `critical_window_and_simulation` | Reproduces the paper's Proposition 1 (all 13 values) and its simulation (77 of 81 Sharpe ratios within 0.03) |
| 05 `fat_tails` | Reruns the simulation with fat-tailed returns: the estimated rules lose at most 0.002 in Sharpe ratio |
| 06 `volatility_clustering` | Reruns the simulation with volatility that clusters over time: the comparison with 1/N does not change |
| 07 `extended_sample` | Runs the nine rules on every month to August 2026 and compares the 261 months since the paper with its period |
| 08 `naive_tilt` | Runs the naive tilt month by month, 1979 to 2026, and compares its realised tracking error, turnover, returns and factor exposures with the seven optimised portfolios under the tilt alone |
| 09 `tilted_index` | Runs the tilted index month by month and compares its forecast and realised factor exposure per basis point of tracking error, turnover, returns and attribution with the seven optimised portfolios under the factor objective |

## Terms

- **1/N**: the rule that holds every asset at the same weight and rebalances to it each month.
- **Sharpe ratio**: the mean monthly excess return divided by its standard deviation.
- **Tracking error**: the standard deviation of the monthly difference between the portfolio's return and the benchmark's, times the square root of 12. It is forecast before the month and realised after it.
- **Active return**: the portfolio's return minus the benchmark's.
- **Mandate**: the rules the portfolio obeys, set out under Findings.
- **Tilt**: holding Coal, Oil and Utilities at no more than half their benchmark weight.
- **Tilt alone**: the first setting, in which the mandate holds the tilt without the two rules the factor objective adds.
- **Optimiser**: the routine that chooses the portfolio's weights each month from a covariance estimate, within the mandate's rules.
- **Optimised portfolio**: the portfolio an optimiser holds month by month, under the tilt alone or under the factor objective, with one of six covariance estimators or as a robust portfolio built from five of them.
- **Factor objective**: the sum of the portfolio's active exposures to value, profitability, investment and momentum.
- **Forecast exposure**: the factor objective as the optimiser computes it, with each industry's betas from the three years before the month.
- **Realised exposure**: the sum of the slopes on the four factors when the portfolio's monthly active returns are regressed on the six factors' monthly returns.
- **Residual**: the part of the active return the six factors do not explain.
- **Naive tilt**: the benchmark with Coal, Oil and Utilities held at half their benchmark weight and the removed weight spread over the other 46 industries in proportion to their benchmark weights, rebalanced to that target every month, with no risk model.
- **Tilted index**: the benchmark under the tilt and the exclusions of the factor objective, with each of the other 44 industries' weights changed by a percentage proportional to the distance of its factor score from their weighted average score, as far as the bound of 2 percentage points on each active weight and a floor of zero allow, rebalanced every month, with no risk model.
- **The two naive portfolios**: the naive tilt and the tilted index together.

The note opens with the full list of the terms it uses.

## Layout

```
build_notebooks.py      writes notebooks/ from their text and the modules in src/bp/
src/bp/                 the code: French's files, the datasets, the nine rules, the backtest, the simulations,
                        and the two naive portfolios
src/bp/source/          the code of the optimised portfolios, copied unchanged from the companion study
notebooks/              one idea per notebook, run in order, committed without outputs
results/202608/         the tables the note and the dashboard cite, with the record of French's files and the solver
results/202608/source/  the optimised portfolios' tables, copied unchanged from the companion study
note/                   the note, as PDF and HTML, its template and its build script
dashboard/              the dashboard, its template and its build script
tests/                  known-answer tests that run without a network connection
outputs/                written when the notebooks run, and not committed
index.html, .nojekyll   the GitHub Pages site, which opens the dashboard
LICENSE                 the MIT licence
```

## Other projects

**Which risk model for an index mandate? Covariance estimators and tracking error on 49 US industries.** Runs a long-only index-tracking mandate on Ken French's 49 US industries from 1979 to 2026 with six covariance estimators. The factor and principal-component models realise 7 to 9 basis points a year more tracking error than the sample covariance's 84.7, each difference statistically significant at the 5 per cent level after Holm's correction. On minimum-variance portfolios, by which Dom, Howard, Jansen and Lohre (2025) judge estimators, the same two models realise 0.95 to 1.58 percentage points a year more volatility when weights may be negative, and within 0.06 points of the sample covariance when they may not. [Page](https://www.carlohofer.com/projects/risk-models-for-index-tracking/), [dashboard](https://www.carlohofer.com/risk-models-for-index-tracking/dashboard/), [note](https://www.carlohofer.com/risk-models-for-index-tracking/note/risk-models-for-index-tracking_note_2026-11.pdf), [code](https://github.com/ochofer/risk-models-for-index-tracking)

**Climate risk as an equity signal.** An ownership graph linking 328 ownership entities in the US and developed Europe, 302 of them listed companies with a price series, to 5,115 asset holdings, built from Global Energy Monitor's free tracker. Of 19 apparent ownership changes drawn at random and checked by hand, 12 had no corporate event behind them. [Page](https://www.carlohofer.com/projects/climate-risk-equity-signal/), [note](https://github.com/ochofer/paper1-hazard-exposure-data/releases/latest/download/what-a-vintage-difference-measures.pdf), [code](https://github.com/ochofer/paper1-hazard-exposure-data)

**Volatility-managed portfolios: a replication, the real-time critique, and the months after the sample.** Volatility estimation and position sizing on Ken French's six equity factors, replicating Moreira and Muir (2017) and the real-time critique of Cederburg, O'Doherty, Wang and Yan (2020). A volatility-managed factor is the factor scaled each month by the inverse of last month's realised variance. Its Sharpe ratio is higher than the original factor's by a margin that is statistically significant at the 5 per cent level for momentum alone when each of the six factors is tested on its own, and for no factor after Holm's correction for the six tests. In the 136 months after Moreira and Muir's sample no factor's difference is statistically significant, and for the six volatility-managed factors the confidence intervals are too wide to rule out the differences found on their sample. [Page](https://www.carlohofer.com/projects/volatility-managed-portfolios/), [dashboard](https://www.carlohofer.com/volatility-managed-portfolios/dashboard/B-Q_dashboard.html), [note](https://www.carlohofer.com/volatility-managed-portfolios/note/B-Q_note_2026-11.pdf), [code](https://github.com/ochofer/volatility-managed-portfolios)

**Stock-level index tracking: a point-in-time benchmark, a long-only mandate, and its performance attribution by sector.** Rebuilds the S&P 500 month by month from the list of members kept by the Center for Research in Security Prices (CRSP), at a tracking error of 11.5 basis points a year from 1926 to 2024 against CRSP's own return of the same list, and runs a long-only index-tracking mandate on it from 1999 to 2024, with its active return attributed by sector. Under the four covariance estimators the mandate realises 78.9 to 83.6 basis points a year of tracking error, and each estimator forecasts less: the realised active return is 48 to 85 per cent more volatile than forecast. Index changes require 11.4 per cent of the turnover under the Ledoit-Wolf estimator. [Page](https://www.carlohofer.com/projects/stock-level-tracking/), [dashboard](https://www.carlohofer.com/stock-level-tracking/dashboard/), [note](https://www.carlohofer.com/stock-level-tracking/note/stock-level-tracking_note_2026-11.pdf), [code](https://github.com/ochofer/stock-level-tracking)

**Return prediction: machine learning on the S&P 500's members, corrected for overfitting.** Forecasts of each S&P 500 member's return over the next month from twelve characteristics built from CRSP and Compustat, by six models from least squares to a neural network, out of sample from 2006 to 2024. The study follows the method of Gu, Kelly and Xiu (2020), reduced to the index's members, and corrects the highest Sharpe ratio among the portfolios built from these forecasts for overfitting, that is, for having tried many versions and kept the one with the highest. In build: its findings are stated when the study is complete. [Page](https://www.carlohofer.com/projects/ml-return-prediction-backtest-overfitting/), [code](https://github.com/ochofer/ml-return-prediction-backtest-overfitting)

**Rules-based portfolio.** Runs a real-money portfolio under rules published before the first order, with every later change dated in the repository: two UCITS ETFs at 70/30, a monthly cycle with each rule checked before the orders, and a public dashboard with the look-through of both ETFs and the estimated risk. [Page](https://www.carlohofer.com/projects/rules-based-portfolio/), [dashboard](https://www.carlohofer.com/rules-based-portfolio/), [guide](https://www.carlohofer.com/rules-based-portfolio/guide/guide.pdf), [code](https://github.com/ochofer/rules-based-portfolio)

The code, the notebooks and the text are released under the MIT licence (`LICENSE`). French's data are his and are downloaded from his library at run time.

Carlo Hofer, 2026.
