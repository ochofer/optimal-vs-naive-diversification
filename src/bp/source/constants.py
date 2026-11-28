"""
The values of src/bp/constants.py at commit ddbb75c of the repository risk-models-for-index-tracking, kept so that the
copies in this folder import. This file holds every name the copies read and no other, each at its value at that
commit, with its line number there beside it; constants.SOURCE_CONSTANTS_SHA256 in the parent package is the hash of
that file. Where the source wrote a value as an expression of other names, the value is written out. No module outside
this folder reads this file: the comparisons with the two naive portfolios read their settings from src/bp/constants.py.
tests/test_source_copies.py checks the names against the copies' text and, in a checkout that holds the commit, each
value and line number against the file at the commit.
"""

# Read by benchmark.py
CAPW_MARKET_SERIES = ("Mkt-RF", "RF")   # line 270
CAPW_WEIGHT_TIMING = "same_month"   # line 268

# Read by covariance.py, with the names listed earlier
ACTIVE_WEIGHT_BOUND = 0.02   # line 301
COV_ESTIMATORS = ("sample", "ledoit_wolf", "factor", "pca")   # line 357
COV_SCALE_VR_HORIZON_DAYS = 21   # line 400
COV_TEST_ACTIVE_DRAWS = 200   # line 390
COV_TEST_SEED = 20260910   # line 391
DAILY_TO_MONTHLY_SCALE = 21   # line 338
EWMA_VARIANT = ("sample", "daily_5y_ewma")   # line 458
EXT_COV_DAILY_WINDOW_YEARS = 3   # line 336
EXT_COV_DAILY_WINDOW_YEARS_SENSITIVITY = (1, 5)   # line 337
EXT_COV_EWMA_HALFLIFE_DAYS = 252   # line 339
EXT_ESTIMATION_WINDOW = 120   # line 226
EXT_SAMPLE_START = "1969-07"   # line 231
PCA_N_COMPONENTS = 5   # line 361
PCA_N_COMPONENTS_SENSITIVITY = 2   # line 384
ROBUST_VARIANT = ("robust", "all_five")   # line 430

# Read by optimiser.py, with the names listed earlier
FO_E1_BIND_TOL_ANNUAL = 0.0001   # line 632
FO_SOLVER_OPTIONS_LOOSE = {"tol_gap_abs": 1e-7, "tol_gap_rel": 1e-7, "tol_feas": 1e-7}   # line 726
OPT_SOLVER = "CLARABEL"   # line 409
OPT_SOLVER_OPTIONS = {"tol_gap_abs": 1e-12, "tol_gap_rel": 1e-12, "tol_feas": 1e-10}   # line 410
OPT_SOLVER_OPTIONS_ROBUST = {"tol_gap_abs": 1e-9, "tol_gap_rel": 1e-9, "tol_feas": 1e-9}   # line 411
OPT_TOL = 1e-6   # line 412
TILT_INDUSTRIES = ("Coal", "Oil", "Util")   # line 303
TILT_MAX_SHARE_OF_BENCHMARK = 0.5   # line 304
TURNOVER_CAP_MONTHLY_ONE_WAY = 0.02   # line 302

# Read by evaluation.py
ATTRIBUTION_FACTORS = ('Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA', 'Mom')   # line 530
EVAL_BOOTSTRAP_BLOCK_MONTHS = 12   # line 484
EVAL_BOOTSTRAP_DRAWS = 2000   # line 485
EVAL_BOOTSTRAP_LEVEL = 0.95   # line 487
EVAL_BOOTSTRAP_SEED = 20261009   # line 486
EVAL_CALIBRATION_MIN = 24   # line 460
EVAL_CALIBRATION_WINDOW = 60   # line 459
EVAL_ROLLING_TE_MONTHS = 36   # line 508
EXT_COST_LEVELS = (0.005, 0.01)   # line 550
FO_TARGET_FACTORS = ("HML", "RMW", "CMA", "Mom")   # line 582
OPT_TOL_TE = 1e-6   # line 413

# Read by rules.py
DGU_CONSTRAINED_BUDGET_INSIDE = True   # line 67
DGU_GMINC_LOWER_BOUND_FRACTION = 0.5   # line 55
DGU_RISK_AVERSION = 1.0   # line 52

# Read by french_loader.py
EXT_SAMPLE_END = "2026-08"   # line 244
FRENCH_BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"   # line 23
FRENCH_FILES = {   # line 28
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
FRENCH_MISSING_CODES = (-99.99, -999.0)   # line 42
FRENCH_RETURNS_ARE_PERCENT = True   # line 43
PROVENANCE_FILE = "outputs/provenance_french.json"   # line 557
TIMEZONE = "Europe/Amsterdam"   # line 558
