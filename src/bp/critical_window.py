"""
DGU Proposition 1 (pp. 1937-1938): how long an estimation window the
sample-based mean-variance rule needs before it beats 1/N on average.

The argument. An investor who knew the true mean vector mu
and covariance Sigma would hold the tangency portfolio and earn expected
utility S*^2 / (2 gamma), where S* is that portfolio's Sharpe ratio. Using
1/N instead costs a known amount, (S*^2 - S_ew^2) / (2 gamma), equation (B6),
where S_ew is the Sharpe ratio of the 1/N rule. Using the sample-based
rule costs an amount that depends on how large the estimation error is, which
shrinks as the window M lengthens and grows with the number of assets N,
equations (B1) to (B3). The critical window M* is the smallest M at which the
second cost falls below the first: from there on, estimating pays.

Three cases, from the proposition:
  1. mu unknown, Sigma known:      S*^2 - S_ew^2 - N/M > 0
  2. mu known, Sigma unknown:      k S*^2 - S_ew^2 > 0
  3. both unknown:                 k S*^2 - S_ew^2 - h > 0
with, equations (25) and (27),
  k = M/(M-N-2) * (2 - M(M-2)/((M-N-1)(M-N-4)))       (< 1)
  h = N M (M-2) / ((M-N-1)(M-N-2)(M-N-4))               (> 0)
The formulas need M > N + 4.
"""
from __future__ import annotations

import numpy as np


def k_factor(M: float, N: int) -> float:
    return M / (M - N - 2) * (2.0 - M * (M - 2) / ((M - N - 1) * (M - N - 4)))


def h_factor(M: float, N: int) -> float:
    return N * M * (M - 2) / ((M - N - 1) * (M - N - 2) * (M - N - 4))


def advantage(M: float, N: int, s_star: float, s_ew: float, case: int = 3) -> float:
    """Left-hand side of the proposition's inequality; positive means mean-variance wins on average."""
    if case == 1:
        return s_star**2 - s_ew**2 - N / M
    if case == 2:
        return k_factor(M, N) * s_star**2 - s_ew**2
    if case == 3:
        return k_factor(M, N) * s_star**2 - s_ew**2 - h_factor(M, N)
    raise ValueError(case)


def critical_window(N: int, s_star: float, s_ew: float, case: int = 3, m_max: int = 200_000) -> int | None:
    """The smallest window M (months) at which the sample-based mean-variance rule beats 1/N on average.

    None when no window up to m_max does, which happens when S_ew >= S* in case 1
    or whenever the 1/N Sharpe ratio is too close to the tangency one for the
    estimation cost ever to fall below the 1/N cost.
    """
    if case == 1:
        gap = s_star**2 - s_ew**2
        if gap <= 0:
            return None
        return int(np.floor(N / gap)) + 1
    for M in range(N + 5, m_max + 1):
        if advantage(M, N, s_star, s_ew, case) > 0:
            return M
    return None


# The six panels of DGU Figure 1 (p. 1940), with the values the text states for
# them (pp. 1939-1941). "about" and "more than" are the paper's own words.
FIGURE_1_PANELS = {
    "A": {"s_star": 0.40, "s_ew": 0.20, "stated": {25: (">", 200), 50: ("about", 600), 100: (">", 1200)}},
    "B": {"s_star": 0.40, "s_ew": 0.10, "stated": {25: ("=", 270), 50: ("=", 530), 100: ("=", 1060)}},
    "C": {"s_star": 0.20, "s_ew": 0.10, "stated": {25: ("about", 1000), 50: ("about", 2000)}},
    "D": {"s_star": 0.20, "s_ew": 0.05, "stated": {50: (">", 1500)}},
    "E": {"s_star": 0.15, "s_ew": 0.12, "stated": {25: (">", 3000), 50: (">", 6000)}},
    "F": {"s_star": 0.15, "s_ew": 0.08, "stated": {25: (">", 1600), 50: (">", 3200)}},
}


def figure_1_table() -> "pandas.DataFrame":
    """Every stated value beside the computed one, with a verdict in the paper's own terms."""
    import pandas as pd
    rows = []
    for panel, spec in FIGURE_1_PANELS.items():
        for N, (rel, value) in spec["stated"].items():
            m = critical_window(N, spec["s_star"], spec["s_ew"], case=3)
            if rel == ">":
                ok = m is not None and m > value
            elif rel == "about":
                ok = m is not None and abs(m - value) / value <= 0.15
            else:
                ok = m is not None and abs(m - value) <= 10
            rows.append({"panel": panel, "S*": spec["s_star"], "S_ew": spec["s_ew"], "N": N,
                         "stated": f"{rel} {value}", "computed": m, "verdict": "pass" if ok else "MISS"})
    return pd.DataFrame(rows).set_index(["panel", "N"])
