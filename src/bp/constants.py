"""
Pre-committed numbers for the study.

Every band, gate, sample boundary and design parameter is defined here,
one per line, with its source beside it. A notebook may read these names; it
may not introduce numbers of its own. The replication bands (section 3)
and the design of the extension (section 5) were fixed on 10 September 2026,
before any of the rules' code was written. Three entries were changed after that
date; each carries the date of the change, the evidence for it, and what it
replaced, so that a reader can judge whether the change was a specification
settled by the paper's own text or a number tuned to the results.

DGU throughout means DeMiguel, Garlappi and Uppal (2009), "Optimal Versus
Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?",
Review of Financial Studies 22(5), 1915-1953. Page numbers are the journal's.
"""

# ---------------------------------------------------------------------------
# 1. Data: Ken French's library, downloaded at run time, never committed
# ---------------------------------------------------------------------------

FRENCH_BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"

# Every file the study reads. The vintage is whatever the library serves on the
# download date; the loader records the date, the SHA-256 of the zip and the
# CRSP vintage line printed at the top of each CSV.
FRENCH_FILES = {
    "factors3":   "F-F_Research_Data_Factors_CSV.zip",        # Mkt-RF, SMB, HML, RF, monthly from 1926-07
    "momentum":   "F-F_Momentum_Factor_CSV.zip",              # Mom, monthly from 1927-01
    "factors5":   "F-F_Research_Data_5_Factors_2x3_CSV.zip",  # Mkt-RF, SMB, HML, RMW, CMA, RF from 1963-07
    "ind10":      "10_Industry_Portfolios_CSV.zip",           # DGU "Industry" dataset
    "ind49":      "49_Industry_Portfolios_CSV.zip",           # the extension universe; carries firm counts and average size
    "size_bm25":  "25_Portfolios_5x5_CSV.zip",                # DGU "FF-1-factor" and "FF-4-factor" datasets
}

FRENCH_MISSING_CODES = (-99.99, -999.0)   # French's own convention, stated at the top of every portfolio file
FRENCH_RETURNS_ARE_PERCENT = True         # the loader divides by 100 once, at load time, and nowhere else

# ---------------------------------------------------------------------------
# 2. The DGU replication
# ---------------------------------------------------------------------------

DGU_SAMPLE_START = "1963-07"   # DGU Table 2, p. 1918, for every French-sourced dataset
DGU_SAMPLE_END = "2004-11"     # DGU Table 2, p. 1918
DGU_ESTIMATION_WINDOW = 120    # months; DGU section 2, p. 1927. M = 60 is in DGU's appendix and is out of scope.
DGU_RISK_AVERSION = 1.0        # gamma in the CEQ, DGU p. 1929: "the results we report are for the case of gamma = 1"
DGU_TCOST = 0.0050             # proportional cost per unit of one-way turnover; DGU p. 1929: 50 basis points, after Balduzzi and Lynch (1999)
TCOST_SENSITIVITY = 0.0100     # the one cost sensitivity reported: double the base cost
DGU_GMINC_LOWER_BOUND_FRACTION = 0.5   # g-min-c imposes w >= a * 1 with a = 1/(2N); DGU p. 1926
DGU_BS_COV_DOF = "M - N - 2"   # the Bayes-Stein covariance divides by M - N - 2; DGU equation (5), p. 1923

# Changed 22 September 2026: a specification the paper leaves ambiguous, settled
# by its own footnote and by replication. DGU's Lagrangian (8), p. 1925, shows
# the short-sale constraint alone, which with the normalisation of equation (1)
# would make gamma irrelevant. Footnote 22, p. 1934, says the constrained rules
# produce "corner solutions with all wealth invested in a single asset", which
# only happens when the budget constraint 1'w = 1 sits inside the optimisation
# with gamma = 1. Both readings were run: with the budget inside, mv-c on
# MKT/SMB/HML gives a Sharpe ratio of 0.1093 against the published 0.1084 and
# puts all wealth in one asset in 257 of 377 months; without it, 0.2382 and
# never. The other three datasets and the turnover and CEQ rows agree the same
# way. The reading that reproduces the paper's tables is used; the literal
# reading is kept as rules.mv_c_cone so the comparison can be rerun
# (notebook 03), and is not a reported rule.
DGU_CONSTRAINED_BUDGET_INSIDE = True

# The rules replicated: those whose only inputs are the window's
# sample moments (and, for Bayes-Stein, Jorion's prior built from them), plus
# the value-weighted market. g-min-c is min-c with the lower bound raised from
# 0 to 1/(2N) (DGU p. 1926). vw is included because its Sharpe ratio is the
# same 0.1138 in every French-sourced column of Table 3, which makes it a free
# check that the market series and the sample match the paper's.
DGU_RULES = ("ew", "mv", "bs", "min", "vw", "mv-c", "bs-c", "min-c", "g-min-c")
DGU_IN_SAMPLE_ROW = "mv (in sample)"   # DGU Table 3 row 2: mean-variance with M = T, the upper bound estimation error costs

# Excluded, each with the criterion. They are not built.
DGU_RULES_EXCLUDED = {
    "Bayesian diffuse-prior": "not reported by DGU (Table 1 note, p. 1917)",
    "dm": "Bayesian Data-and-Model (Pastor 2000); needs an asset-pricing prior, outside the moment-based set",
    "mp": "MacKinlay and Pastor (2000) missing-factor model; needs a maximum-likelihood factor structure, outside the moment-based set",
    "mv-min": "Kan and Zhou (2007) three-fund mixture of two rules already built; not part of the pre-specified set",
    "ew-min": "mixture of 1/N and minimum variance; not part of the pre-specified set",
    "multi-prior": "not reported by DGU (Table 1 note, p. 1917)",
}

# The datasets replicated: the four DGU built from French's site (DGU Table 2, p. 1918; Appendix A, pp. 1948-1949).
# Each is monthly excess returns over the T-bill rate from French's factor file.
DGU_DATASETS = {
    "Industry":     {"n_risky": 10, "factors": ("Mkt-RF",), "N": 11, "source": "ind10 + factors3"},
    "MKT/SMB/HML":  {"n_risky": 0,  "factors": ("Mkt-RF", "SMB", "HML"), "N": 3, "source": "factors3"},
    "FF-1-factor":  {"n_risky": 20, "factors": ("Mkt-RF",), "N": 21, "source": "size_bm25 + factors3"},
    "FF-4-factor":  {"n_risky": 20, "factors": ("Mkt-RF", "SMB", "HML", "Mom"), "N": 24, "source": "size_bm25 + factors3 + momentum"},
}
DGU_DATASETS_EXCLUDED = {
    "S&P Sectors": "Roberto Wessels' GICS sector data, not on French's site (DGU Appendix A.1)",
    "International": "MSCI country indices, not on French's site (DGU Appendix A.3)",
    "FF-3-factor": "DGU do not report it: 'very similar to FF-1-factor' (Table 3 note, p. 1931)",
}
DGU_EXCLUDE_LARGEST_SIZE_QUINTILE = True   # DGU footnote 24, p. 1949: the five largest-size portfolios of the 25 are dropped, leaving 20

# ---------------------------------------------------------------------------
# 3. Bands for the replication, written before the code ran
# ---------------------------------------------------------------------------

BAND_SHARPE_ABS = 0.03          # out-of-sample Sharpe ratio within 0.03 of DGU Table 3, per rule and dataset
CHECK_TOP3_RANKING = True        # the ranking of the top three rules within each dataset is preserved
BAND_TURNOVER_REL = 0.25        # turnover within 25% relative of DGU Table 5

# DGU Table 5 reports the unconstrained mean-variance rule's turnover at 606,594 times
# that of 1/N on the Industry dataset and 10,466 times on FF-1-factor. Those
# figures are dominated by the months in which the sample covariance is
# near-singular, and they move by orders of magnitude when French revises
# a single return. A 25% band on them tests the vintage and says nothing about
# the code. The band
# is therefore applied only where DGU's published relative turnover is below
# the value here; above it, the replicated figure is reported beside the
# published one with no pass or fail. Fixed 10 September 2026, before any
# of the rules' code existed.
BAND_TURNOVER_APPLIES_BELOW_RELATIVE = 100.0

# Changed 13 September 2026, after notebook 02 had run, on its evidence. The
# out-of-sample Sharpe band applies only to rules whose published relative
# turnover (DGU Table 5, panel A) is below the same level; a rule above it is
# reported beside the published figure with the range that ten basis points of
# noise produces, and carries no verdict. The level is the paper's own number
# and the turnover band already used it, so no new level enters here. The
# in-sample mean-variance row carries no verdict either: BAND_SHARPE_ABS was
# written for out-of-sample Sharpe ratios. Evidence: on the Industry, FF-1 and
# FF-4 datasets the unconstrained mean-variance rule moved by 0.12 to 0.25
# under ten basis points of noise, with the published figure inside the range,
# while the 1/N rows matched to the third decimal. Before the change the band
# applied to every out-of-sample row.
BAND_SHARPE_APPLIES_BELOW_RELATIVE = BAND_TURNOVER_APPLIES_BELOW_RELATIVE
BAND_SHARPE_DECISION_DATE = "2026-09-13"

# Sharpe ratios are compared on the same sample, 1963-07 to 2004-11, 120-month
# window, so the out-of-sample period is 1973-07 to 2004-11.
DGU_EXPECTED_T = 497           # months from 1963-07 to 2004-11 inclusive; a count, checked in notebook 01
DGU_EXPECTED_OOS = 377         # DGU_EXPECTED_T - DGU_ESTIMATION_WINDOW

# The replication extended to the latest month (notebook 07). Fixed 1 October
# 2026, before the notebook was written. The nine rules run through the same
# rolling evaluation on every month the vintage carries, from DGU_SAMPLE_START
# to its last month, and the measures are reported for three periods: the
# paper's out-of-sample period (1973-07 to 2004-11, the numbers of notebooks
# 02 and 03), the months since the paper (EXTENDED_NEW_PERIOD_START to the
# last month, every one of them out of sample for a window that begins 120
# months earlier), and the whole period. No published number exists for the
# new months, so the pre-committed statements are expectations, each reported
# as a count.
EXTENDED_NEW_PERIOD_START = "2004-12"   # the month after DGU's sample ends
# Expectations:
#  1. Count first: every dataset carries a return for every month from
#     DGU_SAMPLE_START to the vintage's last month, the four datasets end in
#     the same month, and the number of months is printed and recorded.
#  2. The paper's reading of Table 3 holds on the whole period: each
#     short-sale-constrained rule has a higher out-of-sample Sharpe ratio than
#     its unconstrained version on every dataset (mv-c against mv, bs-c
#     against bs, min-c against min; 12 comparisons).
#  3. Sample-based mean-variance is below 1/N on every dataset in the new
#     period and in the whole period (8 cells). The new months add about 260
#     to a problem that the formula of notebook 04 says needs thousands, so
#     nothing else is expected to change.
#  4. The number of cells in the new period in which a rule beats 1/N with a
#     Jobson-Korkie p-value below 0.05 is reported. On about 260 months the
#     standard error of a Sharpe-ratio difference is about 0.06, so few or
#     none are expected, and none would be claimed as a finding.
# Turnover inside a sub-period counts every rebalance that falls in it; the
# first out-of-sample month of the whole period has no rebalance, as in DGU.

# ---------------------------------------------------------------------------
# 4. DGU's analytical result and simulation (notebook 04)
# ---------------------------------------------------------------------------

# The analytical critical window (DGU Proposition 1, pp. 1937-1938; Figure 1, p. 1940).
# Panel E is the one calibrated to US stock-market data and the one the abstract quotes.
ANALYTIC_SHARPE_TANGENCY = 0.15    # S*, DGU Figure 1 panel E
ANALYTIC_SHARPE_1N = 0.12          # S_ew, DGU Figure 1 panel E
EXPECT_CRITICAL_M_LOWER = {25: 3000, 50: 6000}   # DGU p. 1941: "more than 3000 months" and "more than 6000 months"; the check is order of magnitude and direction in N

# The simulated dataset (DGU section 5.1, pp. 1941-1942).
SIM_RF_MEAN_ANNUAL = 0.02
SIM_RF_SD_ANNUAL = 0.02
SIM_FACTOR_MEAN_ANNUAL = 0.08
SIM_FACTOR_SD_ANNUAL = 0.16
SIM_ALPHA = 0.0
SIM_BETA_RANGE = (0.5, 1.5)          # loadings evenly spread
SIM_IDIO_VOL_RANGE = (0.10, 0.30)    # annual idiosyncratic volatility, uniform, cross-sectional mean 0.20
SIM_N = (10, 25, 50)
SIM_M = (120, 360, 6000)
SIM_T = 24000                        # months in one simulated history
SIM_SEED = 20260910                  # fixed so the run is reproducible; DGU's seed is unknown
# In one 24,000-month simulated history the standard error of a monthly Sharpe ratio is about
# 1/sqrt(24000) = 0.0065, so the comparison with DGU Table 6 uses the same band
# as the empirical tables, and in addition the sign of (mv minus 1/N) is checked
# against Table 6 in every (N, M) cell.
BAND_SIM_SHARPE_ABS = BAND_SHARPE_ABS
# Added 29 September 2026, when notebook 04 was written. Table 6 reports 1/N and
# "mv (true)" as constants across M within each N, so they are full-sample
# Sharpe ratios; the estimated rules are out of sample. The comparison follows
# that convention. As a second check, every rule is rerun on SIM_SPREAD_DRAWS
# alternative draws of the market (seeds 1 to SIM_SPREAD_DRAWS) and the
# published value is checked against the range they produce, the simulation's
# analogue of the fragility test in notebook 02.
SIM_SPREAD_DRAWS = 8

# Fat tails (notebook 05), an addition to the paper. Fixed 30 September 2026,
# before the notebook was written. The market above is rerun with every shock
# drawn from a Student-t distribution instead of a normal one, scaled so that
# the mean and covariance of returns are exactly those of the normal market:
# only the tails differ, and the tangency portfolio, S*, S_ew and the formula's
# critical window are the same numbers as in notebook 04. One scale draw per
# month is shared by the factor shock and every idiosyncratic shock (a
# multivariate t), so an extreme month hits all assets at once, which is how fat
# tails appear in markets. Months stay independent of one another; the
# normality assumption is relaxed and nothing else. The normal shocks are the
# same draws as notebook 04's (same seed), so each fat-tailed market is paired
# with its normal twin month by month.
SIM_T_DOF = (10, 5)                  # degrees of freedom. 10: excess kurtosis 1, about a broad index's monthly returns. 5: excess kurtosis 6, about an industry portfolio's. At 4 or below the fourth moment is infinite, the standard error of a Sharpe ratio is undefined, and no comparison could be read.
SIM_T_COMMON_SCALE = True            # one scale per month shared by all shocks (multivariate t); False would draw one scale per asset
# The crossing table: sample-based mean-variance against 1/N over a grid of
# windows, both measured on the same out-of-sample months, to locate the
# window at which the gap closes under each distribution. The formula's
# critical window for the market's own S* and S_ew is reported beside it.
SIM_CROSSING_WINDOWS = (120, 240, 360, 600, 1000, 2000, 3000, 4000, 6000, 9000, 12000)
# Expectations written before the run, each reported as a count of cells.
#  1. 1/N and mv (true), which use no estimates, have the same full-sample
#     Sharpe ratio under t shocks as under normal ones to within two standard
#     errors; a failure here would be a construction error.
#  2. Every estimated rule's Sharpe ratio in every (N, M) cell is no higher
#     under t shocks than under normal ones, beyond a slack of about one and a
#     half standard errors; the loss is expected to grow as the tails fatten
#     (5 against 10) and as the window shortens.
#  3. For N = 10 the crossing window is later under t shocks than under normal
#     ones. For N = 25 and 50, 1/N is so close to the tangency portfolio in
#     this market that no crossing is expected within 12,000 months under any
#     distribution, and the formula says so.
FAT_TAIL_MOMENT_CHECK_ABS = 0.013    # expectation 1: two standard errors of a 24,000-month Sharpe ratio
FAT_TAIL_DIRECTION_SLACK = 0.01      # expectation 2: a cell counts as in the expected direction if Sharpe(t) <= Sharpe(normal) + this

# Volatility that changes through time (notebook 06), the second addition to
# the paper. Fixed 1 October 2026, before the notebook was written. The market
# of notebook 04 is rerun with shocks whose volatility follows a GARCH(1,1)
# process (Bollerslev 1986), the standard model of volatility clustering: a
# large shock this month raises the volatility of next month's shock, and the
# effect decays slowly. The factor shock and every asset's idiosyncratic shock
# get their own, independent volatility process with the same parameters, so
# both the level and the shape of the covariance matrix move through time:
# when the factor's volatility is high relative to the assets' own, the
# correlations between assets are high, which is what markets do in a crisis.
# The unconditional mean and covariance are exactly those of the normal market
# (omega = 1 - alpha - beta puts the unconditional variance of each scaled
# shock at one), so the tangency portfolio, S*, S_ew and the formula's
# critical window are unchanged. The normal shocks are the same draws as
# notebook 04's, so the two markets are paired month by month. Months are no
# longer independent; the tails stay those of a normal distribution except for
# what the clustering itself produces (excess kurtosis 6 alpha^2 / (1 - beta^2
# - 2 alpha beta - 3 alpha^2), about 0.8 for these parameters).
SIM_GARCH_ALPHA = 0.10               # weight of last month's squared shock; a textbook monthly value
SIM_GARCH_BETA = 0.85                # weight of last month's variance; alpha + beta = 0.95 is the persistence, a half-life of a volatility shock of about 13 months
SIM_GARCH_OWN_PROCESS_PER_ASSET = True   # the factor and each idiosyncratic shock follow their own process; False would scale all shocks by one common volatility, which leaves the shape of the covariance unchanged and the rules' weights with it
# Expectations written before the run, each reported as a count of cells.
#  1. 1/N and mv (true) keep their full-sample Sharpe ratios to within
#     FAT_TAIL_MOMENT_CHECK_ABS of the normal market's; a failure is a
#     construction error.
#  2. Every estimated rule's Sharpe ratio in every (N, M) cell is no higher
#     under volatility clustering than in the normal market, beyond
#     FAT_TAIL_DIRECTION_SLACK. Unlike notebook 05, the loss is expected to be
#     visible, and largest for the rules that depend on the shape of the
#     covariance (min, min-c, g-min-c), because a 120-month average of a
#     covariance that moves is wrong in a known direction for the month that
#     follows.
#  3. For N = 10 the crossing window is later than in the normal market; for
#     N = 25 and 50 no crossing within 12,000 months under either market.
# Descriptive checks reported beside them: the first-order autocorrelation of
# the factor's squared return is about alpha (1 - alpha beta - beta^2) /
# (1 - 2 alpha beta - beta^2) = 0.18 under clustering and zero in the normal
# market, and the average correlation between assets is higher in the months
# of highest factor volatility than in the months of lowest.

# ---------------------------------------------------------------------------
# 5. The extension: constrained index tracking on the 49 industries
# ---------------------------------------------------------------------------

EXT_UNIVERSE = "ind49"
EXT_ESTIMATION_WINDOW = 120        # the same window as the replication, so one convention runs through the repository
EXT_REBALANCE = "monthly"
# The extension sample starts at the first month in which all 49 industries carry
# a return (French codes the early gaps as -99.99). That start month is a count:
# on the 202607 vintage, read on 10 September 2026, Hlth is the last industry to
# fill and does so in 1969-07. Notebook 01 asserts it on every run, so a vintage
# that moves it fails loudly.
EXT_SAMPLE_START = "1969-07"
EXT_SAMPLE_END = None              # the latest month the vintage carries

# The benchmark (the index the portfolio tracks). Count-first check: the
# cap-weighted combination of the 49 industries, weights from firm count times
# average firm size, must track the market factor plus the risk-free rate within
# 50 basis points a year of tracking error over the full sample. If it does not,
# the derived weights are dropped and the benchmark is the market series.
CAPW_TE_MAX_ANNUAL = 0.0050

# Constraints. Fixed 10 September 2026.
ACTIVE_WEIGHT_BOUND = 0.02         # each untilted industry within 2 percentage points of its benchmark weight; an absolute cap does not fit 49 industries whose benchmark weights run from under 0.5% to over 10%
TURNOVER_CAP_MONTHLY_ONE_WAY = 0.02   # one-way turnover per rebalance, against drifted weights; 2% a month is about 24% a year, the enhanced-indexing range
TILT_INDUSTRIES = ("Coal", "Oil", "Util")   # French's column names, stripped of padding
TILT_MAX_SHARE_OF_BENCHMARK = 0.5  # each tilted industry held at no more than half its benchmark weight, reported as a 50% reduction relative to the benchmark; a tilted industry's bounds are [0, 0.5 * benchmark], and ACTIVE_WEIGHT_BOUND does not apply to it, because the two would conflict for any industry above 4% of the benchmark
LONG_ONLY = True

# Constraint sets, cumulative, reported in this order.
CONSTRAINT_SETS = {
    "C0": ("long_only",),
    "C1": ("long_only", "active_weight_bound"),
    "C2": ("long_only", "active_weight_bound", "turnover_cap"),
    "C3": ("long_only", "active_weight_bound", "turnover_cap", "tilt"),
}
# The optimiser also accepts an exclusion list (weight zero on named assets). It
# is built and tested for later use and is not one of the reported constraint
# sets.

# Covariance estimators. LW_TARGET is provisional until the shrinkage target
# used by the constrained-portfolio literature has been checked before notebook
# 10; if a different Ledoit-Wolf target is standard for constrained portfolios,
# the target follows it and this line records the change.
COV_ESTIMATORS = ("sample", "ledoit_wolf", "factor", "pca")
LW_TARGET = "constant_correlation"     # Ledoit and Wolf (2004a), "Honey, I Shrunk the Sample Covariance Matrix"
FACTOR_MODEL_FACTORS = ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom")   # the Fama-French five factors plus momentum; the estimator is B F B' plus a diagonal of residual variances, B estimated in the same estimation window
PCA_N_COMPONENTS = 5                   # five components plus a diagonal idiosyncratic term
PCA_PC1_MARKET_CORR_MIN = 0.95         # the first component's correlation with the cap-weighted market return
PCA_USE_COVARIANCE = True              # covariance, not correlation, of monthly excess returns
PCA_SIGN_RULE = "positive market loading"
PCA_WINDOWS = {                        # three pre-specified windows; loading stability is the finding and carries no pass or fail
    "to_2019":   (None, "2019-12"),
    "2020_2022": ("2020-01", "2022-12"),
    "from_2023": ("2023-01", None),
}

# Attribution: factor-based attribution of each constrained portfolio's
# realised active return against the factors above, contribution by factor
# plus residual, with the identity as the check.
ATTRIBUTION_FACTORS = FACTOR_MODEL_FACTORS
ATTRIBUTION_IDENTITY_MAX_ABS_ERROR = 1e-9        # contributions plus residual minus active return, per month, in return units

# Specification count, written down before the code runs and reported.
# Replication: one specification per rule and dataset. Extension:
EXT_SPEC_COUNT = len(COV_ESTIMATORS) * len(CONSTRAINT_SETS)   # 16 optimised specifications
EXT_COST_LEVELS = (DGU_TCOST, TCOST_SENSITIVITY)              # each reported net of cost at both levels; the cost is applied after the fact and does not enter the optimisation

# ---------------------------------------------------------------------------
# 6. Output conventions
# ---------------------------------------------------------------------------

OUTPUT_DIR = "outputs"
PROVENANCE_FILE = "outputs/provenance_french.json"   # download date, URL, SHA-256 and CRSP vintage line per file
TIMEZONE = "Europe/Amsterdam"
