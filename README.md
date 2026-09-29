# Optimal versus naive diversification: a replication, and what a tracking-error mandate changes

Work in progress. The replication table (notebooks 02 and 03) is produced on the CRSP 202607 vintage of French's files; the extension has not started.

I replicate DeMiguel, Garlappi and Uppal (2009), "Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?" (Review of Financial Studies 22(5), 1915-1953), on the four of their datasets that come from Ken French's library, and then ask their question of a long-only index-tracking mandate: once a portfolio has to stay close to its benchmark under a weight bound, a turnover cap and an industry tilt, does the choice of covariance estimator still matter? The extension compares four estimators (sample, Ledoit-Wolf shrinkage, a Fama-French factor model, a principal-component factor model) on French's 49 industry portfolios and reports what each constraint costs in ex-ante tracking error, with a factor-based attribution of the realised active return.

## Status

| Notebook | What it establishes | State |
|---|---|---|
| 01 `french_loader` | The six French files, their vintage, and the counts DGU's Table 2 implies | built |
| 02 `1N_vs_mean_variance` | 1/N and sample mean-variance through the rolling window, beside Tables 3 to 5; the fragility of the mean-variance rows | built |
| 03 `shrinkage_and_constraints` | Bayes-Stein, minimum variance and the short-sale-constrained rules; the full comparison: 29 of 30 gated Sharpe cells and 30 of 30 turnover cells within the bands | built |
| 04 to 06 | DGU's simulation, the extension of the sample to today, the cap-weight check | not started |
| 07 to 11 | PCA, the four estimators, the optimiser, the rolling backtest, attribution | not started |

## How to run

Each notebook runs from a blank Google Colab runtime: upload it and run all cells. It writes the code it needs into `src/bp/` and downloads French's files at run time. Nothing from French's library is committed; `outputs/provenance_french.json` records the date, the SHA-256 of each zip and the CRSP vintage every output was computed on. French revises history, so a rerun on a later vintage will not reproduce every digit, and the provenance file is what says why.

From a checkout: `pip install -r requirements.txt`, then `python3 -m pytest tests`, then open the notebooks. `build_notebooks.py` regenerates every notebook from its prose and the modules in `src/bp/`; the notebooks are build artefacts and are committed without outputs.

## What is pre-committed

The tolerances the replication has to meet, the sample boundaries and every design parameter of the extension are in `src/bp/constants.py`, each with its source, written before any strategy code ran. The published numbers I compare against are in `src/bp/dgu_published.py`; `tests/test_dgu_published.py` re-reads them digit by digit from the journal PDF when the PDF is present on the machine (it is not in the repository).

## Layout

```
build_notebooks.py      generates notebooks/ from prose here and code in src/bp/
src/bp/constants.py     every pre-committed number, with its source
src/bp/french_loader.py download, provenance, parsing of French's files
src/bp/dgu_published.py DGU's Tables 3, 4, 5 and 6, transcribed and tested
notebooks/              one concept per notebook, run in order
outputs/                portfolio-level tables and provenance records
tests/                  known-answer checks that run without network
```

Carlo Hofer, 2026.
