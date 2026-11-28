# The tables of the write-up, vintage 202608

Every figure in the README, the note and the dashboard comes from a table in this folder. Each notebook downloads French's files at run time and writes its tables to `outputs/`. The copies here are the ones the write-up cites, computed on the files French built from the CRSP database of August 2026, the vintage 202608.

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

## The optimised portfolios, read from risk-models-for-index-tracking

The six tables in `source/` are copied unchanged from the repository risk-models-for-index-tracking at commit ddbb75c, where they sit in `results/202608/` under the same names. The comparisons with the two naive portfolios, in notebooks 08 and 09, read the optimised portfolios' figures from them. `constants.SOURCE_TABLES` holds the SHA-256 of each, and `tests/test_source_copies.py` checks it.

| File | Written at that commit by | What it holds |
|---|---|---|
| `rolling_evaluation` | `notebooks/12_rolling_evaluation.ipynb` | For every path of the mandate study: realised and forecast tracking error, bias statistic, active return, turnover, holdings and cost |
| `active_returns` | `notebooks/12_rolling_evaluation.ipynb` | Each path's monthly active return |
| `attribution_summary` | `notebooks/13_factor_attribution.ipynb` | Each path's mean active exposures and the six factor contributions with their standard errors, the residual and the factor share |
| `factor_objective_evaluation` | `notebooks/15_factor_objective_evaluation.ipynb` | For each of the nineteen paths with a factor objective: realised and forecast tracking error, active return, turnover, cost, the four targeted exposures and the exposure per basis point of realised tracking error |
| `factor_objective_monthly` | `notebooks/15_factor_objective_evaluation.ipynb` | Each of those paths month by month: forecast tracking error, active return, turnover, the objective, the six exposures and the holdings |
| `factor_objective_attribution` | `notebooks/16_factor_objective_attribution.ipynb` | Each path's exposures, the six contributions with their standard errors, the residual, the factor share and the targeted total |

## The naive portfolios under the index mandate

Notebook 08 writes the tables of the naive tilt and notebook 09 those of the tilted index. Figures are fractions per year unless the column names basis points, and turnover is the mean one-way turnover a month. Each table that compares a naive portfolio with the optimised paths carries the seven paths' figures as recorded in `source/`.

| File | Notebook | What it holds |
|---|---|---|
| `naive_tilt_reproduction`, `tilted_index_reproduction` | 08, 09 | The optimised path of the sample covariance on three years of daily returns, rebuilt from the copied code: its realised tracking error beside the recorded one, the largest monthly differences, the band of 0.1 basis point a year and whether it passes |
| `naive_tilt_monthly`, `tilted_index_monthly` | 08, 09 | Each month: active return, one-way turnover, the benchmark's own turnover, largest active weight, effective number and number of industries held, the objective, the six active exposures and the weight removed from the tilted and excluded industries; for the tilted index also k, the limit that set it and the industry at which it binds |
| `naive_tilt_weights`, `tilted_index_weights` | 08, 09 | The weight of each of the 49 industries each month |
| `naive_tilt_measures`, `tilted_index_measures` | 08, 09 | Realised tracking error, active return before and after costs at 50 and 100 basis points, turnover, information ratios, realised beta, mean objective, exposure per basis point of realised tracking error, mean exposures, months above the turnover cap and the turnover of the first and the largest month |
| `naive_tilt_paired_tests` | 08 | The naive tilt's realised tracking error against each of the seven paths under the tilt alone: the difference with its standard error, interval, detectable difference, correlation, p-value and Holm-adjusted p-value of the paired test |
| `naive_tilt_returns_and_costs` | 08 | Realised tracking error, active return, turnover and net active return at the two cost levels, in basis points a year, for the naive tilt and the seven paths |
| `tilted_index_bootstrap` | 09 | The tilted index's exposure per basis point against each of the seven paths at the budget of 100 basis points: the difference, its 95 per cent interval, the p-value and the Holm-adjusted p-value of the paired block bootstrap |
| `tilted_index_beside_paths` | 09 | Tracking error, returns, turnover, costs, mean objective, exposure per basis point and the four targeted exposures for the tilted index and the seven paths |
| `tilted_index_budgets_75_and_150` | 09 | Realised tracking error and exposure per basis point of the five single-estimator paths at budgets of 75 and 150 basis points, as recorded |
| `tilted_index_k`, `tilted_index_k_set_at` | 09 | The range and median of k over the months, the months in which the bound and the floor set it, and the industries at which it was set |
| `naive_tilt_information_ratios`, `tilted_index_information_ratios` | 08, 09 | The information ratio of the naive portfolio and of each path before costs and at the two cost levels, each with its standard error from 2,000 block bootstrap resamples |
| `naive_tilt_realised_betas`, `tilted_index_realised_betas` | 08, 09 | The slope of each portfolio's monthly excess return on the benchmark's |
| `naive_tilt_attribution_monthly`, `tilted_index_attribution_monthly` | 08, 09 | Each month's six active exposures and factor contributions, the residual and the active return |
| `naive_tilt_attribution_summary`, `tilted_index_attribution_summary` | 08, 09 | Mean exposures, the six contributions per year with their standard errors, the factor total, the residual, the factor share and the targeted total |
| `naive_tilt_information_ratio_differences`, `tilted_index_information_ratio_differences` | 08, 09 | Written once the results were known: each difference in information ratio between the naive portfolio and a path, beside the two standard errors |
| `naive_tilt_spread` | 08 | Written once the results were known: the spread between the cap-weighted return of the 46 untilted industries and that of Coal, Oil and Util, its mean and standard deviation per year, its t-ratio and its share of positive months, with the largest error of the identity that makes the naive tilt's active return the removed weight times the spread |
