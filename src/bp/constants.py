"""
Pre-committed numbers for the study.

Every band, gate, sample boundary and design parameter is defined here, one
per line, with its source beside it. A notebook may read these names; it may
not introduce numbers of its own. The replication bands (section 3) and the
design of the extension (section 5) were fixed on 10 September 2026, before any
of the rules' code was written. The expectations each notebook tests are
stated in that notebook's introduction and were written before its code; where
a level was changed after a run, the comment beside it says so, with the date
and the reason, so that a reader can judge whether the change was a
specification settled by the paper's own text or a number tuned to the results.

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
    # Daily files, for the extension's covariance estimators (section 5).
    "ind49_daily":    "49_Industry_Portfolios_daily_CSV.zip",        # value- and equal-weighted daily returns from 1926-07-01
    "factors3_daily": "F-F_Research_Data_Factors_daily_CSV.zip",     # Mkt-RF, SMB, HML, RF daily from 1926-07-01
    "factors5_daily": "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip", # Mkt-RF, SMB, HML, RMW, CMA, RF daily from 1963-07-01
    "momentum_daily": "F-F_Momentum_Factor_daily_CSV.zip",           # Mom daily from 1926-11-03
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

# Settled 22 September 2026, a specification the paper leaves ambiguous. DGU's
# Lagrangian (8), p. 1925, shows the short-sale constraint alone; footnote 22,
# p. 1934, says the constrained rules produce "corner solutions with all wealth
# invested in a single asset", which only happens when the budget constraint
# 1'w = 1 sits inside the optimisation with gamma = 1. With the budget inside,
# mv-c on MKT/SMB/HML gives a Sharpe ratio of 0.1093 against the published
# 0.1084 and a corner solution in 257 of 377 months; without it, 0.2382 and no
# corner. The reading that reproduces the paper's tables is used; the literal
# reading is kept as rules.mv_c_cone for comparison (notebook 03).
DGU_CONSTRAINED_BUDGET_INSIDE = True

# The rules replicated: those whose only inputs are the window's sample moments
# (and, for Bayes-Stein, Jorion's prior built from them), plus the value-weighted
# market, whose Sharpe ratio is the same 0.1138 in every French-sourced column
# of Table 3 and so checks that the market series and the sample match the paper's.
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

# DGU Table 5 reports the unconstrained mean-variance rule's turnover at 606,594
# times that of 1/N on the Industry dataset and 10,466 times on FF-1-factor.
# Those figures are dominated by the months in which the sample covariance is
# near-singular and move by orders of magnitude when French revises a single
# return, so the band applies only where DGU's published relative turnover is
# below the level here; above it, the replicated figure is reported beside the
# published one with no pass or fail. Fixed 10 September 2026.
BAND_TURNOVER_APPLIES_BELOW_RELATIVE = 100.0

# Changed 13 September 2026, after notebook 02 had run, on its evidence: the
# out-of-sample Sharpe band applies only to rules whose published relative
# turnover (DGU Table 5, panel A) is below the same level, and the in-sample
# mean-variance row carries no verdict. Evidence: on the Industry, FF-1 and FF-4
# datasets the unconstrained mean-variance rule moved by 0.12 to 0.25 in Sharpe
# ratio under ten basis points of noise, with the published figure inside the
# range, while the 1/N rows matched to the third decimal. Before the change the
# band applied to every out-of-sample row. The level is the paper's own number,
# already used by the turnover band.
BAND_SHARPE_APPLIES_BELOW_RELATIVE = BAND_TURNOVER_APPLIES_BELOW_RELATIVE
BAND_SHARPE_DECISION_DATE = "2026-09-13"

# Sharpe ratios are compared on the same sample, 1963-07 to 2004-11, 120-month
# window, so the out-of-sample period is 1973-07 to 2004-11.
DGU_EXPECTED_T = 497           # months from 1963-07 to 2004-11 inclusive; a count, checked in notebook 01
DGU_EXPECTED_OOS = 377         # DGU_EXPECTED_T - DGU_ESTIMATION_WINDOW

# The replication extended to the latest month (notebook 07), fixed 1 October
# 2026 before the notebook's code: the nine rules on every month the vintage
# carries, reported for the paper's out-of-sample period, the months since the
# paper and the whole period. The expectations are in the notebook's introduction.
EXTENDED_NEW_PERIOD_START = "2004-12"   # the month after DGU's sample ends

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
# In one 24,000-month history the standard error of a monthly Sharpe ratio is
# about 1/sqrt(24000) = 0.0065, so the comparison with DGU Table 6 uses the same
# band as the empirical tables, plus the sign of (mv minus 1/N) in every cell.
BAND_SIM_SHARPE_ABS = BAND_SHARPE_ABS
# Table 6 reports 1/N and "mv (true)" as full-sample Sharpe ratios and the
# estimated rules out of sample; the comparison follows that convention. As a
# second check every rule is rerun on alternative draws of the market (seeds 1
# to SIM_SPREAD_DRAWS) and the published value is checked against their range.
SIM_SPREAD_DRAWS = 8

# Fat tails (notebook 05), an addition to the paper, fixed 30 September 2026
# before the notebook's code. The market above is rerun with every shock drawn
# from a Student-t distribution, scaled so that the mean and covariance of
# returns are exactly those of the normal market; one scale draw per month is
# shared by all shocks (a multivariate t), so an extreme month hits all assets
# at once. The normal shocks are the same draws as notebook 04's.
SIM_T_DOF = (10, 5)                  # degrees of freedom. 10: excess kurtosis 1, about a broad index's monthly returns. 5: excess kurtosis 6, about an industry portfolio's. At 4 or below the fourth moment is infinite and the standard error of a Sharpe ratio is undefined.
SIM_T_COMMON_SCALE = True            # one scale per month shared by all shocks (multivariate t); False draws one scale per shock series, which changes the shape of the month's co-movement as well as its size
# The crossing table: sample-based mean-variance against 1/N over a grid of
# windows, to locate the window at which the gap closes under each distribution.
SIM_CROSSING_WINDOWS = (120, 240, 360, 600, 1000, 2000, 3000, 4000, 6000, 9000, 12000)
FAT_TAIL_MOMENT_CHECK_ABS = 0.013    # notebook 05, expectation 1: two standard errors of a 24,000-month Sharpe ratio
FAT_TAIL_DIRECTION_SLACK = 0.01      # notebook 05, expectation 2: a cell counts as in the expected direction if Sharpe(t) <= Sharpe(normal) + this
# One test added after notebook 05's first run (6 October 2026), fixed here before
# its code and labelled in the notebook: the fat-tailed market rerun with one
# scale per shock series (common_scale False), so that an extreme month changes
# the shape of the estimated covariance as well as its level. Expectation P1a:
# the mean change in Sharpe ratio across the seven estimated rules and the nine
# cells of the Table 6 grid is more negative than under the common scale at both
# degrees of freedom. P1b: the rules whose weights depend on the shape of the
# covariance and use no means lose more on average than the other estimated rules.
FAT_TAIL_SHAPE_RULES = ("min", "min-c", "g-min-c")   # P1b: the minimum-variance rules

# Volatility that changes through time (notebook 06), the second addition to
# the paper, fixed 1 October 2026 before the notebook's code. The market of
# notebook 04 is rerun with shocks whose volatility follows a GARCH(1,1) process
# (Bollerslev 1986); the factor shock and every asset's idiosyncratic shock get
# their own process with the same parameters, so both the level and the shape
# of the covariance matrix move through time, while the unconditional mean and
# covariance are exactly those of the normal market (omega = 1 - alpha - beta).
# The expectations of notebooks 05 and 06 are in their introductions and use
# the two levels above.
SIM_GARCH_ALPHA = 0.10               # weight of last month's squared shock; a textbook monthly value
SIM_GARCH_BETA = 0.85                # weight of last month's variance; alpha + beta = 0.95 is the persistence, a half-life of a volatility shock of about 13 months
SIM_GARCH_OWN_PROCESS_PER_ASSET = True   # the factor and each idiosyncratic shock follow their own process; False would scale all shocks by one common volatility, which leaves the shape of the covariance unchanged

# ---------------------------------------------------------------------------
# 5. The extension: constrained index tracking on the 49 industries
# ---------------------------------------------------------------------------

EXT_UNIVERSE = "ind49"
EXT_ESTIMATION_WINDOW = 120        # the same window as the replication, so one convention runs through the repository
EXT_REBALANCE = "monthly"
# The extension sample starts at the first month in which all 49 industries carry
# a return (French codes the early gaps as -99.99): Hlth is the last industry to
# fill and does so in 1969-07. Notebook 01 asserts it on every run.
EXT_SAMPLE_START = "1969-07"
EXT_SAMPLE_END = None              # the latest month the vintage carries

# The benchmark (the index the portfolio tracks): the cap-weighted combination
# of the 49 industries, weights from firm count times average firm size, must
# track the market factor plus the risk-free rate within this tracking error a
# year over the full sample (notebook 08). If it does not, the derived weights
# are dropped and the benchmark is the market series.
CAPW_TE_MAX_ANNUAL = 0.0050

# Notebook 08, the cap-weight check, fixed 1 October 2026 before its code. The
# weight of industry i in month t is its firm count times its average firm size
# in French's file for month t, divided by the sum over the 49 industries;
# French measures both at the start of month t, so the weight uses nothing
# unknown when the month begins. The previous-month reading is run beside it as
# a check of this timing, and the notebook stops if it tracks more closely.
CAPW_WEIGHT_TIMING = "same_month"
CAPW_WEIGHT_TIMING_ALTERNATIVE = "previous_month"   # reported beside the chosen timing, never used as the benchmark
CAPW_MARKET_SERIES = ("Mkt-RF", "RF")                # the market series is Mkt-RF plus RF, so that both sides are plain returns
CAPW_REPORT_MONTHS = ("first", "2004-11", "last")

# The direct test of where the benchmark's gap to the market comes from
# (notebook 08, second part), fixed 1 October 2026 before its code. French forms
# the industry portfolios once a year at the end of June from the firms that
# have an SIC code then, while the market return takes in a firm from its first
# full month of trading, so between one July and the next the market holds
# firms that no industry portfolio holds. The test needs the firm list of each
# portfolio each month, which French does not publish, so it runs on the CRSP
# monthly stock file (WRDS, under Queen Mary University of London's
# subscription), the one use of data outside French's library in the study.
# The CRSP data stay on the machine that holds them: no notebook reads them,
# the repository carries none, and only the aggregates in
# DIRECT_TEST_RESULTS_FILE are published, with CRSP cited by name. The market
# universe is CRSP share codes 10 and 11 on NYSE, AMEX and NASDAQ, weighted by
# start-of-month market equity; the June-formed universe is the firms of that
# market that were in it at the end of June of the formation year with a
# positive SIC code. The script is checks/crsp_direct_test.py; its pure
# functions are in bp.direct_test.
DIRECT_TEST_SHARE_CODES = (10, 11)
DIRECT_TEST_EXCHANGE_CODES = (1, 2, 3)
DIRECT_TEST_FORMATION_MONTH = 6          # the end of June
DIRECT_TEST_MARKET_TE_MAX = 0.0020       # expectation 1: the CRSP market universe tracks French's market return within 20 basis points a year
DIRECT_TEST_MIN_CORRELATION = 0.80       # expectation 2: correlation of the predicted gap with the observed one
DIRECT_TEST_SLOPE_RANGE = (0.8, 1.2)     # expectation 2: slope of the observed gap on the predicted one
DIRECT_TEST_RESIDUAL_TE_MAX = 0.0025     # expectation 4: tracking error of what the explanation leaves, 25 basis points a year
DIRECT_TEST_RESULTS_FILE = "checks/results_crsp_direct_test.json"   # aggregates only; committed

# Constraints. Fixed 10 September 2026; the sources for the levels are in
# notebook 11, "Where the numbers come from".
ACTIVE_WEIGHT_BOUND = 0.02         # each untilted industry within 2 percentage points of its benchmark weight; an absolute cap does not fit 49 industries whose benchmark weights run from under 0.5% to over 10%
TURNOVER_CAP_MONTHLY_ONE_WAY = 0.02   # one-way turnover per rebalance, against drifted weights; 2% a month is about 24% a year, the enhanced-indexing range
TILT_INDUSTRIES = ("Coal", "Oil", "Util")   # French's column names, stripped of padding
TILT_MAX_SHARE_OF_BENCHMARK = 0.5  # each tilted industry held at no more than half its benchmark weight, a 50% reduction relative to the benchmark; a tilted industry's bounds are [0, 0.5 * benchmark], and ACTIVE_WEIGHT_BOUND does not apply to it, because the two would conflict for any industry above 4% of the benchmark
LONG_ONLY = True

# Constraint sets, cumulative, reported in this order. C3 is the mandate: the
# tilt with beta neutrality and the exclusions. Beta neutrality and the
# exclusions were added on 4 October 2026, after notebook 11's checks D1 to D4
# and before notebook 12's code, because the tilt's hedge left a beta bet
# standing when the covariance was noisy and bought tobacco and weapons. The
# tilt alone is CONSTRAINT_SET_TILT_ONLY, the C3 of the first design, reported
# beside the mandate in notebooks 11 and 12 so that the cost of the two
# additions is visible.
CONSTRAINT_SETS = {
    "C0": ("long_only",),
    "C1": ("long_only", "active_weight_bound"),
    "C2": ("long_only", "active_weight_bound", "turnover_cap"),
    "C3": ("long_only", "active_weight_bound", "turnover_cap", "tilt", "beta_neutral", "exclusion"),
}
CONSTRAINT_SET_TILT_ONLY = ("long_only", "active_weight_bound", "turnover_cap", "tilt")   # the C3 of the design of 10 September 2026
MANDATE_EXCLUSIONS = ("Smoke", "Guns")   # tobacco and weapons, the standard exclusions of Dutch institutional mandates, in French's industry names; weight zero

# The data the covariance estimators see, fixed 1 October 2026. The 120-month
# window is the paper's convention and gives 49 x 120 = 5,880 returns for the
# 1,225 entries of a 49-industry covariance matrix, fewer than five per entry.
# Practitioners estimate from daily returns (three years hold about 756 trading
# days, 30 observations per entry), impose structure, and weight recent days
# more; the extension does all three. Each estimator is built at two data
# frequencies: "monthly_120", the last EXT_ESTIMATION_WINDOW months of monthly
# excess returns, and "daily_3y", the last EXT_COV_DAILY_WINDOW_YEARS years of
# daily excess returns scaled to a monthly covariance by DAILY_TO_MONTHLY_SCALE
# (notebook 10 tests that scaling). A trading day on which any industry has no
# return (one in the sample, Softw on 1971-03-11) is left out of the window.
EXT_COV_FREQUENCIES = ("monthly_120", "daily_3y")
EXT_COV_DAILY_WINDOW_YEARS = 3
EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY = (1, 5)   # reported for the sample estimator only, no verdict
DAILY_TO_MONTHLY_SCALE = 21                        # 252 trading days a year divided by 12
EXT_COV_EWMA_HALFLIFE_DAYS = 252                   # the recency-weighted sensitivity: a half-life of one year of trading days, the RiskMetrics setting of Dom, Howard, Jansen and Lohre (2024, section 3.3.2); 126 until 3 October 2026, changed on reading that paper, before notebook 10's code

# Covariance estimators. The shrinkage target follows Dom, Howard, Jansen and
# Lohre (2024), the paper the design named as its reference, checked on
# 3 October 2026 before notebook 10's code: their linear shrinkage pulls the
# sample covariance towards a scaled identity matrix (Ledoit and Wolf 2004b),
# and their footnote 11 reports that the constant-correlation target gave
# inferior results. The same paper estimates from three years of daily returns
# and rebalances monthly, and finds that under long-only constraints the
# differences between estimators shrink, which is notebook 10's expectation 3.
COV_ESTIMATORS = ("sample", "ledoit_wolf", "factor", "pca")
LW_TARGET = "scaled_identity"          # Ledoit and Wolf (2004b), "A well-conditioned estimator for large-dimensional covariance matrices"; was "constant_correlation" until 3 October 2026
LW_TARGET_SENSITIVITY = "constant_correlation"   # Ledoit and Wolf (2004a), "Honey, I Shrunk the Sample Covariance Matrix"; reported, no verdict
FACTOR_MODEL_FACTORS = ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom")   # the Fama-French five factors plus momentum; the estimator is B F B' plus a diagonal of residual variances, B estimated in the same estimation window
PCA_N_COMPONENTS = 5                   # five components plus a diagonal idiosyncratic term
PCA_PC1_MARKET_CORR_MIN = 0.95         # notebook 09, expectation 2: the first component's correlation with the cap-weighted market return
PCA_USE_COVARIANCE = True              # covariance, not correlation, of monthly excess returns
PCA_SIGN_RULE = "positive market loading"
PCA_WINDOWS = {                        # three pre-specified windows; loading stability is the finding and carries no pass or fail
    "to_2019":   (None, "2019-12"),
    "2020_2022": ("2020-01", "2022-12"),
    "from_2023": ("2023-01", None),
}

# Notebook 09, the principal components of the 49 industries, fixed 1 October
# 2026 before its code; the expectations are in its introduction.
PCA_REPORT_COMPONENTS = 10
PCA_PARALLEL_DRAWS = 200
PCA_PARALLEL_PERCENTILE = 95
PCA_PARALLEL_SEED = 20260910
# Set after notebook 09 ran, as its design said: the first component's
# correlation with the benchmark fell below PCA_PC1_MARKET_CORR_MIN in the
# window from 2023 (0.837), so notebook 10's PCA estimator takes the
# benchmark's excess return as its first factor. Parallel analysis found two
# components above noise; PCA_N_COMPONENTS stays at five and the two-component
# version is reported beside it.
PCA_FIRST_COMPONENT = "market"        # notebook 10: the benchmark's excess return is the first factor; "data" would take it from the eigenvectors
PCA_N_COMPONENTS_SENSITIVITY = 2      # the parallel-analysis count on the full sample, reported beside PCA_N_COMPONENTS

# Notebook 10, the four covariance estimators, fixed 3 October 2026 before its
# code. The estimators, data frequencies, tests and expectations are stated in
# the notebook's introduction and in covariance.py.
COV_EVAL_START = "1979-07"            # 1969-07 plus 120 months; the three-year daily window starts 1972-07 and is the shorter requirement
COV_TEST_ACTIVE_DRAWS = 200           # random active-weight vectors for the calibration test
COV_TEST_SEED = 20260910
COV_LONG_ONLY_RANGE_MAX = 0.01        # expectation 3: one percentage point of annualised volatility across the four estimators on daily data
COV_SCALE_RATIO_RANGE = (0.8, 1.25)   # expectation 4: the ratio of the benchmark's realised monthly variance to 21 times its daily variance
# Three tests added after notebook 10's first run (4 October 2026), each fixed
# here before its code and labelled in the notebook: P1, a scale correction by
# the variance ratio of Lo and MacKinlay (1988), one number from the benchmark's
# daily returns that multiplies the daily covariance in place of
# DAILY_TO_MONTHLY_SCALE alone; P2, bias statistics by decade; P3, trading costs
# of the minimum-variance portfolios at EXT_COST_LEVELS.
COV_SCALE_VR_HORIZON_DAYS = DAILY_TO_MONTHLY_SCALE   # the horizon of the variance ratio: one month of trading days
COV_SCALE_VR_WINDOW_YEARS_SENSITIVITY = 10           # P1 sensitivity: the variance ratio from ten years of daily benchmark returns
COV_POST_RUN_DECADES_MIN_CLOSER = 4                  # P1a: of five decades, the corrected forecast is closer to calibrated in at least this many
COV_POST_RUN_COST_MIN_VARIANTS = 6                   # P3a and P3b: of eight main variants, the long-only portfolio beats the unconstrained one net of cost in at least this many

# Notebook 11, the optimiser, fixed 4 October 2026 before its code; the
# constraints themselves date from 10 September. The problem, the infeasible-month
# rule and the expectations are stated in the notebook's introduction and in
# optimiser.py.
OPT_SOLVER = "CLARABEL"                  # interior-point solver shipped with cvxpy; deterministic
OPT_SOLVER_OPTIONS = {"tol_gap_abs": 1e-12, "tol_gap_rel": 1e-12, "tol_feas": 1e-10}   # tighter than the solver's defaults (1e-8), which left weights 1e-4 off an independent solver's on a test problem
OPT_SOLVER_OPTIONS_ROBUST = {"tol_gap_abs": 1e-9, "tol_gap_rel": 1e-9, "tol_feas": 1e-9}   # the robust problem is written with second-order cones, on which the solver reaches 1e-9 and reports 1e-12 as inaccurate; the objective agrees with the 1e-12 run to 1e-10 on the test problems
OPT_TOL = 1e-6                           # feasibility checks on weights, bounds and turnover; also "binding" means within this of the limit
OPT_TOL_TE = 1e-6                        # expectation 2a: a forecast tracking error below this, per year, counts as zero
OPT_TILT_TE_MAX_ANNUAL = 0.01            # expectation 3: 100 basis points a year, the enhanced-indexing ex-ante limit (Robeco's composite ran at 1.06%, J.P. Morgan quotes below 2%; sources in notebook 11)
OPT_REPORT_MONTHS = ("first_eval", "2004-11", "last")   # first_eval is COV_EVAL_START, the first month with both windows
OPT_SPEED_LIMIT_STEPS = (1, 6, 12, 24)   # expectation 5: rebalances reported on the journey from 1/N to the benchmark
# Checks D1 to D4 on the practical problem behind the tilt's hedge, added after
# notebook 11's first run (4 October 2026), each fixed here before its code.
OPT_D1_MARKET_SHARE_MAX = 0.05         # D1a: the market part of the tilt's forecast active variance is below this share in every month-estimator pair
OPT_D2_TE_RISE_MAX = 0.0001            # D2a: a beta-neutral constraint raises the forecast tracking error by less than one basis point a year in every pair
OPT_D3_EXCLUDE = ("Smoke",)            # D3: the hedge's tobacco purchase refused, its cost reported
# The fixes F1 to F3 (4 October 2026, before notebook 12's code): beta neutrality
# and the exclusions join C3 (above), and a robust portfolio, the weights whose
# largest forecast active variance across the estimators' covariances is
# smallest (Goldfarb and Iyengar 2003; Tutuncu and Koenig 2004), joins the
# rolling evaluation as a variant. Its beta neutrality holds under the average
# of the five beta vectors, because one equality per covariance was infeasible
# at 1979-07 under the mandate's bounds.
OPT_FIX_RISE_MAX = 0.0015              # F2: the mandate's C3 costs less than 15 basis points a year more than the tilt alone
ROBUST_VARIANT = ("robust", "all_five")   # the robust portfolio: minimax over the five covariances
# Check D5 on the solver, added after notebook 12's first run (6 October 2026),
# fixed here before its code: at this month the index moved more than the cap
# allows, no portfolio satisfied the cap and the tilt at once, and the solver
# reported "optimal" with weights that fail the independent check. The
# optimiser therefore finds the smallest feasible turnover first and never
# poses a capped problem that has no solution; the check of every returned
# portfolio stays.
OPT_D5_MONTH = "1984-07"

# Notebook 12, the rolling evaluation, fixed 4 October 2026 before its code: one
# path per specification, each portfolio built on the data before its month,
# judged on realised tracking error, calibration of the forecasts, active
# return net of costs, turnover and holdings. The expectations are in the
# notebook's introduction.
EVAL_TE_RANGE_MAX = 0.0010           # expectation 2: 10 basis points a year across the four daily estimators
EVAL_BIAS_RANGE = (0.8, 1.25)        # expectation 3, the same band as COV_SCALE_RATIO_RANGE
EVAL_RELAX_SHARE_MAX = 0.10          # expectation 6: at most one month in ten with a relaxed cap
EVAL_START_PORTFOLIO = "benchmark"   # every path starts as the index
EVAL_BENCHMARK_TOL = 1e-6            # expectation 1: an active return below this a month counts as holding the benchmark; written as 1e-10 and set to the solver's precision (about 1e-7) before the recorded run
# Expectations 8 and 9, added after notebook 12's first run (6 October 2026),
# each fixed here before its code and labelled in the notebook. RiskMetrics
# joins as a seventh variant because Dom, Howard, Jansen and Lohre (2024) find
# that time dynamics matter more than shrinkage or factor structure; the
# calibration multiplies each forecast by the ratio of realised to forecast
# tracking error over the previous EVAL_CALIBRATION_WINDOW months of the same
# path, using only months before the forecast.
EWMA_VARIANT = ("sample", "daily_5y_ewma")   # the seventh variant: RiskMetrics, as in notebook 10's sensitivity
EVAL_CALIBRATION_WINDOW = 60                 # months of a path's own past the calibration uses; a standard deviation from 60 observations has a standard error of about 9%
EVAL_CALIBRATION_MIN = 24                    # the forecast is left as it is while fewer months are available
EVAL_CALIBRATED_BIAS_RANGE = (0.85, 1.15)    # expectation 9: the calibrated bias statistic under C3, four daily estimators

# Notebook 13, the factor attribution, fixed 6 October 2026 before its code: each
# path's monthly active return split into the contributions of the six factors
# (the active exposure to each, from the industries' betas estimated on the data
# before the month, times the factor's return in the month) plus a residual, the
# industries' own returns; the identity is the check. The paths attributed are
# the seven variants under the mandate's C3 and under the tilt alone, rebuilt
# from the modules; the expectations are in the notebook's introduction.
ATTRIBUTION_FACTORS = FACTOR_MODEL_FACTORS
ATTRIBUTION_IDENTITY_MAX_ABS_ERROR = 1e-9        # expectation 1: contributions plus residual minus active return, per month, in return units
ATTRIBUTION_SETS = ("C3", "C3 tilt only")        # the two constraint sets whose paths are attributed
ATTRIBUTION_REPRODUCTION_TOL = 0.00001           # expectation 1: the rebuilt paths reproduce notebook 12's realised tracking errors within 0.1 basis point a year
ATTRIBUTION_REFERENCE_TE = {                     # notebook 12's realised tracking errors, per year, for the reproduction check
    ("sample, daily 3y", "C3"): 0.0084654, ("ledoit_wolf, daily 3y", "C3"): 0.0084820, ("factor, daily 3y", "C3"): 0.0093449,
    ("pca, daily 3y", "C3"): 0.0091482, ("sample, monthly 120", "C3"): 0.0095761, ("robust, all five", "C3"): 0.0087358,
    ("RiskMetrics, daily 5y", "C3"): 0.0084278,
    ("sample, daily 3y", "C3 tilt only"): 0.0080276, ("ledoit_wolf, daily 3y", "C3 tilt only"): 0.0080282, ("factor, daily 3y", "C3 tilt only"): 0.0088296,
    ("pca, daily 3y", "C3 tilt only"): 0.0086722, ("sample, monthly 120", "C3 tilt only"): 0.0090924, ("robust, all five", "C3 tilt only"): 0.0082305,
    ("RiskMetrics, daily 5y", "C3 tilt only"): 0.0079698,
}
ATTRIBUTION_MARKET_EXPOSURE_MAX = 0.05           # expectation 2: the mean active exposure to Mkt-RF, in absolute value, for every path
ATTRIBUTION_SIGN_AGREEMENT_MIN = 4               # expectation 3: of the five factors other than the market, the number whose mean active exposure under the mandate has the same sign for all seven variants
ATTRIBUTION_FACTOR_SHARE_MAX = 0.5               # expectation 4: the share of the active return's variance the six factors explain, for every path
ATTRIBUTION_FACTOR_PART_MAX = 0.5                # expectation 5a: the share of the mandate's cost against the tilt alone that comes through the factor contributions, every variant
ATTRIBUTION_ARITHMETIC_TOL = 0.0002              # expectation 5b: the exclusions' factor part (the five factors other than the market) within this of the arithmetic of the inputs, per year (2 basis points), every variant

# Specification count, written down before the code runs and reported.
EXT_SPEC_COUNT = (len(COV_ESTIMATORS) + 3) * len(CONSTRAINT_SETS)   # 28 optimised specifications: four daily-based estimators, the monthly sample covariance, the robust portfolio and RiskMetrics, times four constraint sets
EXT_COST_LEVELS = (DGU_TCOST, TCOST_SENSITIVITY)              # each reported net of cost at both levels; the cost is applied after the fact and does not enter the optimisation

# ---------------------------------------------------------------------------
# 6. Output conventions
# ---------------------------------------------------------------------------

OUTPUT_DIR = "outputs"
PROVENANCE_FILE = "outputs/provenance_french.json"   # download date, URL, SHA-256 and CRSP vintage line per file
TIMEZONE = "Europe/Amsterdam"

# ---------------------------------------------------------------------------
# 7. Version 2, module A: the factor objective under the mandate
# ---------------------------------------------------------------------------
# Fixed 8 October 2026, before any of the module's code was written, from the
# design of 7 October 2026 and version 1's results at commit 6835d49. Version 1 found that
# the mandate's tilt leaves incidental exposures of 0.004 to 0.018 in absolute
# value to the six factors, costing 9 to 13 basis points a year. Module A makes
# the exposures the objective: each month, with the data available before the
# month, the optimiser maximises the sum of the active exposures to the four
# targeted factors, s' B' (w - b), where B holds the industries' betas to the
# six factors estimated as in notebook 13 (three years of daily returns before
# the month) and s is FO_TARGET_SIGN, under every constraint of the mandate
# (CONSTRAINT_SETS["C3"]) and one new constraint, the budget: the forecast
# tracking error from the month's covariance estimate at most FO_BUDGETS_ANNUAL.
# The study holds no view on expected returns, as version 1 did not: the
# targets are the four of French's six factors with a documented premium, the
# direction of each is the literature's, and the four are weighted equally in
# beta units. Nothing estimates a premium or times a factor.
# Naming, fixed in the design: "tilt" stays the industry reduction of version 1;
# the new objective is the factor objective, the four are the targeted factors,
# the limit is the budget.
FO_DECISION_DATE = "2026-10-08"
FO_TARGET_FACTORS = ("HML", "RMW", "CMA", "Mom")              # value, profitability, investment, momentum
FO_TARGET_SIGN = {"Mkt-RF": 0.0, "SMB": 0.0, "HML": 1.0, "RMW": 1.0, "CMA": 1.0, "Mom": 1.0}   # s, on ATTRIBUTION_FACTORS; +1 is the direction of the documented premium
FO_CONSTRAINT_SET = "C3"                                       # the mandate: every constraint of version 1's C3, unchanged
FO_BUDGETS_ANNUAL = (0.0075, 0.0100, 0.0150)                   # tau, per year: just above the mandate's own realised cost (84.7 to 95.8 bp), the enhanced-indexing limit of OPT_TILT_TE_MAX_ANNUAL, and the generous case
FO_BUDGET_MAIN = 0.0100                                        # the budget at which the robust, RiskMetrics and single-factor paths run and most expectations are tested
FO_BETA_WINDOW_YEARS = EXT_COV_DAILY_WINDOW_YEARS              # the betas' window: notebook 13's three years of daily returns before the month
# Infeasibility rule: in a month in which the budget cannot be met under the
# mandate (the tracking-error-minimising solution of version 1 already exceeds
# tau), the path takes that minimising solution, the month is counted and
# reported, and nothing else is relaxed; the count is one of the results.
FO_INFEASIBLE_RULE = "tracking-error minimiser"
# The 19 paths, the count fixed here: the five estimator variants of version 1
# at each of the three budgets (15); the robust and RiskMetrics variants at the
# main budget (2); two single-factor sensitivities at the main budget with the
# daily sample estimator, s on value alone and on momentum alone (2). Version
# 1's mandate paths (tracking error minimised, no objective) are the comparison
# and are not rerun. A path added after the first run is disclosed with its
# date and reason, and the count restated.
FO_SINGLE_FACTOR_PATHS = (("HML",), ("Mom",))
FO_PATH_COUNT = 19
# The two measures new to module A. The exposure the budget bought: the mean
# over the months of the sum of the four targeted active exposures, divided by
# the realised tracking error in basis points a year. The gap: for each month,
# the targeted exposure the optimiser chose ex ante, s' B_t' a_t with B_t the
# betas estimated before the month, minus the exposure the same weights carry
# when the betas are estimated after the month, s' B_{t+1}' a_t; its mean
# absolute value over the months is the path's gap.
FO_GAP_DEFINITION = "s'(B_t - B_{t+1})' a_t, mean absolute value over the months"
# The seven expectations, each a strict pass or fail; the levels from
# version 1's results at 6835d49, with the design's reasons.
# E1. At the main budget the budget binds (forecast tracking error within
# FO_E1_BIND_TOL of the budget) in at least FO_E1_BIND_SHARE_MIN of the 566
# months for each of the four daily estimators; the months where it cannot
# be met are counted. Reason: version 1's forecast under the mandate was 55
# to 68 bp on average and 47 to 55 for the tilt alone at the 1979 oil peak for
# the daily estimators, so a budget of 100 should be reachable almost always;
# the monthly estimator (108 at that peak) may fail it in the first years.
FO_E1_BIND_TOL_ANNUAL = 0.0001           # one basis point a year
FO_E1_BIND_SHARE_MIN = 0.95
# E2. At the main budget the mean active exposure to each targeted factor is
# positive on every main path, the average of the four is at least
# FO_E2_MEAN_EXPOSURE_MIN for the daily sample estimator, and that average
# rises with the budget (75, then 100, then 150) on every estimator. Reason:
# version 1's incidental exposures were 0.004 to 0.018 in absolute value with
# no objective; 49 industries within 2 percentage points of their weights can
# reach three to ten times that when the objective asks for it.
FO_E2_MEAN_EXPOSURE_MIN = 0.05
# E3. Realised tracking error exceeds the budget by 20 to 60 per cent on the
# daily estimators, and by more on the monthly sample covariance; tested at
# every budget (the design names none), the monthly ratio against the largest
# daily ratio at the same budget. Reason: version 1's bias was 1.22 to 1.39 on
# daily data and 1.61 on monthly; a budget-binding solution concentrates risk
# where the estimator sees least, so the miss may exceed version 1's, bounded
# here at 1.6.
FO_E3_REALISED_OVER_BUDGET_RANGE = (1.2, 1.6)
# E4. The four targeted factors' contributions sum to a positive amount on
# every main path, and at the main budget and above the six factors explain at
# least FO_E4_FACTOR_SHARE_MIN of the active return's variance on every main
# path. Reason: version 1's factors explained 14 to 28 per cent of incidental
# exposures; deliberate exposures raise the share.
FO_E4_FACTOR_SHARE_MIN = 0.30
# E5. At the main budget the gross active return is positive for at least
# FO_E5_POSITIVE_MIN of the five estimators; the net return at DGU_TCOST per
# unit of turnover lies within FO_E5_NET_GAP_MAX of the gross. Whether the
# active return is more than two standard errors from zero is reported, not
# expected. Reason: the study holds no view on the premia; the sign follows
# from the targets if the premia had their documented sign over the sample,
# which is what the data say and not a claim of skill.
FO_E5_POSITIVE_MIN = 4
FO_E5_NET_GAP_MAX = 0.0010               # 10 basis points a year
# E6. Of the two single-factor paths, momentum alone has the higher turnover
# and the larger gap, and the turnover cap binds in more months on the
# momentum path than on the value path. Reason: industry momentum betas rotate
# within a year; value betas do not.
# E7. At the main budget the spread across the four daily estimators in
# realised tracking error is at most FO_E7_TE_RANGE_MAX, the exposure bought
# per basis point differs across them by less than FO_E7_EXPOSURE_PER_BP_REL_MAX
# of their mean (largest minus smallest over the mean), and the monthly sample
# covariance remains the worst calibrated (the largest realised over forecast
# of the five). Reason: version 1, a range of 9 basis points on a level of
# about 90, the monthly covariance 61 per cent under-forecast.
FO_E7_TE_RANGE_MAX = 0.0020              # 20 basis points a year
FO_E7_EXPOSURE_PER_BP_REL_MAX = 0.30
# Notebook 14 runs the objective at the report months of version 1 and over
# the sample without a rolling path: a worked month, the exposure against the
# budget at FO_CURVE_BUDGETS (the three budgets and points between), and the
# feasibility of each budget in every month, from the forecast tracking error
# of the tracking-error-minimising solution under the mandate.
FO_CURVE_BUDGETS_ANNUAL = (0.0050, 0.0075, 0.0100, 0.0125, 0.0150, 0.0200)
FO_TOL_TE = 1e-9                         # a forecast tracking error within this of the budget counts as on it, in the tests
