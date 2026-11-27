"""The naive portfolios of notebooks 08 and 09, and the settings they share with the optimised paths.

The settings of constants.py section 8 are the source's values: those the copied modules also read are compared with
src/bp/source/constants.py, and in a checkout that holds the source commit every one is compared with the source's
constants.py read with git. The two weighting functions are checked on made-up months: weights that sum to one, the tilt
at half the benchmark weight, the exclusions at zero, every other active weight within the bound, no weight below zero,
and k at the largest value the bound and the floor allow. The path, the bootstrap and the measures are checked on
made-up series against the formulas their docstrings state.
"""
import ast
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import constants as C  # noqa: E402
from bp import naive as N  # noqa: E402
from bp.source import constants as SC  # noqa: E402
from bp.source import evaluation as E  # noqa: E402
from bp.source import optimiser as O  # noqa: E402


def source_constants():
    """The source's constants.py at the commit as a dict of its top-level names, or None where the checkout lacks it."""
    if not (ROOT / ".git").exists():
        return None
    r = subprocess.run(["git", "cat-file", "-p", f"{C.SOURCE_COMMIT}:src/bp/constants.py"], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        return None
    values = {}
    exec(compile(r.stdout.decode(), "constants.py", "exec"), values)
    return values


def test_section_8_matches_the_copied_constants():
    shared = [n for n in C.NAIVE_TAKEN_FROM_SOURCE if hasattr(SC, n)]
    assert len(shared) >= 10
    for name in shared:
        assert getattr(C, name) == getattr(SC, name), name


def test_section_8_matches_the_source_at_the_commit():
    values = source_constants()
    if values is None:
        pytest.skip("this checkout does not hold the source commit")
    for name in C.NAIVE_TAKEN_FROM_SOURCE:
        if name == "CONSTRAINT_SETS":
            continue
        assert getattr(C, name) == values[name], name
    assert C.CONSTRAINT_SETS["C3"] == values["CONSTRAINT_SETS"]["C3"]


def test_every_name_of_section_8_is_listed():
    tree = ast.parse((ROOT / "src/bp/constants.py").read_text())
    names = [t.id for node in tree.body if isinstance(node, ast.Assign) for t in node.targets if isinstance(t, ast.Name)]
    start = names.index("COV_EVAL_START")
    taken = names[start:names.index("NAIVE_TAKEN_FROM_SOURCE")]
    assert set(taken) == set(C.NAIVE_TAKEN_FROM_SOURCE) | {"CONSTRAINT_SETS"}


def made_up_month(seed, n=49):
    rng = np.random.default_rng(seed)
    b = rng.lognormal(0.0, 1.0, n)
    b = b / b.sum()
    tilt = np.zeros(n, dtype=bool)
    tilt[[3, 17, 40]] = True
    excluded = np.zeros(n, dtype=bool)
    excluded[[8, 30]] = True
    score = rng.normal(0.0, 0.5, n)
    names = [f"i{i}" for i in range(n)]
    return b, tilt, excluded, score, names


@pytest.mark.parametrize("seed", range(20))
def test_naive_tilt(seed):
    b, tilt, _, _, _ = made_up_month(seed)
    w, info = N.naive_tilt(b, tilt)
    assert abs(w.sum() - 1.0) < 1e-14
    assert np.allclose(w[tilt], C.TILT_MAX_SHARE_OF_BENCHMARK * b[tilt], rtol=0, atol=1e-16)
    ratio = w[~tilt] / b[~tilt]
    assert np.allclose(ratio, ratio[0], rtol=1e-13)
    assert abs(info["removed weight"] - 0.5 * b[tilt].sum()) < 1e-15


@pytest.mark.parametrize("seed", range(20))
def test_tilted_index(seed):
    b, tilt, excluded, score, names = made_up_month(seed)
    w, info = N.tilted_index(b, tilt, excluded, score, names)
    rest = ~(tilt | excluded)
    assert abs(w.sum() - 1.0) < 1e-13
    assert (w[excluded] == 0).all()
    assert np.allclose(w[tilt], C.TILT_MAX_SHARE_OF_BENCHMARK * b[tilt], rtol=0, atol=1e-16)
    assert (w >= -1e-15).all()
    assert (np.abs(w - b)[rest] <= C.ACTIVE_WEIGHT_BOUND + 1e-12).all()
    assert info["k"] > 0
    # k is the largest value allowed: one constraint binds at the industry named
    i = names.index(info["k set at"])
    if info["k set by"] == "floor":
        assert abs(w[i]) < 1e-15
    else:
        assert abs(abs(w[i] - b[i]) - C.ACTIVE_WEIGHT_BOUND) < 1e-12
    # the score of the 44 rises over that of w0 by k times the w0-weighted sum of the squared centred scores
    w0 = b[rest] * (1.0 + info["removed weight"] / b[rest].sum())
    z = score[rest] - (w0 @ score[rest]) / w0.sum()
    assert w[rest] @ score[rest] - w0 @ score[rest] == pytest.approx(info["k"] * (w0 @ z ** 2), rel=1e-10)


def test_run_path_turnover_against_drifted_weights():
    rng = np.random.default_rng(3)
    months = pd.period_range("2000-01", periods=6, freq="M")
    cols = [f"i{i}" for i in range(5)]
    raw = rng.lognormal(0.0, 0.3, (6, 5))
    weights = pd.DataFrame(raw / raw.sum(axis=1, keepdims=True), index=months, columns=cols)
    returns = pd.DataFrame(rng.normal(0.01, 0.05, (6, 5)), index=months, columns=cols)
    betas = {m: rng.normal(0.0, 1.0, (5, 6)) for m in months}
    tilt = np.array([True, False, False, False, False])
    sign = np.array([C.FO_TARGET_SIGN[f] for f in C.ATTRIBUTION_FACTORS])
    path = N.run_path(lambda m, b: N.naive_tilt(b, tilt), months, weights, returns, betas, list(C.ATTRIBUTION_FACTORS), sign)
    w_first = path["weights"].iloc[0]
    assert abs(path["turnover"].iloc[0] - O.one_way_turnover(w_first, weights.iloc[0].to_numpy())) < 1e-15
    for j in range(1, 6):
        drifted = O.drifted_weights(path["weights"].iloc[j - 1], returns.iloc[j - 1].to_numpy())
        assert abs(path["turnover"].iloc[j] - O.one_way_turnover(path["weights"].iloc[j], drifted)) < 1e-15
        b = weights.iloc[j].to_numpy()
        assert abs(path["active_return"].iloc[j] - (path["weights"].iloc[j] - b) @ returns.iloc[j].to_numpy()) < 1e-15


def test_resamples_are_those_of_the_bias_band():
    rng = np.random.default_rng(5)
    n = 100
    idx = N.resample_indices(n)
    assert idx.shape == (C.EVAL_BOOTSTRAP_DRAWS, n)
    active = rng.normal(0.0, 0.01, n)
    forecast = np.full(n, 0.02)
    ratio = active / (forecast / np.sqrt(12.0))
    stats = np.std(ratio[idx], axis=1, ddof=1)
    tail = 100.0 * (1.0 - C.EVAL_BOOTSTRAP_LEVEL) / 2.0
    lo, hi = np.percentile(stats, [tail, 100.0 - tail])
    assert (lo, hi) == E.block_bootstrap_band(active, forecast)


def test_bootstrap_difference():
    d = np.concatenate([np.full(1990, 1.0), np.full(10, -1.0)])
    lo, hi, p = N.bootstrap_difference(d)
    assert p == pytest.approx(2.0 * 11 / 2001)
    assert lo <= hi
    assert N.bootstrap_difference(np.zeros(2000))[2] == 1.0


def test_measures():
    rng = np.random.default_rng(7)
    active = rng.normal(0.0002, 0.003, 120)
    turnover = rng.uniform(0.0, 0.02, 120)
    bench = rng.normal(0.006, 0.04, 120)
    m = N.measures(active, turnover, bench)
    te = np.std(active, ddof=1) * np.sqrt(12.0)
    assert m["realised TE"] == pytest.approx(te, rel=1e-14)
    assert m["active return (gross)"] == pytest.approx(12.0 * active.mean(), rel=1e-14)
    for c in C.EXT_COST_LEVELS:
        bp = int(round(c * 1e4))
        assert m[f"net active return at {bp} bp"] == pytest.approx(12.0 * active.mean() - 12.0 * turnover.mean() * c, rel=1e-12)
    assert m["realised beta"] == pytest.approx(np.polyfit(bench, bench + active, 1)[0], rel=1e-10)
