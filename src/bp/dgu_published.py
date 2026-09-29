"""
The published numbers of DeMiguel, Garlappi and Uppal (2009), Review of
Financial Studies 22(5), transcribed from Tables 3, 4, 5 and 6, for the four
datasets built from Ken French's library.

The comparison tables in notebooks 02 to 05 are built from this module, never
typed into a notebook. tests/test_dgu_published.py re-reads the numbers from
the journal PDF when it is present on the machine (papers/, not committed) and
fails on any digit that differs.

Monthly figures throughout. Sharpe ratios and CEQ returns are for the
out-of-sample period 1973-07 to 2004-11 with a 120-month window (Tables 3 and
4); "mv (in sample)" uses the full sample. Turnover (Table 5) is the 1/N
strategy's absolute monthly turnover and every other strategy's turnover
relative to it; return-loss is the extra monthly return a strategy needs to
match 1/N's Sharpe ratio net of a 50 basis point proportional cost.
"""

DATASETS = ("Industry", "MKT/SMB/HML", "FF-1-factor", "FF-4-factor")

# Table 3, p. 1931: monthly Sharpe ratio, with the Jobson-Korkie p-value of the
# difference from 1/N in the second tuple (None where the paper prints none).
SHARPE = {
    "ew":              ((0.1353, 0.2240, 0.1623, 0.1753), None),
    "mv (in sample)":  ((0.2124, 0.2851, 0.5098, 0.5364), None),
    "mv":              ((0.0679, 0.2186, 0.0128, 0.1841), (0.17, 0.46, 0.02, 0.45)),
    "bs":              ((0.0719, 0.2536, 0.0138, 0.1791), (0.19, 0.25, 0.02, 0.48)),
    "dm":              ((0.0581, 0.0016, 0.0004, 0.2355), (0.14, 0.00, 0.01, 0.17)),
    "min":             ((0.1554, 0.2493, 0.2778, -0.0183), (0.30, 0.23, 0.01, 0.01)),
    "vw":              ((0.1138, 0.1138, 0.1138, 0.1138), (0.01, 0.00, 0.01, 0.00)),
    "mp":              ((0.0533, -0.0002, 0.1238, 0.1230), (0.04, 0.00, 0.08, 0.03)),
    "mv-c":            ((0.0678, 0.1084, 0.1977, 0.2024), (0.03, 0.02, 0.02, 0.27)),
    "bs-c":            ((0.0819, 0.1514, 0.1955, 0.2062), (0.06, 0.09, 0.03, 0.25)),
    "min-c":           ((0.1425, 0.2493, 0.1546, 0.3580), (0.41, 0.23, 0.35, 0.00)),
    "g-min-c":         ((0.1451, 0.2467, 0.1615, 0.3028), (0.31, 0.25, 0.47, 0.00)),
    "mv-min":          ((0.0772, 0.2546, -0.0079, 0.1757), (0.21, 0.22, 0.01, 0.50)),
    "ew-min":          ((0.1576, 0.2503, 0.2608, -0.0161), (0.21, 0.17, 0.00, 0.01)),
}

# Table 4, p. 1934: monthly certainty-equivalent return, gamma = 1, with p-values.
CEQ = {
    "ew":              ((0.0050, 0.0039, 0.0073, 0.0072), None),
    "mv (in sample)":  ((0.0106, 0.0047, 0.0300, 0.0304), None),
    "mv":              ((-0.7816, 0.0045, -2.7142, -0.0829), (0.00, 0.31, 0.00, 0.01)),
    "bs":              ((-0.3157, 0.0043, -0.6504, -0.0362), (0.00, 0.32, 0.00, 0.06)),
    "dm":              ((-0.0319, -0.0084, -0.0296, 0.0110), (0.01, 0.04, 0.00, 0.11)),
    "min":             ((0.0052, 0.0039, 0.0100, -0.0002), (0.45, 0.45, 0.12, 0.00)),
    "vw":              ((0.0042, 0.0042, 0.0042, 0.0042), (0.04, 0.44, 0.00, 0.00)),
    "mp":              ((0.0014, -0.0026, 0.0054, 0.0053), (0.05, 0.04, 0.09, 0.10)),
    "mv-c":            ((0.0023, 0.0030, 0.0090, 0.0075), (0.10, 0.28, 0.03, 0.42)),
    "bs-c":            ((0.0031, 0.0038, 0.0088, 0.0074), (0.15, 0.46, 0.05, 0.44)),
    "min-c":           ((0.0047, 0.0039, 0.0060, 0.0051), (0.40, 0.45, 0.12, 0.17)),
    "g-min-c":         ((0.0048, 0.0038, 0.0067, 0.0070), (0.41, 0.40, 0.17, 0.45)),
    "mv-min":          ((-0.2337, 0.0044, -0.0875, -0.0318), (0.00, 0.28, 0.00, 0.07)),
    "ew-min":          ((0.0052, 0.0039, 0.0093, -0.0002), (0.42, 0.43, 0.12, 0.00)),
}

# Table 5, p. 1935. TURNOVER_1N is absolute; TURNOVER_RELATIVE is each strategy's
# turnover divided by 1/N's; RETURN_LOSS is panel B.
TURNOVER_1N = (0.0216, 0.0237, 0.0162, 0.0198)
TURNOVER_RELATIVE = {
    "mv":       (606594.36, 2.83, 10466.10, 3553.03),
    "bs":       (10621.23, 1.85, 11796.47, 3417.81),
    "dm":       (21744.35, 76.30, 918.40, 32.46),
    "min":      (21.65, 1.11, 45.47, 6.83),
    "vw":       (0.0, 0.0, 0.0, 0.0),
    "mp":       (11.98, 59.41, 2.39, 2.07),
    "mv-c":     (7.17, 4.12, 17.53, 13.82),
    "bs-c":     (7.22, 3.65, 17.32, 13.07),
    "min-c":    (2.58, 1.11, 3.93, 1.76),
    "g-min-c":  (1.52, 1.09, 1.78, 1.70),
    "mv-min":   (9927.09, 2.61, 4292.16, 4857.19),
    "ew-min":   (15.66, 1.11, 34.10, 6.80),
}
RETURN_LOSS = {
    "mv":       (231.8504, 0.0003, 7.4030, 1.5740),
    "bs":       (9.4602, -0.0004, 2.0858, 1.1876),
    "dm":       (8.9987, 0.0393, 0.1302, -0.0007),
    "min":      (0.0015, -0.0004, -0.0008, 0.0024),
    "vw":       (0.0037, 0.0157, 0.0021, 0.0028),
    "mp":       (0.0050, 0.0227, 0.0023, 0.0030),
    "mv-c":     (0.0048, 0.0041, -0.0005, 0.0002),
    "bs-c":     (0.0038, 0.0023, -0.0004, -0.0000),
    "min-c":    (-0.0001, -0.0004, 0.0006, -0.0025),
    "g-min-c":  (-0.0003, -0.0003, 0.0001, -0.0029),
    "mv-min":   (6.8115, -0.0003, 0.9306, 1.8979),
    "ew-min":   (0.0008, -0.0004, -0.0011, 0.0024),
}

# Table 6, p. 1943: simulated data, monthly Sharpe ratio, columns ordered
# (N=10: M=120, 360, 6000), (N=25: same), (N=50: same).
SIM_COLUMNS = tuple((n, m) for n in (10, 25, 50) for m in (120, 360, 6000))
SIM_SHARPE = {
    "ew":        (0.1356, 0.1356, 0.1356, 0.1447, 0.1447, 0.1447, 0.1466, 0.1466, 0.1466),
    "mv (true)": (0.1477, 0.1477, 0.1477, 0.1477, 0.1477, 0.1477, 0.1477, 0.1477, 0.1477),
    "mv":        (-0.0019, 0.0077, 0.1416, 0.0027, 0.0059, 0.1353, 0.0078, -0.0030, 0.1212),
    "bs":        (-0.0021, 0.0087, 0.1416, 0.0031, 0.0074, 0.1363, 0.0076, -0.0035, 0.1229),
    "dm":        (0.0725, 0.1475, 0.1464, 0.0133, 0.1473, 0.1457, 0.0201, 0.0380, 0.1430),
    "min":       (0.1113, 0.1181, 0.1208, 0.0804, 0.0911, 0.0956, 0.0491, 0.0676, 0.0696),
    "mp":        (0.1171, 0.1349, 0.1354, 0.1265, 0.1442, 0.1446, 0.1312, 0.1460, 0.1465),
    "mv-c":      (0.0970, 0.1121, 0.1276, 0.1011, 0.1150, 0.1315, 0.1111, 0.1194, 0.1355),
    "bs-c":      (0.1039, 0.1221, 0.1317, 0.1095, 0.1222, 0.1350, 0.1162, 0.1251, 0.1381),
    "min-c":     (0.1284, 0.1324, 0.1335, 0.1181, 0.1227, 0.1248, 0.1224, 0.1277, 0.1292),
    "g-min-c":   (0.1289, 0.1312, 0.1320, 0.1311, 0.1336, 0.1348, 0.1364, 0.1402, 0.1415),
    "mv-min":    (-0.0029, 0.0106, 0.1414, 0.0087, 0.0172, 0.1361, 0.0016, -0.0068, 0.1229),
    "ew-min":    (0.1116, 0.1184, 0.1211, 0.0810, 0.0918, 0.0964, 0.0496, 0.0684, 0.0706),
}


def table(name: str):
    """A pandas DataFrame of one published table, strategies by dataset."""
    import pandas as pd
    if name == "sharpe":
        return pd.DataFrame({k: v[0] for k, v in SHARPE.items()}, index=DATASETS).T
    if name == "ceq":
        return pd.DataFrame({k: v[0] for k, v in CEQ.items()}, index=DATASETS).T
    if name == "turnover_relative":
        return pd.DataFrame(TURNOVER_RELATIVE, index=DATASETS).T
    if name == "return_loss":
        return pd.DataFrame(RETURN_LOSS, index=DATASETS).T
    if name == "sim_sharpe":
        cols = pd.MultiIndex.from_tuples(SIM_COLUMNS, names=["N", "M"])
        return pd.DataFrame(SIM_SHARPE, index=cols).T
    raise KeyError(name)
