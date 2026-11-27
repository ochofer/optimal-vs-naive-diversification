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

## The optimised portfolios, read from risk-models-for-index-tracking

The six tables in `source/` are copied unchanged from the repository risk-models-for-index-tracking at commit ddbb75c, where they sit in `results/202608/` under the same names. The comparisons with the naive rules read the optimised portfolios' figures from them. `constants.SOURCE_TABLES` holds the SHA-256 of each, and `tests/test_source_copies.py` checks it.

| File | Written at that commit by | What it holds |
|---|---|---|
| `rolling_evaluation` | `notebooks/12_rolling_evaluation.ipynb` | For every path of the mandate study: realised and forecast tracking error, bias statistic, active return, turnover, holdings and cost |
| `active_returns` | `notebooks/12_rolling_evaluation.ipynb` | Each path's monthly active return |
| `attribution_summary` | `notebooks/13_factor_attribution.ipynb` | Each path's mean active exposures and the six factor contributions with their standard errors, the residual and the factor share |
| `factor_objective_evaluation` | `notebooks/15_factor_objective_evaluation.ipynb` | For each of the nineteen paths with a factor objective: realised and forecast tracking error, active return, turnover, cost, the four targeted exposures and the exposure per basis point of realised tracking error |
| `factor_objective_monthly` | `notebooks/15_factor_objective_evaluation.ipynb` | Each of those paths month by month: forecast tracking error, active return, turnover, the objective, the six exposures and the holdings |
| `factor_objective_attribution` | `notebooks/16_factor_objective_attribution.ipynb` | Each path's exposures, the six contributions with their standard errors, the residual, the factor share and the targeted total |
