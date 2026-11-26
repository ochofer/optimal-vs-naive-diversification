# The tables of the write-up, vintage 202608

Every figure in the README, the two notes, the companion page and the dashboard comes from a table in this folder. Each notebook downloads French's files at run time and writes its tables to `outputs/`. The copies here are the ones the write-up cites, computed on the files French built from the CRSP database of August 2026, the vintage 202608.

Two records sit beside the tables, `provenance_french.json`, i.e., the download date, the SHA-256 hash and the vintage of each of French's files, and `provenance_solver.json`, i.e., the name and version of the solver.

French revises past returns, so a later vintage will not reproduce every digit. His library no longer serves the 10-industry and 25-portfolio files at vintage 202608. With those two files at vintage 202609, notebook 03 reproduces its tables byte for byte and notebook 07 reproduces every verdict of `extended_sample_vs_1N`, with its numbers within 2e-4.

Each file name ends in `_202608.csv`, left out below.

## The replication

| File | Notebook | What it holds |
|---|---|---|
| `replication_sharpe` | 03 | Each rule's Sharpe ratio on each dataset over the paper's period, beside the published value, with its verdict |
| `replication_turnover` | 03 | Each rule's turnover relative to 1/N, beside the published value, with its verdict |
| `replication_ceq` | 03 | Each rule's certainty-equivalent return, beside the published value, with its verdict |
| `replication_ranking` | 03 | The three best rules on each dataset, replicated and published |
| `replication_vs_1N` | 03 | Each rule against 1/N over the paper's period: the two Sharpe ratios, their difference, the two-sided Jobson-Korkie p-value, the one-sided value and the published one |
| `extended_sample_sharpe`, `extended_sample_turnover`, `extended_sample_ceq` | 07 | The same three measures in the paper's period and in the 261 months since |
| `extended_sample_vs_1N` | 07 | Each rule against 1/N in the 261 months since the paper, with the p-value and whether the rule beats 1/N at the 5 per cent level |

## The benchmark and the covariance estimators

| File | Notebook | What it holds |
|---|---|---|
| `benchmark_returns` | 08 | The benchmark's monthly return beside French's market return |
| `benchmark_weights` | 08 | The benchmark's weight in each of the 49 industries, each month |
| `covariance_estimators` | 10 | For each estimator, the bias of its forecast and the volatility, turnover and holdings of its minimum-variance portfolio, unconstrained and long-only |
| `minimum_variance_costs` | 10 | The same portfolios' returns net of trading costs at 50 and 100 basis points |
| `bias_by_period` | 10 | The bias of the forecasts by period, for the benchmark, 1/N, the industries and the active portfolio |
| `daily_to_monthly_scaling` | 10 | For each month, the benchmark's monthly variance over the window divided by 21 times its daily variance, the daily autocorrelation, and the variance ratio of Lo and MacKinlay (1988) over three and ten years |

## The mandate

| File | Notebook | What it holds |
|---|---|---|
| `optimiser_report` | 11 | The optimiser's portfolio at three months, by estimator and constraint set: tracking error, turnover, holdings and the constraints that bind |
| `optimiser_fixes` | 11 | The forecast tracking error of the tilt alone and of the mandate at those months |
| `optimiser_robust` | 11 | The robust portfolio's worst-case forecast against each single estimator's |
| `optimiser_speed_limit` | 11 | The forecast tracking error after each rebalance at the turnover cap, starting from 1/N |
| `rolling_evaluation` | 12 | Table 1's figures for every path: realised and forecast tracking error, bias statistic, active return, turnover, holdings and cost |
| `rolling_evaluation_by_decade` | 12 | Realised and forecast tracking error by decade |
| `rolling_evaluation_calibration` | 12 | The bias statistic of the forecast as made and of the calibrated forecast, overall and by decade |
| `rolling_evaluation_bias_by_decade` | 12 | The bias statistic by decade, under the mandate and under the tilt alone |
| `rolling_evaluation_descriptives` | 12 | The largest cumulative fall of the active return, the share of positive months, and the 95 per cent band of the bias statistic from the block bootstrap |
| `rolling_tracking_error` | 12 | The tracking error over the 36 months ending in each month, for every path |
| `active_returns`, `forecast_tracking_errors` | 12 | Each path's monthly active return and forecast tracking error |
| `rolling_weights_2026-08` | 12 | Each path's weights and the benchmark's in August 2026 |
| `attribution_summary` | 13 | Each path's mean active exposures and the six factor contributions with their standard errors, the residual and the factor share |
| `attribution_by_decade` | 13 | The contributions and the residual by decade |
| `attribution_mandate_cost` | 13 | The cost of the mandate against the tilt alone, split into the factors and the residual |
| `attribution_newey_west`, `attribution_mandate_cost_newey_west` | 13 | The contributions, the factor total, the residual and the active return of each path, and the cost of the mandate against the tilt alone, each per year with the standard error that takes the months as independent, the Newey-West standard error with six lags and the first-order autocorrelation of the monthly series |
| `attribution_monthly` | 13 | The monthly contributions, factor total, residual and active return of all fourteen paths |
| `attribution_monthly_sample_C3` | 13 | The monthly exposures and contributions of the sample covariance under the mandate |
| `attribution_betas_mean`, `attribution_betas_2026-08`, `attribution_benchmark_weights` | 13 | The industries' betas to the six factors and their benchmark weights, averaged and in August 2026 |
| `factor_means_1979-07_to_2026-08` | 13 | Each factor's mean return and volatility a year |

## The paired tests

| File | Notebook | What it holds |
|---|---|---|
| `paired_tests` | 17 | Each comparison of two paths on months: the two tracking errors, the difference, its standard error and 95 per cent interval, the smallest difference the test would detect, the p-value and Holm's correction |
| `paired_holm_a_and_e` | 17 | The nine comparisons under the mandate, i.e., six paths against the daily sample covariance and three pairs among the other daily estimators, with Holm's correction across the nine |
| `paired_tests_by_block` | 17 | The same tests with blocks of 3, 6, 12 and 24 months |
| `paired_size_check`, `paired_size_check_further` | 17 | The share of 1,000 simulated pairs of 566 months with equal tracking errors that the test rejects, at a correlation of 0.99 on four seeds and at correlations of 0.93 and 0.81 on one |
| `paired_paper_gain` | 17 | The gain of RiskMetrics over the sample covariance that Dom, Howard, Jansen and Lohre (2025) report, in basis points on this study's level, with the chance that an interval here would exclude zero |
| `bias_split_2000` | 17 | The bias statistic before January 2000 and from it, each with its band, and the band of the difference |
| `paired_tests_daily` | 18 | The paired tests on daily active returns, beside the same comparisons on months |
| `paired_tests_daily_batch_means` | 18 | Each row of `paired_tests_daily` with a standard error from batch means of 63, 126, 252 and 504 trading days (3, 6, 12 and 24 months for the rows on months), the interval and the p-value from Student's t, Holm's correction within A and within B, the number of calendar years in which the difference has the sign of the whole period, and for A's RiskMetrics row the reading on that interval |
| `paired_daily_calendar_years` | 18 | The difference of the two tracking errors of each row in each calendar year |
| `paired_daily_readings`, `paired_daily_expectations` | 18 | The RiskMetrics comparisons read against the published gains, and the two expectations on the daily tests with their verdicts |
| `paired_size_check_daily` | 18 | The size check on simulated daily data with clustered volatility |
| `daily_active_returns`, `daily_benchmark_returns`, `daily_minimum_variance_returns` | 18 | The daily returns of the paths, the benchmark and the minimum-variance portfolios |
| `daily_reconciliation`, `daily_reconciliation_minimum_variance`, `daily_reconciliation_minimum_variance_series` | 18 | The daily series compounded to months against the monthly records, with the largest gap |
| `daily_window_weights` | 18 | The three daily covariance windows described by the mean age and the effective number of their observations |
| `path_d_monthly_records`, `path_d_daily_active_returns` | 18 | The sample covariance on five years of daily returns under the mandate, the path the daily tests add |

## Why the structured models lose

| File | Notebook | What it holds |
|---|---|---|
| `structured_models_paths` | 19 | The realised tracking error on months and on days, the mean forecast, the turnover and the holdings of 26 paths under the mandate: the two structured models given back 0, 0.25, 0.5, 0.75 and all of the residual covariance between industries, and the four daily estimators on 3, 6, 12 and 36 months of daily returns |
| `structured_models_paired_tests` | 19 | The paired tests of those paths on days and on months, with Holm's correction within each part and each frequency |
| `structured_models_shrinkage` | 19 | Shrinkage's intensity over the months on each window, with the number of days the window holds |

## The factor objective

| File | Notebook | What it holds |
|---|---|---|
| `factor_objective_curves` | 14 | The factor objective against the budget at three months |
| `factor_objective_feasibility` | 14 | For each month, the smallest forecast tracking error the mandate allows on the sample covariance, and the objective at each budget |
| `factor_objective_capped_step` | 14 | One rebalance at the turnover cap, against the solution without the cap |
| `factor_objective_worked_2026-08` | 14 | August 2026 industry by industry: weights, betas and each industry's contribution to the objective |
| `factor_objective_evaluation` | 15 | Table 2's figures for the nineteen paths |
| `factor_objective_budget_months` | 15 | The months the mandate alone cannot meet, the months each path misses, and the months the budget binds |
| `factor_objective_by_decade` | 15 | Realised and forecast tracking error and the objective by decade |
| `factor_objective_monthly` | 15 | Every path's monthly record |
| `factor_objective_weights_2026-08` | 15 | Every path's weights in August 2026 |
| `factor_objective_incidental` | 15 | The exposures the mandate's portfolios carry with no factor objective |
| `factor_objective_verdicts` | 15 | E1 to E3 and E5 to E7 with their verdicts |
| `factor_objective_attribution` | 16 | Each path's exposures, the six contributions with their standard errors, the residual, the factor share and the targeted total |
| `factor_objective_attribution_by_decade` | 16 | The contributions and the targeted total by decade, at 100 basis points |
| `factor_objective_exposure_bought` | 16 | The mean exposure per basis point of realised tracking error, by targeted factor |
| `factor_objective_gap` | 16 | Each path's gap and gap per unit |
| `factor_objective_attribution_verdict` | 16 | E4 with its verdict |
| `factor_objective_attribution_newey_west` | 16 | The contributions, the targeted total, the factor total, the residual and the active return of each path per year, with the standard error that takes the months as independent, the Newey-West standard error with six lags and the first-order autocorrelation of the monthly series |
