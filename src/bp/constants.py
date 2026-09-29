"""
Pre-committed numbers for B-P version 1.

Every tolerance, gate, sample boundary and design parameter the study uses is
defined here, one per line, before any notebook runs. A notebook may read these
names; it may not introduce a number of its own. If a number has to change, it
changes here, with the date and the reason, and the notebooks that depend on it
are re-run.

Sources, abbreviated in the comments:

  RULING  Finance Research Design chat, RULING_projectB_2026-09-06.html, section 4
          ("Project B, fixed"), read 10 September 2026 at 20:06 Europe/Amsterdam.
  BML     RULING_B-ML_and_MonteCarlo_2026-09-10.html, section 1, read the same
          evening at 20:07.
  DGU     DeMiguel, Garlappi and Uppal (2009), "Optimal Versus Naive
          Diversification: How Inefficient is the 1/N Portfolio Strategy?",
          Review of Financial Studies 22(5), 1915-1953. Page numbers are the
          journal's.
  PBM     A decision taken by Project B main on 10 September 2026 under the
          authority Carlo gave it that evening, with the reason beside it.
          Carlo's five conditions on any such decision: relevant to the job,
          teaches the job, not overly complex, feasible with the data held,
          safe from surprises.
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
# 2. The DGU replication (B-P core)
# ---------------------------------------------------------------------------

DGU_SAMPLE_START = "1963-07"   # DGU Table 2, p. 1918, for every French-sourced dataset
DGU_SAMPLE_END = "2004-11"     # DGU Table 2, p. 1918
DGU_ESTIMATION_WINDOW = 120    # months; DGU section 2, p. 1927; RULING. M = 60 is in DGU's appendix and is out of scope.
DGU_RISK_AVERSION = 1.0        # gamma in the CEQ, DGU p. 1929: "the results we report are for the case of gamma = 1"
DGU_TCOST = 0.0050             # proportional cost per unit of one-way turnover; DGU p. 1929: 50 basis points, after Balduzzi and Lynch (1999)
TCOST_SENSITIVITY = 0.0100     # RULING: "a sensitivity at double the cost is the only variant"
DGU_GMINC_LOWER_BOUND_FRACTION = 0.5   # g-min-c imposes w >= a * 1 with a = 1/(2N); DGU p. 1926
DGU_BS_COV_DOF = "M - N - 2"   # the Bayes-Stein covariance divides by M - N - 2; DGU equation (5), p. 1923

# PBM, 22 September 2026, a specification the paper leaves ambiguous, settled by
# its own footnote and by replication. DGU's Lagrangian (8), p. 1925, shows the
# short-sale constraint alone, which with the normalisation of equation (1)
# would make gamma irrelevant. Footnote 22, p. 1934, says the constrained rules
# produce "corner solutions with all wealth invested in a single asset", which
# only happens when the budget constraint 1'w = 1 sits inside the optimisation
# with gamma = 1. Run both ways on 22 September: with the budget inside, mv-c
# on MKT/SMB/HML gives 0.1093 against the published 0.1084 and puts all wealth
# in one asset in 257 of 377 months; without it, 0.2382 and never. The other
# three datasets and the turnover and CEQ rows agree the same way. The paper
# wins over the literal reading of its equation. The literal version is kept
# as strategies.mv_c_cone for the record and is not a reported rule.
DGU_CONSTRAINED_BUDGET_INSIDE = True

# The strategies replicated. RULING names "1/N, sample mean-variance, minimum
# variance, Bayes-Stein, short-sale-constrained versions". PBM reads g-min-c as a
# short-sale-constrained minimum-variance variant (it is min-c with the bound
# raised from 0 to 1/(2N), DGU p. 1926) and includes vw because its Sharpe ratio
# is the same 0.1138 in every French-sourced column of Table 3, which makes it a
# free check that the market series and the sample match the paper's.
DGU_STRATEGIES = ("ew", "mv", "bs", "min", "vw", "mv-c", "bs-c", "min-c", "g-min-c")
DGU_IN_SAMPLE_ROW = "mv (in sample)"   # DGU Table 3 row 2: mean-variance with M = T, the ceiling estimation error costs

# Excluded, each with the criterion. Nothing here is tuned around; they are not built.
DGU_STRATEGIES_EXCLUDED = {
    "Bayesian diffuse-prior": "not reported by DGU (Table 1 note, p. 1917)",
    "dm": "Bayesian Data-and-Model (Pastor 2000); needs an asset-pricing prior, not named in RULING",
    "mp": "MacKinlay and Pastor (2000) missing-factor model; maximum-likelihood factor structure, not named in RULING",
    "mv-min": "Kan and Zhou (2007) three-fund mixture; not named in RULING",
    "ew-min": "mixture of 1/N and minimum variance; not named in RULING",
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
# 3. Tolerances for the replication, written before the code runs
# ---------------------------------------------------------------------------

TOL_SHARPE_ABS = 0.03          # RULING: out-of-sample Sharpe ratio within 0.03 of DGU Table 3, per strategy and dataset
TOL_TOP3_RANKING = True        # RULING: the ranking of the top three strategies within each dataset is preserved
TOL_TURNOVER_REL = 0.25        # RULING: turnover within 25% relative of DGU Table 5

# PBM, 10 Sep 2026. DGU Table 5 reports the unconstrained mv strategy's turnover at
# 606,594 times that of 1/N on the Industry dataset and 10,466 times on FF-1-factor.
# Those figures are dominated by a handful of months in which the sample covariance
# is nearly singular, and they move by orders of magnitude when French revises a
# single return. A 25% band on them tests the vintage, not the code. The band is
# therefore applied only where DGU's published relative turnover is below the value
# here; above it, the replicated figure is reported beside the published one with
# no pass or fail. Decided before any strategy code exists.
TOL_TURNOVER_APPLIES_BELOW_RELATIVE = 100.0

# Decided by Carlo on 13 September 2026, after notebook 02 and on its evidence
# (option 1 of learning note 02). The out-of-sample Sharpe band applies only to
# rules whose published relative turnover (DGU Table 5, panel A) is below the
# same level; a rule above it is reported beside the published figure with the
# range that ten basis points of noise produces, and carries no verdict. The
# level is DGU's number, not ours, and the turnover band already used it. The
# in-sample mean-variance row carries no verdict either: TOL_SHARPE_ABS was
# written for out-of-sample Sharpe ratios. Evidence: on the Industry, FF-1 and
# FF-4 datasets the unconstrained mean-variance rule moved by 0.12 to 0.25 under
# ten basis points of noise, with the published figure inside the range, while
# the 1/N rows matched to the third decimal.
TOL_SHARPE_APPLIES_BELOW_RELATIVE = TOL_TURNOVER_APPLIES_BELOW_RELATIVE
TOL_SHARPE_DECISION_DATE = "2026-09-13"

# Sharpe ratios are compared on the same sample, 1963-07 to 2004-11, 120-month
# window, so the out-of-sample period is 1973-07 to 2004-11.
DGU_EXPECTED_T = 497           # months from 1963-07 to 2004-11 inclusive; a count, checked in notebook 01
DGU_EXPECTED_OOS = 377         # DGU_EXPECTED_T - DGU_ESTIMATION_WINDOW

# ---------------------------------------------------------------------------
# 4. DGU's simulation and analytical result (notebook 04; BML section 1)
# ---------------------------------------------------------------------------

# The analytical critical window (DGU Proposition 1, pp. 1937-1938; Figure 1, p. 1940).
# Panel E is the one calibrated to US stock-market data and the one BML quotes.
ANALYTIC_SHARPE_TANGENCY = 0.15    # S*, DGU Figure 1 panel E
ANALYTIC_SHARPE_1N = 0.12          # S_ew, DGU Figure 1 panel E
EXPECT_CRITICAL_M_LOWER = {25: 3000, 50: 6000}   # DGU p. 1941: "more than 3000 months" and "more than 6000 months"; BML: match order of magnitude and direction in N

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
SIM_T = 24000                        # months on one simulated path
SIM_SEED = 20260910                  # PBM: fixed so the run is reproducible; DGU's seed is unknown
# PBM: on one 24,000-month path the standard error of a monthly Sharpe ratio is about
# 1/sqrt(24000) = 0.0065, so the replication band for DGU Table 6 is TOL_SHARPE_ABS,
# and in addition the sign of (mv minus 1/N) must match Table 6 in every (N, M) cell.
TOL_SIM_SHARPE_ABS = TOL_SHARPE_ABS

# ---------------------------------------------------------------------------
# 5. The extension: constrained index tracking on the 49 industries
# ---------------------------------------------------------------------------

EXT_UNIVERSE = "ind49"
EXT_ESTIMATION_WINDOW = 120        # PBM: the same window as the core, so one convention runs through the repository
EXT_REBALANCE = "monthly"          # PBM
# The extension sample starts at the first month in which all 49 industries carry
# a return (French codes the early gaps as -99.99). That start month is a count:
# on the 202607 vintage, read on 10 September 2026, Hlth is the last industry to
# fill and does so in 1969-07. Notebook 01 asserts it on every run, so a vintage
# that moves it fails loudly.
EXT_SAMPLE_START = "1969-07"
EXT_SAMPLE_END = None              # the latest month the vintage carries

# The parent (the index the portfolio tracks). RULING, count-first check: the
# cap-weighted combination of the 49 industries, weights from firm count times
# average firm size, must track the market factor plus the risk-free rate within
# 50 basis points a year of tracking error over the full sample. If it does not,
# the derived weights are dropped and the parent is the market series.
CAPW_TE_MAX_ANNUAL = 0.0050

# Constraints. PBM, 10 Sep 2026.
ACTIVE_WEIGHT_BOUND = 0.02         # each untilted industry within 2 percentage points of its parent weight; an absolute cap does not fit 49 industries whose parent weights run from under 0.5% to over 10%
TURNOVER_CAP_MONTHLY_ONE_WAY = 0.02   # one-way turnover per rebalance, against drifted weights; 2% a month is about 24% a year, the enhanced-indexing range
TILT_INDUSTRIES = ("Coal", "Oil", "Util")   # RULING; French's column names, stripped of padding
TILT_MAX_SHARE_OF_BENCHMARK = 0.5  # each tilted industry held at no more than half its parent weight, reported as a 50% reduction relative to the benchmark; a tilted industry's bounds are [0, 0.5 * parent], and ACTIVE_WEIGHT_BOUND does not apply to it, because the two would conflict for any industry above 4% of the parent
LONG_ONLY = True

# Constraint sets, cumulative, reported in this order.
CONSTRAINT_SETS = {
    "C0": ("long_only",),
    "C1": ("long_only", "active_weight_bound"),
    "C2": ("long_only", "active_weight_bound", "turnover_cap"),
    "C3": ("long_only", "active_weight_bound", "turnover_cap", "tilt"),
}
# The optimiser also accepts an exclusion list (weight zero on named assets). It is
# built and tested because paper two needs it, and it is not one of the reported
# constraint sets in version 1.

# Covariance estimators, RULING. LW_TARGET is provisional (PBM) until Beyond GMV
# has been read before notebook 08; if that paper uses a different Ledoit-Wolf
# target for its constrained portfolios, the target follows the paper and this
# line records the change.
COV_ESTIMATORS = ("sample", "ledoit_wolf", "factor", "pca")
LW_TARGET = "constant_correlation"     # Ledoit and Wolf (2004a), "Honey, I Shrunk the Sample Covariance Matrix"
FACTOR_MODEL_FACTORS = ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom")   # PBM: Fama-French five plus momentum, the set paper two uses for its factor tilt, so both documents speak the same vocabulary; the estimator is B F B' plus a diagonal of residual variances, B estimated in the same rolling window
PCA_N_COMPONENTS = 5                   # RULING: five components plus a diagonal idiosyncratic term
PCA_PC1_MARKET_CORR_MIN = 0.95         # RULING: the first component's correlation with the cap-weighted market return
PCA_USE_COVARIANCE = True              # RULING: covariance, not correlation, of monthly excess returns
PCA_SIGN_RULE = "positive market loading"
PCA_WINDOWS = {                        # RULING: three pre-specified windows; loading stability is the finding and carries no threshold
    "to_2019":   (None, "2019-12"),
    "2020_2022": ("2020-01", "2022-12"),
    "from_2023": ("2023-01", None),
}

# Attribution, BML section 5: factor-based attribution of each constrained
# portfolio's realised active return against the factors above, contribution by
# factor plus residual, with the identity as the check.
ATTRIBUTION_FACTORS = FACTOR_MODEL_FACTORS
ATTRIBUTION_IDENTITY_TOL = 1e-9        # contributions plus residual minus active return, per month, in return units

# Specification count, RULING ("written down before the code runs, and reported").
# Replication: one specification per strategy and dataset. Extension:
EXT_SPEC_COUNT = len(COV_ESTIMATORS) * len(CONSTRAINT_SETS)   # 16 optimised specifications
EXT_COST_LEVELS = (DGU_TCOST, TCOST_SENSITIVITY)              # each reported net of cost at both levels; the cost is applied after the fact and does not enter the optimisation

# ---------------------------------------------------------------------------
# 6. Output conventions
# ---------------------------------------------------------------------------

OUTPUT_DIR = "outputs"
PROVENANCE_FILE = "outputs/provenance_french.json"   # download date, URL, SHA-256 and CRSP vintage line per file
TIMEZONE = "Europe/Amsterdam"
