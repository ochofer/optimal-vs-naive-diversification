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

# The constrained rules' solver, set on 17 November 2026: each
# constrained rule is a quadratic programme whose budget 1'w = 1 is an equality
# of the problem and whose lower bound is a bound on each weight, solved
# exactly by the active-set method of
# rules._budget_qp, so that no constraint is approximated by a weight and no
# result depends on a setting of a library or of the module. The replication
# tables of notebook 03 are the tables written under this decision and committed
# with it; the extended-sample tables of notebook 07 stay as committed
# (results/202608/README.md records why). The suite checks the optimality
# conditions at the scale of the study's data (tests/test_rules_backtest.py).
DGU_CONSTRAINED_SOLVER_DATE = "2026-11-17"

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
# The end of the sample, fixed on 6 November 2026. Until then the end was the
# latest month the vintage carried, and every recorded run (7 to 18 October
# 2026) used the 202608 vintage, whose last month is 2026-08, the end the design
# names ("1979-07 to 2026-08"). French's library moved to the 202609 vintage
# before 6 November, which carries 2026-09 and so gave 567 evaluation months
# and stopped every notebook at its count. From now on the loader cuts every
# file at this month, whatever the vintage, so that each notebook sees the same
# months on any later vintage; the vintage line and the SHA-256 in the
# provenance record say which revision of French's history a run used, and a
# later vintage need not reproduce every digit of the committed tables, since
# French revises history. A run on the cached 202608 files is unchanged by the
# cut. Not an expectation: a data rule, disclosed here and in the README.
EXT_SAMPLE_END = "2026-08"
# The rule, written here on 8 November 2026 after the decision of 6 November, and carried in the README's run section in
# the same words: the sample is July 1979 to August 2026, fixed in the code.
# The recorded tables are those of the 202608 vintage as cached. A run on a
# later vintage, cut at August 2026, is a confirmation run: it is labelled by
# its vintage in the provenance record, it is expected to reproduce every
# verdict line and every printed decimal and not every digit, because French
# revises history, and it replaces no committed table without a dated decision.
EXT_SAMPLE_END_RULE_DATE = "2026-11-08"
EXT_CONFIRMATION_RUN = "a run on a later vintage, cut at August 2026, labelled by its vintage in the provenance record"

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
EXT_COV_EWMA_HALFLIFE_DAYS = 252                   # the recency-weighted sensitivity: a half-life of 252 trading days, close to the decay of 0.99734 in Dom, Howard, Jansen and Lohre (2025, section 3.3.2), about 260 days; 126 until 3 October 2026, changed on reading that paper, before notebook 10's code

# Covariance estimators. The shrinkage target follows Dom, Howard, Jansen and
# Lohre, the paper the study takes as its reference: their linear shrinkage
# pulls the sample covariance towards a scaled identity matrix (Ledoit and
# Wolf 2004b), and the constant-correlation target gave inferior results.
# Checked on 3 October 2026, before notebook 10's code, in the
# working paper of January 2024 (SSRN 4684926, its footnote 11), the version
# the study was written against, which estimates from three years of daily
# returns, having tried one, three and five (its section 4.1.1). Set on
# 18 November 2026: the citation moved to the published version
# (2025; the section, table and footnote numbers are the accepted manuscript's
# of January 2025), whose footnote 10 reports the same result, which estimates
# from five years (its section 4.1), rebalances monthly and finds that under long-only
# and weight constraints the differences between estimators shrink (its
# Table 3), which notebook 10's expectation 3 tested for this study's
# estimators. EXT_COV_DAILY_WINDOW_YEARS stays at three, the study's own
# setting; five years is reported as a sensitivity.
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
# joins as a seventh variant because Dom, Howard, Jansen and Lohre (2025) find
# that time dynamics matter more than shrinkage or factor structure in long-only
# and weight-constrained portfolios (the scope added on
# 18 November 2026); the calibration multiplies each forecast by the ratio of
# realised to forecast tracking error over the previous EVAL_CALIBRATION_WINDOW
# months of the same path, using only months before the forecast.
EWMA_VARIANT = ("sample", "daily_5y_ewma")   # the seventh variant: RiskMetrics, as in notebook 10's sensitivity; five years of daily returns, notebook 10's choice of 3 October 2026, which is the window of the published paper (2025, section 4.1)
EVAL_CALIBRATION_WINDOW = 60                 # months of a path's own past the calibration uses; a standard deviation from 60 observations has a standard error of about 9%
EVAL_CALIBRATION_MIN = 24                    # the forecast is left as it is while fewer months are available
EVAL_CALIBRATED_BIAS_RANGE = (0.85, 1.15)    # expectation 9: the calibrated bias statistic under C3, four daily estimators
# Additions of 18 October 2026 to notebook 12, planned on 9 October 2026,
# fixed here before their code, after the recorded run of 7 October (commit
# 6835d49) and labelled in the notebook. (a) Two saves, so that the dashboard
# can draw the forecasts and the holdings from committed tables: the monthly
# forecast tracking error of every path, beside the active returns the
# notebook already writes, and the weights every path holds in the last
# evaluation month, with the benchmark's. (b) Two descriptive figures per path,
# reported beside the standard-error sentence and entering no claim: the worst
# cumulative fall of the active return (the largest fall of the cumulative
# active return from an earlier high, with its peak and trough months) and the
# share of months with a positive active return. (c) A 95 per cent band on the
# bias statistic from a circular block bootstrap of the monthly pairs (active
# return, forecast) in blocks of EVAL_BOOTSTRAP_BLOCK_MONTHS, with
# EVAL_BOOTSTRAP_DRAWS resamples from the seed below; a block keeps the months'
# order, so the band allows for the clustering of the active returns, and the
# circle lets a block run past the last month into the first. No normal band is
# drawn. The one expectation attached, expectation 10: after the re-run every
# table the notebook wrote on 7 October (EVAL_RERUN_IDENTICAL, the measures,
# the by-decade table, the calibration table and the active returns) comes
# out byte for byte equal to the committed copy in results/<vintage>/, so that
# the additions change no number of version 1.
EVAL_ADDITIONS_DATE = "2026-10-18"
EVAL_BOOTSTRAP_BLOCK_MONTHS = 12
EVAL_BOOTSTRAP_DRAWS = 2000
EVAL_BOOTSTRAP_SEED = 20261009               # the date of the decision, as a number
EVAL_BOOTSTRAP_LEVEL = 0.95
EVAL_RERUN_IDENTICAL = ("rolling_evaluation", "rolling_evaluation_by_decade", "rolling_evaluation_calibration", "active_returns")   # expectation 10

# Additions of 6 November 2026 to notebook 12, after the runs of 7 and 18
# October. (a) The rolling realised tracking error of every path: the standard
# deviation (n minus 1, as in realised_tracking_error) of the monthly active
# return over the EVAL_ROLLING_TE_MONTHS months ending in and including each
# month, times the square root of 12, from the first month with a full window;
# and the median across the seven variants under C3 and under the tilt alone.
# A reported measure in no claim, with no expectation attached; the window is
# three years, the length of the daily covariance windows. Written as a table
# so that a figure drawn from the series is traced to a committed table like
# every other figure. (b) The rule for every rerun from now on, set on
# 6 November 2026 beside expectation 10 and not part of its verdict,
# which stays as written: a table from the quadratic programs reproduces the
# committed copy to the last digit; a table from the cone program (the robust
# variant, ROBUST_VARIANT) reproduces it to EVAL_RERUN_CONE_MAX_DIFFERENCE per cell;
# the solver's name and version are written to the run's provenance record
# (provenance_solver.json); the count of months with an inaccurate solver
# status is reported beside the comparison and is not part of it.
EVAL_ROLLING_ADDITIONS_DATE = "2026-11-06"
EVAL_ROLLING_TE_MONTHS = 36
EVAL_RERUN_CONE_MAX_DIFFERENCE = 1e-8        # the monthly records of the cone program (active_returns)
# The measures' own number, set on 7 November 2026 after the run
# of 6 November showed the robust variant's by-decade and calibration rows up
# to 3e-8 and 2e-8 from their committed copies while its monthly active returns
# were within 3.2e-9: a measure computed over the 566 months from those
# records, a standard deviation or a ratio, moves by a multiple of what its
# inputs move by, so a table of measures from the cone program (the three
# measure tables of version 1 and the rolling tracking-error table) reproduces
# its committed copy to EVAL_RERUN_CONE_MEASURES_MAX_DIFFERENCE per cell. The
# records' number above stays as written; the verdict of expectation 10 is
# unchanged.
EVAL_RERUN_CONE_MEASURES_MAX_DIFFERENCE = 1e-7
EVAL_RERUN_MEASURE_TABLES = ("rolling_evaluation", "rolling_evaluation_by_decade", "rolling_evaluation_calibration", "rolling_tracking_error", "rolling_evaluation_bias_by_decade")   # the last added 8 November 2026

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
# version 1's results at 6835d49, with their reasons.
# E1 and E2 were restated on 9 October 2026, after notebook 14's check of
# the arithmetic and before any path ran, on 9 October 2026:
# a level changed at that point, between the pre-run check notebook 14
# exists for and the first rolling run, is a pre-run restatement, dated and
# disclosed here and once in the write-up; a level changed after notebook 15
# runs is a post-run change. The original levels of 8 October stay below,
# marked as superseded.
FO_RESTATEMENT_DATE = "2026-10-09"
# E1. At the main budget the budget binds (forecast tracking error within
# FO_E1_BIND_TOL of the budget) in at least FO_E1_BIND_SHARE_MIN of the
# months in which the mandate's own minimum forecast tracking error, with
# turnover free, is at or below the budget, for each of the four daily
# estimators. The months the mandate alone cannot meet are reported per
# estimator and budget from notebook 14's feasibility table; the months the
# path misses beyond them, with the turnover cap in force, are counted and
# reported, since that difference is what the path adds. Reason for the
# restatement: notebook 14 found the mandate alone above 100 bp in 37
# (sample), 43 (Ledoit-Wolf) and 39 (six-factor) of the 566 months, 22 for
# principal components, nearly all in 1979 to 1989, so the budget cannot
# bind in those months whatever the objective.
FO_E1_BIND_TOL_ANNUAL = 0.0001           # one basis point a year
FO_E1_BIND_SHARE_MIN = 0.95
FO_E1_DENOMINATOR = "months the mandate alone can meet"
# Superseded on 9 October 2026: the same share of all 566 months. Reason
# given on 8 October: version 1's forecast under the mandate was 55 to 68 bp
# on average and 47 to 55 for the tilt alone at the 1979 oil peak for the
# daily estimators, so a budget of 100 should be reachable almost always;
# the monthly estimator (108 at that peak) may fail it in the first years.
FO_E1_DENOMINATOR_SUPERSEDED_2026_10_08 = "all 566 months"
# E2. At the main budget the mean active exposure to each targeted factor is
# positive on every main path, the average of the four is at least
# FO_E2_MEAN_EXPOSURE_MIN for the daily sample estimator, and that average
# rises with the budget (75, then 100, then 150) on every estimator; the four
# exposures are reported per path at every budget, the average never alone.
# Reason for the restatement: notebook 14's stationary mean of the four at
# 100 bp is 0.030 for the daily sample estimator and a capped path holds at
# most the stationary exposure on average; the level is four fifths of
# 0.030, the fifth being the design's allowance for what the turnover cap,
# the infeasible months and the rolling betas may cost against the
# stationary solution, a judgement stated as such. Under an active weight
# bound of 2 percentage points on 49 industries, 100 bp of budget buys about
# 0.03 of average exposure in beta units.
FO_E2_MEAN_EXPOSURE_MIN = 0.024
# Superseded on 9 October 2026. Reason given on 8 October: version 1's
# incidental exposures were 0.004 to 0.018 in absolute value with no
# objective; 49 industries within 2 percentage points of their weights can
# reach three to ten times that when the objective asks for it.
FO_E2_MEAN_EXPOSURE_MIN_SUPERSEDED_2026_10_08 = 0.05
# One diagnostic per path, counted and reported with no expectation
# attached (the design of 9 October 2026): the months in which any targeted
# exposure ends below its incidental value, the value the mandate's
# tracking-error minimiser carries. Notebook 14 found such a month in 5 of
# its 15 month-estimator pairs at 100 bp.
FO_DIAGNOSTIC_BELOW_INCIDENTAL = "months with a targeted exposure below its incidental value"
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
# Solver rule for the factor problem, added 18 October 2026 while notebook 15 was
# being built, before its first recorded run: the first path at 150 basis points
# stopped at 1981-02, a month in which the budget cone and the turnover cap are
# both active and the interior-point method stalls at a primal residual of 1e-7
# (status AlmostSolved at the 1e-9 rule, and a failure outright on the second pass
# at the default rule). The factor problem therefore gets a third pass at this
# looser rule when the solver fails at the first two; a portfolio from any pass is
# accepted only after the same checks as every other (the bounds, the cap, the
# budget within 1e-6 relative), and the month keeps the solver's status word, so
# that the notebook counts it among the inaccurate months. A second case met the
# same day, at 2009-06 for the principal-components estimator at 100 basis
# points: the minimiser's forecast exceeds the budget by a hundredth of a basis
# point, the factor problem has no interior, and the solver reports a numerical
# error at every rule; the month then follows the infeasibility rule above, as
# any month whose minimiser exceeds the budget does, and the guard that the
# minimiser must indeed exceed the budget stays, so that a solver failure on a
# feasible month still stops the run.
FO_SOLVER_OPTIONS_LOOSE = {"tol_gap_abs": 1e-7, "tol_gap_rel": 1e-7, "tol_feas": 1e-7}
# Notebook 15 (built 18 October 2026, after notebook 14 and the restatement of
# 9 October, before any path ran) runs the 19 paths month by month as notebook
# 12 runs version 1's, with the betas of the month before each portfolio, and
# judges E1, E2, E3, E5, E6 and E7 on their records; E4 needs the attribution
# of notebook 16 and is judged there. The gap of FO_GAP_DEFINITION is recorded
# in notebook 15, where the next month's betas are at hand, and drawn in
# notebook 16. The incidental value of the diagnostic is the exposure the
# mandate's tracking-error-minimising path of the same variant carries in the
# same month, rebuilt from the modules as notebook 13 rebuilds it and checked
# against ATTRIBUTION_REFERENCE_TE; the months the mandate alone can meet, E1's
# denominator, are those in which its stationary minimum forecast tracking
# error (the mandate with turnover free, as notebook 14 computes it) is at or
# below the budget.
FO_NOTEBOOK_15_JUDGES = ("E1", "E2", "E3", "E5", "E6", "E7")
FO_NOTEBOOK_16_JUDGES = ("E4",)
# Notebook 16, the attribution of the nineteen paths, built 8 November 2026,
# after the recorded run of notebook 15 and its reading on 6
# November, before any attribution ran. It rebuilds the nineteen paths from the
# modules, as notebook 13 rebuilds version 1's, checks each path's realised
# tracking error against notebook 15's below within ATTRIBUTION_REPRODUCTION_TOL
# and, where the repository is present, the records against the committed
# monthly table under the rule for reruns; it attributes each path's active
# return exactly as notebook 13 does and judges E4. Two measures it reports,
# in no claim: the exposure bought per factor, the mean active exposure to
# each targeted factor divided by the realised tracking error in basis points
# a year, the per-factor form of notebook 15's exposure per basis point; and
# the gap per unit of exposure bought, the path's mean absolute gap divided by
# its mean factor objective, which the design of 6 November 2026 allows as a
# reported measure with no expectation attached.
FO_ATTRIBUTION_DATE = "2026-11-08"
FO_ATTRIBUTION_REFERENCE_TE = {                  # notebook 15's realised tracking errors, per year, for the reproduction check
    "sample, daily 3y | 75": 0.01002117, "sample, daily 3y | 100": 0.01205713, "sample, daily 3y | 150": 0.01731365,
    "ledoit_wolf, daily 3y | 75": 0.00985564, "ledoit_wolf, daily 3y | 100": 0.01185552, "ledoit_wolf, daily 3y | 150": 0.01713197,
    "factor, daily 3y | 75": 0.01102305, "factor, daily 3y | 100": 0.01335962, "factor, daily 3y | 150": 0.01876902,
    "pca, daily 3y | 75": 0.01126859, "pca, daily 3y | 100": 0.01369633, "pca, daily 3y | 150": 0.01849629,
    "sample, monthly 120 | 75": 0.01279599, "sample, monthly 120 | 100": 0.01501193, "sample, monthly 120 | 150": 0.01917291,
    "robust, all five | 100": 0.01156417, "RiskMetrics, daily 5y | 100": 0.01186274,
    "sample, daily 3y, value alone | 100": 0.01227800, "sample, daily 3y, momentum alone | 100": 0.01230211,
}
FO_EXPOSURE_BOUGHT_PER_FACTOR = "mean active exposure to the factor over the realised tracking error in basis points a year"
FO_GAP_PER_UNIT = "mean absolute gap over the mean factor objective"
# Notebook 12, added 8 November 2026 in no claim, for the dashboard's figure of
# the forecasts' miss by decade in one measure for both of its states: the bias
# statistic by decade under the 21 rule and after calibration, for every path under C3 and the tilt alone,
# written as a table beside the calibration table, which stays as committed.
EVAL_BIAS_BY_DECADE_DATE = "2026-11-08"

# ---------------------------------------------------------------------------
# 8. Paired tests of two realised volatilities, added 18 November 2026
# ---------------------------------------------------------------------------
# Set on 18 November 2026, after every recorded run of version 1
# and of module A, and labelled so wherever it is used. The reason: notebook 12
# judged RiskMetrics against the sample covariance under the mandate (84.3
# against 84.7 basis points a year) by the standard error of one tracking
# error, about 2.5 basis points, while the two paths share their 566 months
# and their active returns correlate at 0.99, so the difference between them
# is far less noisy than either figure. The test is the one Dom, Howard,
# Jansen and Lohre (2025) apply to their portfolios' realised volatilities,
# the variance test of Ledoit and Wolf (2011), built in paired.py: the delta
# method on the four means (each series and its square), the standard error
# from the prewhitened Parzen kernel, and the studentised circular block
# bootstrap with EVAL_BOOTSTRAP_BLOCK_MONTHS, EVAL_BOOTSTRAP_DRAWS,
# EVAL_BOOTSTRAP_SEED and EVAL_BOOTSTRAP_LEVEL as they are. Two statistics
# from the same resamples: the difference of the log variances, for the
# p-value in the paper's form, and the difference of the two annualised
# standard deviations in the tables' n minus 1 convention, for an interval at
# EVAL_BOOTSTRAP_LEVEL in basis points. The comparisons below were fixed here
# before paired.py produced any figure on the study's data, and every one is
# reported with no verdict: the two figures, their difference, the correlation
# of the two monthly series, the p-value and the interval. A and B are
# computed from the committed active returns (active_returns_<vintage>.csv)
# with no path rerun, so every version 1 table stays byte for byte; C rebuilds
# the four minimum-variance portfolios of notebook 10 from the modules and
# checks their realised volatilities against the committed table before the
# test runs. The one expectation attached is the size check, P1, run before
# the test touches the study's data: PAIRED_SIZE_PAIRS simulated pairs of
# PAIRED_SIZE_MONTHS months with equal variances and a correlation of
# PAIRED_SIZE_CORRELATION, Student-t shocks with PAIRED_SIZE_T_DOF degrees of
# freedom, no difference in means; the share rejected at 5 per cent lies in
# PAIRED_SIZE_RANGE.
PAIRED_TEST_DATE = "2026-11-18"
PAIRED_REFERENCE = ("sample", "daily 3y")        # the variant the comparisons of A are made against, under C3
PAIRED_COMPARISONS_A = (                          # A: each against the reference under the mandate (C3); Holm's correction across the six, as the paper applies it
    ("RiskMetrics", "daily 5y"), ("ledoit_wolf", "daily 3y"), ("pca", "daily 3y"), ("factor", "daily 3y"),
    ("sample", "monthly 120"), ("robust", "all five"),
)
PAIRED_COMPARISON_B_SETS = ("C3", "C3 tilt only")   # B: the mandate against the tilt alone, for each of the seven variants, no correction
PAIRED_COMPARISONS_B = (
    ("sample", "daily 3y"), ("ledoit_wolf", "daily 3y"), ("factor", "daily 3y"), ("pca", "daily 3y"),
    ("sample", "monthly 120"), ("robust", "all five"), ("RiskMetrics", "daily 5y"),
)
PAIRED_COMPARISONS_C = (                          # C: notebook 10's minimum-variance portfolios, RiskMetrics against the sample covariance, no correction
    (("sample", "daily_5y_ewma"), ("sample", "daily_5y"), "unconstrained"), (("sample", "daily_5y_ewma"), ("sample", "daily_5y"), "long-only"),
    (("sample", "daily_5y_ewma"), ("sample", "daily_3y"), "unconstrained"), (("sample", "daily_5y_ewma"), ("sample", "daily_3y"), "long-only"),
)
PAIRED_C_REPRODUCTION_TOL = 0.001                 # C: the rebuilt portfolios' realised volatilities within this of the committed table, in percentage points a year
PAIRED_PERIODS = 12                               # months a year, the annualisation
PAIRED_SIZE_PAIRS = 1000
PAIRED_SIZE_MONTHS = 566                          # the months of the rolling evaluation, 1979-07 to 2026-08
PAIRED_SIZE_SD = 0.0025                           # the monthly standard deviation of the simulated pairs, about 85 basis points a year
PAIRED_SIZE_CORRELATION = 0.99
PAIRED_SIZE_T_DOF = 5
PAIRED_SIZE_SEED = 20261118                       # the date of the plan, as a number
PAIRED_SIZE_RANGE = (0.035, 0.065)                # P1: the share of simulated pairs rejected at 5 per cent
# Added on 18 November 2026, after the first run of notebook 17 and
# before its recorded run, in no verdict: a row whose interval includes zero
# says what the comparison could have seen only beside the difference at which
# the interval would exclude zero about four times in five, (the critical
# value plus the standard normal quantile at this power) times the standard
# error, reported in the table's units and as a share of the row's reference
# figure, the second of the two series.
PAIRED_DETECTABLE_POWER = 0.80
# The paper's gain of RiskMetrics over the sample covariance for the
# weight-capped minimum-variance portfolio, per cent volatility a year, in
# the two versions of the paper (the figures the text of expectation 8 is
# measured against): RiskMetrics first, the sample covariance second.
PAIRED_PAPER_GAIN_WITH_CAP = {
    "published version, Table 3 Panel B, with the cap": (13.00, 13.36),
    "working paper of January 2024, Table 2 Panel B, with the cap": (13.4, 13.6),
}
# Added on 18 November 2026 after every recorded run, in no verdict and with
# no correction, and labelled so wherever the rows appear: E, the three pairs among the four daily estimators under the mandate
# that A does not test, so that the sentence on two groups among them (the
# sample covariance and shrinkage; the factor model and the principal-component
# model) rests on tested differences. First series minus second, in basis
# points a year, from the committed active returns with no path rerun.
PAIRED_E_DATE = "2026-11-18"
PAIRED_COMPARISONS_E = (
    (("factor", "daily 3y"), ("ledoit_wolf", "daily 3y")),
    (("pca", "daily 3y"), ("ledoit_wolf", "daily 3y")),
    (("factor", "daily 3y"), ("pca", "daily 3y")),
)
# Notebook 03, added the same day after every recorded run: the
# comparison of every rule with 1/N on the paper's period written as a table,
# with the two-sided p-value the study uses beside the one-sided value the
# paper prints (half of the two-sided value under the normal distribution of
# the Jobson-Korkie statistic), so that each figure resolves to a committed
# file. The study's convention stays two-sided.
REPLICATION_VS_1N_DATE = "2026-11-18"
# Added on 19 November 2026 after the study's results were known, with no
# verdict, and labelled so wherever the figures appear: none is an expectation,
# and the text says of each that it was added after the results were known.
# The additions below go into notebook 17, each computed from the committed
# records with no path rerun and with EVAL_BOOTSTRAP_DRAWS, EVAL_BOOTSTRAP_SEED
# and EVAL_BOOTSTRAP_LEVEL as they are, so that every earlier table stays byte
# for byte.
# (1) The block length. The study fixes the bootstrap's block at
# EVAL_BOOTSTRAP_BLOCK_MONTHS, the bias band's, where Ledoit and Wolf (2008,
# Algorithm 3.1) calibrate it from the data. The rows of the families in
# PAIRED_BLOCK_FAMILIES_FURTHER are reported again at each length in
# PAIRED_BLOCK_LENGTHS_FURTHER, same seed and draws, in a table of their own,
# so that a reader sees what the choice does.
PAIRED_ADDITIONS_DATE = "2026-11-19"
PAIRED_BLOCK_LENGTHS_FURTHER = (3, 6, 24)         # months, beside the committed rows at EVAL_BOOTSTRAP_BLOCK_MONTHS
PAIRED_BLOCK_FAMILIES_FURTHER = ("A", "B", "E")
# (2) Holm's correction, by the function that gives A its column: across the
# seven rows of B, as a column of the paired table, and across the nine rows
# of the families in PAIRED_HOLM_JOINT_FAMILIES together, as one sentence.
PAIRED_HOLM_FAMILIES_FURTHER = ("B",)
PAIRED_HOLM_JOINT_FAMILIES = ("A", "E")
# (3) The size check again, with no verdict and P1's verdict as recorded on
# its seed: on each seed in PAIRED_SIZE_FURTHER_SEEDS at PAIRED_SIZE_CORRELATION,
# and on PAIRED_SIZE_SEED at each correlation in PAIRED_SIZE_FURTHER_CORRELATIONS,
# two correlations of rows the text reads (the factor model, the component
# model and the robust portfolio correlate with the sample covariance's path
# at 0.93, the monthly covariance's at 0.81), PAIRED_SIZE_PAIRS pairs each with
# the other settings of P1; every rate with the standard error of a share, the
# square root of rate times (1 minus rate) over the pairs.
PAIRED_SIZE_FURTHER_SEEDS = (20261119, 20261120, 20261121)   # the date of the addition as a number, and the two integers after it
PAIRED_SIZE_FURTHER_CORRELATIONS = (0.93, 0.81)
# (4) The years before 2000 and from 2000. The bias statistic under the 21
# rule (evaluation.bias_statistic) for each variant under EVAL_BIAS_SPLIT_SET,
# from the committed active returns and forecast tracking errors, on the months
# before EVAL_BIAS_SPLIT_MONTH and on the months from it, each with the band of
# evaluation.block_bootstrap_band (blocks of EVAL_BOOTSTRAP_BLOCK_MONTHS, the
# draws, seed and level above, the two periods resampled independently), and
# the band of the difference, before less from, from the same resampled
# statistics paired draw by draw. The sentence that the daily estimators'
# understatement comes from the years before 2000 rests on this table.
EVAL_BIAS_SPLIT_MONTH = "2000-01"                 # the first month of the second period
EVAL_BIAS_SPLIT_SET = "C3"

# ---------------------------------------------------------------------------
# 9. The daily measurement of tracking error, added 18 November 2026
# ---------------------------------------------------------------------------
# Set on 18 November 2026, after every recorded run and after the monthly paired test of
# section 8, and labelled so wherever it is used. The reason: on 566 months the
# comparison of RiskMetrics with the sample covariance under the mandate cannot
# tell no gain from a gain of the size the paper reports (difference -0.38
# basis points, interval -2.30 to +1.55, detectable difference about 2.7),
# while the paper measures volatility on daily portfolio returns; French's
# daily files of the 49 industries cover the whole evaluation, about 11,900
# trading days. The expectations and the readings of this section were written
# on 18 November 2026, before any daily figure of the study was computed, and
# the daily test of (c) runs only after (a) and (b) are committed and pushed.
# The repository's history cannot show that. It will show that (a) and (b) were
# committed before the commit that carries (c)'s results. Two things were seen
# before that commit: the fifteenth path's monthly tracking error, in the reconciliation
# table of (b), and the daily tracking errors of the fourteen paths, printed on
# 19 November 2026 during the check of gate D1; no constant, expectation or
# reading was changed after either. ED3 is an expectation about the sign of two
# daily differences whose point estimates follow from the figures printed that
# day. Every row of the daily comparisons is reported with no verdict. No
# version 1 or module A table changes.
# The order: (a) these constants, the code (paired.py's chunked bootstrap,
# daily.py), the tests and P3 on made-up data; (b) the gates D0 and D1 with
# their tables; (c) the daily test, its table and the text. Family D, below,
# joined the block on 18 November 2026 at 21:45, after every recorded run,
# because comparison A sets RiskMetrics against a window whose weights lie on
# nearly the same data.
DAILY_TEST_DATE = "2026-11-18"
DAILY_PERIODS = 252                               # trading days a year, the annualisation of a daily series, a constant
DAILY_BLOCK = 252                                 # the bootstrap's block in trading days: one year at both frequencies, so the count of blocks is the same, 47
DAILY_CHUNK_DRAWS = 200                           # the bootstrap's draws computed this many at a time, so that 2,000 draws of about 11,900 days fit in memory; the indices are drawn once, and at this chunk every result equals the unchunked one in the recorded environment; the monthly test is not chunked (tests/test_paired.py)
DAILY_FIRST_MONTH = COV_EVAL_START                # the first trading day of July 1979 is the first day of the daily series; the last is the last trading day of EXT_SAMPLE_END
DAILY_PATH_SETS = ATTRIBUTION_SETS                # the fourteen paths: the seven variants under the mandate's C3 and under the tilt alone, rebuilt from the modules with their weights kept, as notebook 13 rebuilds them
DAILY_C_VARIANTS = (("sample", "daily_5y_ewma"), ("sample", "daily_5y"), ("sample", "daily_3y"))   # notebook 10's minimum-variance portfolios, unconstrained and long-only, six series of the portfolio's own daily return
DAILY_C_SIDES = ("unconstrained", "long-only")
# Gate D0: the rebuilt paths reproduce the committed monthly records (active_returns) under the rule for
# reruns, the quadratic programs to the last digit and the robust path within EVAL_RERUN_CONE_MAX_DIFFERENCE;
# the rebuilt minimum-variance portfolios' realised volatilities within PAIRED_C_REPRODUCTION_TOL of the
# committed table. Gate D1: for each of the fourteen paths, the month's active return compounded from the
# daily series (the portfolio's compounded return less the benchmark's) against the committed monthly active
# return. If either fails, the notebook stops and reports; no daily test runs on a series that does not reconcile.
DAILY_D1_CORRELATION_MIN = 0.995                  # over the 566 months
DAILY_D1_TE_GAP_MAX = 0.0001                      # the realised tracking error from the compounded series within 1 basis point a year of the committed one
# The size check P3, on made-up daily data with clustered volatility; it runs in part (a) of notebook 18, before
# part (b) builds the study's daily series.
# The count of pairs was 500 in the plan of 18 November and was raised to 3,000 on 19 November 2026, before
# the larger run, because one run of 1,000 monthly pairs has a standard error of about 0.65 percentage
# points on the share rejected, so a verdict on one seed can turn on the seed. The run at 500 pairs made
# on 19 November before the raise stays recorded
# with its outcome as it fell and is reported beside the larger one; the first DAILY_SIZE_PAIRS_FIRST pairs of
# the larger run are those pairs (one generator, the pairs drawn in sequence; one bootstrap seed per pair,
# spawned in sequence), and where the two differ P3 is read on the 3,000.
DAILY_SIZE_PAIRS = 3000
DAILY_SIZE_PAIRS_FIRST = 500                      # the count of the first run, whose pairs are the first of the larger run
DAILY_SIZE_PAIRS_RAISED = "2026-11-19"
DAILY_SIZE_DAYS = "evaluation"                    # each pair has as many days as the evaluation, counted from the daily file in the notebook
DAILY_SIZE_SD_ANNUAL = 0.0085                     # an annual standard deviation of 85 basis points; the daily one is this over sqrt(DAILY_PERIODS)
DAILY_SIZE_CORRELATION = 0.99
DAILY_SIZE_T_DOF = 5
DAILY_SIZE_GARCH = (0.02, 0.06, 0.92)             # one GARCH(1,1) variance common to both series: omega + alpha times the squared common shock of the day before + beta times the variance of the day before; it scales the common shock and both own shocks; its unconditional value is 1
DAILY_SIZE_SEED = 20261119
DAILY_SIZE_RATE_MAX = 0.065                       # P3 is met when the test rejects in at most this share of the pairs at 5 per cent; the share is reported whatever it is
DAILY_SIZE_RATE_LOW = 0.035                       # a share under this is stated in the text as a test that rejects less often than its level at P3's setting (a pilot on 400 pairs with 999 draws: 2.8 per cent with blocks of 252 days, 3.7 with 63; the block of one year kept because it is the monthly test's and real clustering lasts longer than the pilot's)
# The daily comparisons, fixed now: A daily, the six variants of PAIRED_COMPARISONS_A against PAIRED_REFERENCE
# under the mandate, Holm across the six; B daily, the mandate against the tilt alone for each of the seven
# variants of PAIRED_COMPARISONS_B, no correction; C daily, the four comparisons of PAIRED_COMPARISONS_C on the
# portfolios' daily returns. Each row carries the two daily figures, their difference, its standard error,
# the critical value, the interval, the correlation of the two daily series, the p-value, for A the Holm
# value, and the detectable difference at PAIRED_DETECTABLE_POWER; beside each row, with no verdict, the
# same two figures on monthly returns and the ratio of the monthly to the daily variance of each series.
# Expectations, fixed before the run:
DAILY_ED1 = "gate D1 holds for all fourteen paths"                       # from the arithmetic of the gate: the gap of French's monthly returns to his daily ones compounded is well under a basis point a month on an active return whose monthly standard deviation is about 25
DAILY_ED2_SE_RATIO_MAX = 0.5                      # ED2: for RiskMetrics against the sample covariance under the mandate, the standard error of the daily difference is at most half the monthly one of 0.91 basis points, that is, at most 0.455; about 21 times the observations would give a factor of 4.6 if days behaved like months, and fat tails and clustering take part of it away
DAILY_ED3_VARIANTS = (("factor", "daily 3y"), ("pca", "daily 3y"))     # ED3: the factor model and principal components realise a higher daily tracking error than the sample covariance, each with an interval above zero and a Holm value below 0.05; both are so on months (+8.79 and +6.83 basis points, Holm 0.003 and 0.025), and a difference of that size should not depend on the horizon
DAILY_ED3_HOLM_MAX = 0.05
# No expectation on the RiskMetrics rows; their readings are fixed instead. With the difference RiskMetrics
# less the sample covariance and its 95 per cent interval, and the paper's gain as its share of the
# reference figure here: the interval wholly below zero reads "a gain from RiskMetrics is found, of the size
# and interval stated, and set beside the paper's"; the interval including zero and excluding a gain of the
# published size reads "no gain is found, and a gain as large as the published one is excluded here"; the
# interval including zero and a gain of the published size reads "daily data do not settle it either, at
# the detectable difference stated"; the interval wholly above zero reads "RiskMetrics realises more than
# the sample covariance here". The mandate's rows (A) are read against the capped portfolio, the
# minimum-variance rows (C) against the unconstrained and the long-only one, and every reading names the
# difference in setting: 49 industries here, about 500 stocks there, a tracking mandate here, a
# minimum-variance portfolio there.
DAILY_READINGS = {
    "below": "a gain from RiskMetrics is found, of the size and interval stated, and set beside the paper's",
    "excludes_gain": "no gain is found, and a gain as large as the published one is excluded here",
    "includes_gain": "daily data do not settle it either, at the detectable difference stated",
    "above": "RiskMetrics realises more than the sample covariance here",
}
# The paper's figures, RiskMetrics against the sample covariance, per cent volatility a year, by portfolio
# and version (the capped pair is PAIRED_PAPER_GAIN_WITH_CAP of section 8):
PAIRED_PAPER_FIGURES = {
    "published version, Table 3 Panel B": {"unconstrained": (11.36, 10.91), "long-only": (11.31, 12.24), "with the cap": (13.00, 13.36)},
    "working paper of January 2024, Table 2 Panel B": {"unconstrained": (14.7, 14.3), "long-only": (12.0, 12.5), "with the cap": (13.4, 13.6)},
}

# Family D, added on 18 November 2026 at 21:45, after every recorded run,
# because the study sets RiskMetrics, an exponentially weighted covariance
# over five years of daily returns with a one-year half-life, against the
# sample covariance on three years, two estimators whose weights lie on nearly
# the same data (90 per cent of RiskMetrics' weight in the last 756 days, by
# the arithmetic of the half-life), while the paper compares the two on one
# window. One new path: the sample covariance on five years of daily returns
# under the mandate, built and run as the seven variants are, over the same
# 566 months, labelled wherever it appears as added on 18 November 2026 after
# every recorded run; its records go into tables of their own, and no version 1 table
# gains a column. Two comparisons, D, on months and on days, with no correction
# and no verdict: RiskMetrics against the sample covariance on five years, which
# differ only in how they weigh the same window (the paper's comparison; the
# four readings of DAILY_READINGS apply to it), and the sample covariance on five
# years against the one on three, what the window alone does. Stated with them
# and computed by code from the weights, for RiskMetrics, the flat three-year
# window and the flat five-year window: the mean age of an observation, the
# effective number of observations and the share of the weight in the last
# DAILY_RECENT_DAYS days. The text says that family A sets RiskMetrics against a
# window whose weights lie on nearly the same data, and that D is the comparison
# on one window. No expectation.
DAILY_D_DATE = "2026-11-18"
DAILY_D_VARIANT = ("sample", "daily_5y")          # the fifteenth path: the sample covariance on EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY[1] years of daily returns, under DAILY_D_SET; labelled "sample, daily 5y"
DAILY_D_SET = "C3"                                # the mandate
DAILY_COMPARISONS_D = (                           # first series less second, under the mandate, on months and on days
    (("RiskMetrics", "daily 5y"), ("sample", "daily 5y")),
    (("sample", "daily 5y"), ("sample", "daily 3y")),
)
DAILY_D_FREQUENCIES = ("monthly", "daily")
DAILY_WINDOWS_DESCRIBED = (                       # (label, years of daily returns, half-life in days or None for a flat window)
    ("RiskMetrics, daily 5y", EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY[1], EXT_COV_EWMA_HALFLIFE_DAYS),
    ("flat, daily 3y", EXT_COV_DAILY_WINDOW_YEARS, None),
    ("flat, daily 5y", EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY[1], None),
)
DAILY_RECENT_DAYS = 756                           # the last three years of trading days, the flat three-year window's length

# Settings of 20 November 2026, before part (c) ran and before any daily comparison
# was made (the daily tracking errors of the fourteen paths had been printed on
# 19 November, as the opening of this section says): what each reading of the
# RiskMetrics rows is read against, the size check at the correlations of the
# other rows, and the reconciliation of family C's six daily series.
DAILY_SETTINGS_DATE = "2026-11-20"
# What each reading is read against. The published version (Table 3, Panel B)
# sets "the published size" in every row; the working paper's gain is printed
# beside it with no reading. Under the mandate, A's RiskMetrics row and D's first
# row on months and on days are read against the capped pair, 13.00 against
# 13.36, a gain of 2.69 per cent of the reference figure here. C's two long-only
# rows against the long-only pair, 11.31 against 12.24, 7.6 per cent. C's two
# unconstrained rows: the paper has RiskMetrics above the sample covariance
# there, 11.36 against 10.91, so there is no published gain to exclude or
# include, and the rows have the three readings of DAILY_READINGS_UNCONSTRAINED.
# The rows against three years of data, A's and two of C's, are read against the
# same pairs, and each reading names the window as a difference from the paper,
# which estimates on one window of five years. daily.read_interval takes a row
# and its interval and returns the reading; part (c) calls it and writes no
# reading by hand (tests/test_daily.py checks every reading on made-up intervals).
DAILY_READING_VERSION = "published version, Table 3 Panel B"
DAILY_PAPER_WINDOW_YEARS = 5                      # the paper estimates every covariance on one window of five years
DAILY_READING_ROWS = (                            # (family, series 1, series 2, frequency or side, the paper's portfolio the row is read against, years of this row's sample-covariance window)
    ("A", "RiskMetrics, daily 5y", "sample, daily 3y", "daily", "with the cap", 3),
    ("D", "RiskMetrics, daily 5y", "sample, daily 5y", "monthly", "with the cap", 5),
    ("D", "RiskMetrics, daily 5y", "sample, daily 5y", "daily", "with the cap", 5),
    ("C", "sample, daily_5y_ewma", "sample, daily_5y", "unconstrained", "unconstrained", 5),
    ("C", "sample, daily_5y_ewma", "sample, daily_5y", "long-only", "long-only", 5),
    ("C", "sample, daily_5y_ewma", "sample, daily_3y", "unconstrained", "unconstrained", 3),
    ("C", "sample, daily_5y_ewma", "sample, daily_3y", "long-only", "long-only", 3),
)
DAILY_READINGS_UNCONSTRAINED = {                  # for a row whose published pair has RiskMetrics above the sample covariance
    "below": "a gain from RiskMetrics is found, where the paper reports none without constraints",
    "includes_zero": "no difference is found, and the paper reports no gain without constraints",
    "above": DAILY_READINGS["above"],
}
DAILY_WINDOW_CLAUSE = ("the paper estimates every covariance on one window of five years, and this row sets "
                       "RiskMetrics' five-year window against the sample covariance on three")
# P3 at the correlations of the other rows (ED3's pairs correlate at 0.93 on months, B's seven at 0.94 to
# 0.97, the monthly covariance's at 0.81): two more runs of the size check, DAILY_SIZE_PAIRS pairs each,
# with P3's other settings, its seed, its criterion (at most DAILY_SIZE_RATE_MAX) and its rule of reading
# (under DAILY_SIZE_RATE_LOW stated as rejecting less often than its level at that setting); each sentence
# names its setting. Set before part (c) ran.
DAILY_SIZE_FURTHER_CORRELATIONS = (0.93, 0.81)
# The six daily series of family C, notebook 10's minimum-variance portfolios, reconciled as gate D1
# reconciles the paths: the month's return compounded from the daily series against the monthly return of
# the rebuilt portfolio of the same run (the portfolios have no committed monthly return; their realised
# volatilities reproduce the committed table, gate D0), the correlation, the two volatilities and their
# gap, the largest monthly gap and its month, in a table, reported with no band. Added on 20 November
# 2026 after the series were built.
DAILY_C_RECONCILIATION_DATE = "2026-11-20"

# ---------------------------------------------------------------------------
# 10. Two further standard errors, added 24 November 2026
# ---------------------------------------------------------------------------
# Added on 24 November 2026, after every result of notebooks 13, 16, 17 and 18
# was known, and labelled so wherever they are used. They change no committed
# table; each is reported beside the standard error it supplements.
#
# (1) Notebook 18, the daily tests: a standard error from batch means. The
# kernel of paired.standard_errors chooses its bandwidth from the data, 8 to 13
# days, and 1 to 5 on the minimum-variance portfolios' rows on the daily
# series, while the variances of two paths can drift apart over months, so
# its standard error can be too small; the size check P3
# cannot show this, because its simulated pairs share one variance. Beside each
# of the 21 rows of the daily table: the study's statistic with a standard
# error from batch means of BATCH_MEANS_BLOCK_DAYS trading days (paired.
# batch_means), its p-value from Student's t with the number of blocks less
# one degrees of freedom, Holm's correction within family A and within family
# B (the families notebook 17 corrects), and the same at the further block
# lengths; family D's two rows on months use blocks of the same span in months.
# Beside each row, the number of calendar years in which the difference has the
# sign of the whole period. A's RiskMetrics row keeps the reading
# daily.read_interval gives on the study's interval; beside it, the reading the
# same rule returns on the batch-means interval.
BATCH_MEANS_DATE = "2026-11-24"
BATCH_MEANS_BLOCK_DAYS = 252                      # one year of trading days, the bootstrap's block
BATCH_MEANS_BLOCK_DAYS_FURTHER = (63, 126, 504)
BATCH_MEANS_MONTHS_OF = {63: 3, 126: 6, 252: 12, 504: 24}    # the same spans in months, for family D's rows on months
BATCH_MEANS_HOLM_FAMILIES = ("A", "B")
#
# (2) Notebooks 13 and 16, the factor attribution: a Newey-West standard error.
# The monthly contributions are serially correlated (the factor total's
# first-order autocorrelation is 0.16 to 0.32 on notebook 13's fourteen paths
# and 0.12 to 0.30 on notebook 16's nineteen), and the standard error of
# attribution.summarise takes the months as independent. Beside it, for every
# factor contribution, the factor total, the residual and the active return,
# and in notebook 13 for the cost of the exclusions and the beta constraint
# against the tilt alone: the Newey-West standard error with
# ATTRIBUTION_NEWEY_WEST_LAGS lags (attribution.newey_west). Notebook 13 also
# writes the monthly attribution of all fourteen paths, so that every count can
# be checked.
ATTRIBUTION_NEWEY_WEST_DATE = "2026-11-24"
ATTRIBUTION_NEWEY_WEST_LAGS = 6                   # 0.75 times the cube root of 566 months, 6.2, rounded down

# ---------------------------------------------------------------------------
# 11. The residual covariance given back, and shorter windows (notebook 19)
# ---------------------------------------------------------------------------
# Set on 26 November 2026, after the study's results were known. Notebook 19 asks
# why the two structured models realise more tracking error under the mandate
# than the daily sample covariance. It is an analysis run after the results,
# with no expectation and no verdict, and it changes no committed table.
#
# (1) The share of the residual covariance between industries given back to the
# six-factor model and the principal-component model on three years of daily
# returns: B Sigma_F B' + D + share (S_e - D), where S_e is the covariance of the
# model's residuals with the model's own denominator and D its diagonal
# (covariance.factor_residual_cov, covariance.pca_residual_cov,
# covariance.blended_cov). At 0 each model is the study's; at 1 each is the
# sample covariance but for the residuals' denominator.
#
# (2) The windows of the four daily estimators, in calendar months before the
# month, counted as covariance.daily_window counts its years
# (covariance.daily_window_months); 36 months is the study's three years.
#
# Every path is run under the mandate, C3, with the study's optimiser, and every
# pair is tested with notebook 18's paired test on days and notebook 17's on
# months. Holm's correction runs within each part and each frequency: the ten
# rows of (1), each path against the daily sample covariance on three years, and
# the fifteen rows of (2), each estimator against the sample covariance on the
# same window and the sample covariance on each shorter window against three years.
STRUCTURED_ADDITIONS_DATE = "2026-11-26"
RESIDUAL_COV_SHARES = (0.0, 0.25, 0.5, 0.75, 1.0)
SHORT_WINDOW_MONTHS = (3, 6, 12, 36)
