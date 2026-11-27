"""
Pre-committed numbers for the study.

Every band, gate, sample boundary and design parameter is defined here, one
per line, with its source beside it. A notebook may read these names; it may
not introduce numbers of its own. The replication bands (section 3) were
fixed on 10 September 2026, before any of the rules' code was
written. The expectations each notebook tests are
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
# 5. The 49 industries: the sample, and the three industries the mandate tilts
# ---------------------------------------------------------------------------

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

TILT_INDUSTRIES = ("Coal", "Oil", "Util")   # French's column names, stripped of padding

# ---------------------------------------------------------------------------
# 6. Output conventions
# ---------------------------------------------------------------------------

OUTPUT_DIR = "outputs"
PROVENANCE_FILE = "outputs/provenance_french.json"   # download date, URL, SHA-256 and CRSP vintage line per file
TIMEZONE = "Europe/Amsterdam"

# ---------------------------------------------------------------------------
# 7. The code and the tables taken from risk-models-for-index-tracking
# ---------------------------------------------------------------------------

# The comparisons with the naive rules under the index mandate run the optimised portfolios' own code and read their
# recorded figures. Both come from the repository risk-models-for-index-tracking at commit ddbb75c, whose history up to
# that commit is this repository's. The modules are copied into SOURCE_MODULES_DIR, each unchanged below a first line
# naming its source file and the commit, and src/bp/source/constants.py holds the source's values of the names they
# read. The tables are copied unchanged into SOURCE_TABLES_DIR. tests/test_source_copies.py checks every copy against
# the SHA-256 below and, in a checkout that holds the commit, against the file at the commit.
SOURCE_REPOSITORY = "https://github.com/ochofer/risk-models-for-index-tracking"
SOURCE_COMMIT = "ddbb75c"
SOURCE_MODULES_DIR = "src/bp/source/"
SOURCE_TABLES_DIR = "results/202608/source/"
SOURCE_MODULES = {
    "benchmark.py": ("src/bp/benchmark.py", "f9c6b71a8f44a66e2756e18d75281729fc4cd65e598a420384661e149d9df2b1"),
    "covariance.py": ("src/bp/covariance.py", "296b842291ad829c48fa784db114adc3495f26cb1441cc3776357421280b193a"),
    "optimiser.py": ("src/bp/optimiser.py", "8944b967bb5969fe3c4b2ffbc603aa2b75a6fddc0683735fc842ec241e303b93"),
    "evaluation.py": ("src/bp/evaluation.py", "5e92444e694996f7801864ce3feaea96a2d290aae97ac2e1525e78229d59d23d"),
    "attribution.py": ("src/bp/attribution.py", "61e14a7106f9398f5d82a178f376dc3fa8ec73fa48baeacff91c1dcd53f0c97c"),
    "paired.py": ("src/bp/paired.py", "579d216032e9ec6ab8e3c0619dd5c33700afbe1a873d2cfe9ea454c01a264bb5"),
    "rules.py": ("src/bp/rules.py", "c18872058185839981806dafdc5de417b25ea4a9d2e607cd01d615775a4addeb"),
    "french_loader.py": ("src/bp/french_loader.py", "83e01cb19c5640d81e19fe828b816f5bd115ea15e3b56fdbd63dea8aaabca6b1"),
}
SOURCE_CONSTANTS_SHA256 = "0ba29dc41644607d89318d50c16299901453b4e89b4444f119982fbd8912b4d9"   # src/bp/constants.py at the commit, 1,168 lines
SOURCE_TABLES = {
    "rolling_evaluation_202608.csv": ("results/202608/rolling_evaluation_202608.csv", "32cea22bcf34f975923f60af457bf653c731d4cdc71043e6166b944cfd279446"),
    "active_returns_202608.csv": ("results/202608/active_returns_202608.csv", "f83481400080e5cbaa8a4fb907e72a59ec97de41b89c6c89f8185d2cc51cd2c4"),
    "attribution_summary_202608.csv": ("results/202608/attribution_summary_202608.csv", "6059b492760f4cee547555b0a52558134710d0a356de5197d98cbd7968d1c877"),
    "factor_objective_evaluation_202608.csv": ("results/202608/factor_objective_evaluation_202608.csv", "d9bc6c735a350942a49fecce64595190a7c2280e2bc5057835eba0c729c1a926"),
    "factor_objective_monthly_202608.csv": ("results/202608/factor_objective_monthly_202608.csv", "a19f45ea671af1553912446a1bc848bae918e07e75d3509f706c117e1a99ef2b"),
    "factor_objective_attribution_202608.csv": ("results/202608/factor_objective_attribution_202608.csv", "7b917c8ebabd805f47526a97d351e7ade83351ac2d2cf73b3d69f426d9bacd4c"),
}
