"""
Portfolio rules from DeMiguel, Garlappi and Uppal (2009), section 1.

Each rule is a function of one estimation window of monthly excess returns,
an array of shape (M, N), and returns the vector of relative weights on the N
risky assets, DGU equation (1): the mean-variance solution x = Sigma^-1 mu / gamma
normalised by the absolute value of its sum, so that the weights sum to +1 or
to -1 and the direction of the position is preserved in the few windows where
the risky assets are net short.

Notation follows the paper: mu and Sigma are the sample moments of the window,
M its length, N the number of assets. The risk aversion gamma cancels in the
normalisation for every unconstrained rule, which is why it does not appear.

Rules in this module, with the DGU abbreviation and section:
  ew       1/N, section 1.1
  mv       sample-based mean-variance, section 1.2
  bs       Bayes-Stein shrinkage, section 1.3.2, Jorion (1986)
  min      minimum variance, section 1.4.1
  vw       the value-weighted market, section 1.4.2 (all weight on the market column)
  mv-c     short-sale-constrained mean-variance, section 1.5
  bs-c     short-sale-constrained Bayes-Stein, section 1.5
  min-c    short-sale-constrained minimum variance, section 1.5
  g-min-c  minimum variance with every weight at least 1/(2N), section 1.5

The constrained rules are quadratic programmes with a budget constraint,
  minimise  w' Sigma w / 2 - mu' w   subject to 1'w = 1 and w >= a 1,
solved exactly by an active-set method written in this module (_budget_qp):
the budget is an equality of the problem and the lower bound a bound on each
weight, so no constraint is approximated by a weight and no result depends on a
solver setting. The method is the one Lawson and Hanson's algorithm belongs to:
it starts with the whole budget on the one weight that gives the lowest
objective, solves the equality-constrained problem on the weights above the bound, moves toward that solution until a weight reaches the
bound, and frees a weight at the bound while its multiplier says the objective
falls by freeing it. Every step lowers the objective, so it ends after a finite
number of steps at the point that satisfies the optimality conditions; the
test of a multiplier allows ten units of rounding in the last place and
nothing more. nonneg_mean_variance, the reading of DGU's Lagrangian without the
budget, is a non-negative least squares problem and uses scipy.optimize.nnls.
tests/ checks every rule against an independent solver and checks the
optimality conditions at the scale of the study's data.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import nnls

from . import constants as C


def sample_moments(R: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sample mean and covariance (divisor M - 1) of an (M, N) window."""
    R = np.asarray(R, dtype=float)
    mu = R.mean(axis=0)
    Sigma = np.cov(R, rowvar=False, ddof=1)
    return mu, np.atleast_2d(Sigma)


def normalise(x: np.ndarray) -> np.ndarray:
    """DGU equation (1): w = x / |1'x|."""
    s = float(np.sum(x))
    if s == 0.0:
        raise ZeroDivisionError("portfolio weights sum to zero; cannot normalise")
    return x / abs(s)


def ew(R: np.ndarray) -> np.ndarray:
    n = np.asarray(R).shape[1]
    return np.full(n, 1.0 / n)


def mv(R: np.ndarray) -> np.ndarray:
    mu, Sigma = sample_moments(R)
    x = np.linalg.solve(Sigma, mu)
    return normalise(x)


def min_variance(R: np.ndarray) -> np.ndarray:
    _, Sigma = sample_moments(R)
    ones = np.ones(Sigma.shape[0])
    x = np.linalg.solve(Sigma, ones)
    return x / x.sum()


def vw(market_index: int):
    """The value-weighted market: weight one on the market column, zero elsewhere."""
    def rule(R: np.ndarray) -> np.ndarray:
        w = np.zeros(np.asarray(R).shape[1])
        w[market_index] = 1.0
        return w
    rule.__name__ = "vw"
    return rule


def in_sample_sharpe(R: np.ndarray, rule=mv) -> float:
    """DGU equation (13): the Sharpe ratio of a rule estimated once on the whole sample."""
    mu, Sigma = sample_moments(R)
    w = rule(R)
    return float(w @ mu / np.sqrt(w @ Sigma @ w))


# ---------------------------------------------------------------------------
# Bayes-Stein, DGU section 1.3.2, equations (4) and (5); Jorion (1986)
# ---------------------------------------------------------------------------

def bayes_stein_from_moments(mu: np.ndarray, Sigma_mnm2: np.ndarray, M: int) -> tuple[np.ndarray, np.ndarray, float]:
    """Jorion's predictive moments from a window's mean and its covariance with divisor M - N - 2.

    Returns (mu_bs, Sigma_bs, phi). The mean is shrunk toward the mean return
    of the minimum-variance portfolio by phi (DGU equation 5); the covariance
    is inflated for the uncertainty in the mean, Jorion's predictive variance.
    """
    N = len(mu)
    Sigma_inv_1 = np.linalg.solve(Sigma_mnm2, np.ones(N))
    w_min = Sigma_inv_1 / Sigma_inv_1.sum()
    mu_min = float(mu @ w_min)
    d = mu - mu_min
    dist = float(d @ np.linalg.solve(Sigma_mnm2, d))     # (mu - mu_min 1)' Sigma^-1 (mu - mu_min 1)
    lam = (N + 2) / dist
    phi = lam / (M + lam)                                 # equals (N+2) / ((N+2) + M * dist), DGU equation (5)
    mu_bs = (1.0 - phi) * mu + phi * mu_min
    Sigma_bs = Sigma_mnm2 * (1.0 + 1.0 / (M + lam)) + (lam / (M * (M + 1.0 + lam))) * np.outer(np.ones(N), np.ones(N)) / Sigma_inv_1.sum()
    return mu_bs, Sigma_bs, phi


def bayes_stein_moments(R: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """The predictive mean and covariance of Jorion (1986), as DGU implement them, from a window of returns.

    The sample covariance here divides by M - N - 2 (DGU equation 5), the
    unbiased estimator of the inverse. Returns (mu_bs, Sigma_bs, phi).
    """
    R = np.asarray(R, dtype=float)
    M, N = R.shape
    mu = R.mean(axis=0)
    dev = R - mu
    Sigma = dev.T @ dev / (M - N - 2)
    return bayes_stein_from_moments(mu, Sigma, M)


def bs(R: np.ndarray) -> np.ndarray:
    mu_bs, Sigma_bs, _ = bayes_stein_moments(R)
    return normalise(np.linalg.solve(Sigma_bs, mu_bs))


# ---------------------------------------------------------------------------
# Constrained rules, DGU section 1.5: quadratic programmes with a budget
# ---------------------------------------------------------------------------

def _ridged(Sigma: np.ndarray) -> np.ndarray:
    """Sigma itself when it is positive definite; a tiny ridge keeps a near-singular window solvable."""
    N = Sigma.shape[0]
    try:
        np.linalg.cholesky(Sigma)
        return Sigma
    except np.linalg.LinAlgError:
        return Sigma + 1e-12 * np.trace(Sigma) / N * np.eye(N)


def _cholesky_upper(Sigma: np.ndarray) -> np.ndarray:
    """L' with Sigma = L L', on the ridged matrix of _ridged."""
    return np.linalg.cholesky(_ridged(Sigma)).T


def _budget_qp(Sigma: np.ndarray, mu: np.ndarray, lower: float) -> np.ndarray:
    """argmin w' Sigma w / 2 - mu' w over 1'w = 1 and w >= lower, by an active-set method.

    In v = w - lower 1 the problem is  minimise v' Sigma v / 2 - b' v  over
    1'v = c and v >= 0, with b = mu - lower Sigma 1 and c = 1 - N lower. The
    free set F holds the weights above the bound; at the start it holds the one
    weight on which the whole budget gives the lowest objective. Each round
    solves the equality-constrained problem on F exactly, from its optimality conditions
      Sigma_FF s_F - b_F + lam 1 = 0,   1's_F = c,
    one linear system in s_F and the budget's multiplier lam. If every s_F is
    positive, v = s and the multipliers of the bound weights, g = Sigma v - b + lam,
    are read: a negative g_j says the objective falls when w_j leaves the bound,
    so the most negative one is freed and the round repeats; if none is negative,
    v is the optimum. If some s_F is not positive, v moves toward s only
    as far as the first weight to reach the bound, that weight leaves F, and the
    round repeats. A freed weight is positive in the next solution, so every
    round lowers the objective and the method ends after a finite number of
    rounds; the cap on rounds is a guard that a correct run never reaches.
    """
    Sigma = _ridged(np.asarray(Sigma, dtype=float))
    mu = np.asarray(mu, dtype=float)
    N = Sigma.shape[0]
    c = 1.0 - N * lower
    if c < 0.0:
        raise ValueError(f"no portfolio has {N} weights of at least {lower} that sum to one")
    if c == 0.0:
        return np.full(N, lower)
    ones = np.ones(N)
    b = mu - lower * (Sigma @ ones)
    tol = 10.0 * np.finfo(float).eps * N * (np.abs(Sigma).max() + np.abs(b).max())
    start = int(np.argmin(0.5 * c * c * np.diag(Sigma) - c * b))
    v = np.zeros(N)
    v[start] = c
    free = np.zeros(N, dtype=bool)
    free[start] = True
    for _ in range(50 * N + 50):
        F = np.flatnonzero(free)
        k = len(F)
        K = np.zeros((k + 1, k + 1))
        K[:k, :k] = Sigma[np.ix_(F, F)]
        K[:k, k] = 1.0
        K[k, :k] = 1.0
        sol = np.linalg.solve(K, np.concatenate([b[F], [c]]))
        s = np.zeros(N)
        s[F] = sol[:k]
        lam = sol[k]
        if np.all(s[F] > 0.0):
            v = s
            g = Sigma @ v - b + lam
            bound = np.flatnonzero(~free)
            if bound.size == 0 or g[bound].min() >= -tol:
                return v + lower
            free[bound[np.argmin(g[bound])]] = True
            continue
        hit = F[s[F] <= 0.0]
        ratios = v[hit] / (v[hit] - s[hit])
        alpha = ratios.min()
        if alpha <= 0.0:
            # only a weight freed in the round before can be at the bound here, and a freed weight is positive
            # in exact arithmetic: a zero step means its multiplier was rounding, and the point stands
            return v + lower
        v = v + alpha * (s - v)
        v[hit[ratios <= alpha]] = 0.0
        free &= v > 0.0
    raise RuntimeError("the active-set method did not end within its cap on rounds")


def nonneg_mean_variance(mu: np.ndarray, Sigma: np.ndarray) -> np.ndarray:
    """argmax mu'x - x'Sigma x / 2 over x >= 0, as NNLS: minimise |L'x - L^-1 mu|^2.

    This is DGU's Lagrangian (8) read literally: the non-negativity constraint
    alone, the scale then removed by normalise(). It is kept so that the two
    readings of the equation can be compared (notebook 03); budget_mean_variance
    is the reading that reproduces the paper's tables.
    """
    Lt = _cholesky_upper(Sigma)
    b = np.linalg.solve(Lt.T, mu)           # L^-1 mu
    x, _ = nnls(Lt, b)
    return x


def budget_mean_variance(mu: np.ndarray, Sigma: np.ndarray, gamma: float = C.DGU_RISK_AVERSION) -> np.ndarray:
    """argmax mu'w - gamma w'Sigma w / 2 over w >= 0 and 1'w = 1.

    The budget constraint sits inside the optimisation, so gamma no longer
    cancels: with gamma = 1 and monthly moments the risk term is small against
    the differences in means, and the rule often puts all wealth in the asset
    with the highest estimated mean. That is the "corner solutions with all
    wealth invested in a single asset" of DGU footnote 22, and it is what
    reproduces their Tables 3 to 5 (constants.DGU_CONSTRAINED_BUDGET_INSIDE).
    Solved by _budget_qp as  minimise w' (gamma Sigma) w / 2 - mu' w  over
    1'w = 1 and w >= 0.
    """
    return _budget_qp(gamma * np.asarray(Sigma, dtype=float), mu, 0.0)


def constrained_min_variance(Sigma: np.ndarray, lower: float = 0.0) -> np.ndarray:
    """argmin w'Sigma w over w >= lower, 1'w = 1, by _budget_qp with mu = 0."""
    N = np.asarray(Sigma).shape[0]
    return _budget_qp(Sigma, np.zeros(N), lower)


def mv_c(R: np.ndarray) -> np.ndarray:
    mu, Sigma = sample_moments(R)
    if C.DGU_CONSTRAINED_BUDGET_INSIDE:
        return budget_mean_variance(mu, Sigma)
    return normalise(nonneg_mean_variance(mu, Sigma))


def bs_c(R: np.ndarray) -> np.ndarray:
    mu_bs, Sigma_bs, _ = bayes_stein_moments(R)
    if C.DGU_CONSTRAINED_BUDGET_INSIDE:
        return budget_mean_variance(mu_bs, Sigma_bs)
    return normalise(nonneg_mean_variance(mu_bs, Sigma_bs))


def mv_c_cone(R: np.ndarray) -> np.ndarray:
    """Equation (8) read literally, for the comparison in notebook 03; not a reported rule."""
    mu, Sigma = sample_moments(R)
    return normalise(nonneg_mean_variance(mu, Sigma))


def min_c(R: np.ndarray) -> np.ndarray:
    _, Sigma = sample_moments(R)
    return constrained_min_variance(Sigma, lower=0.0)


def g_min_c(R: np.ndarray) -> np.ndarray:
    """DGU p. 1926: minimum variance with w >= a 1, a = 1/(2N), halfway between min-c and 1/N."""
    _, Sigma = sample_moments(R)
    N = Sigma.shape[0]
    return constrained_min_variance(Sigma, lower=C.DGU_GMINC_LOWER_BOUND_FRACTION / N)


# ---------------------------------------------------------------------------
# The same rules from a window's moments, for the long simulated histories of
# notebook 04, where recomputing the covariance at every month would dominate
# the running time. Each takes (mu, Sigma, M) with Sigma the sample covariance
# with divisor M - 1, and returns the same weights as its window-based twin
# (tests/test_rules_backtest.py checks the equality).
# ---------------------------------------------------------------------------

def _to_mnm2(Sigma: np.ndarray, M: int) -> np.ndarray:
    """Rescale a divisor-(M-1) covariance to divisor M - N - 2, DGU equation (5)."""
    N = Sigma.shape[0]
    return Sigma * (M - 1) / (M - N - 2)


def ew_m(mu, Sigma, M):
    return np.full(len(mu), 1.0 / len(mu))


def mv_m(mu, Sigma, M):
    return normalise(np.linalg.solve(Sigma, mu))


def min_m(mu, Sigma, M):
    x = np.linalg.solve(Sigma, np.ones(len(mu)))
    return x / x.sum()


def bs_m(mu, Sigma, M):
    mu_bs, Sigma_bs, _ = bayes_stein_from_moments(mu, _to_mnm2(Sigma, M), M)
    return normalise(np.linalg.solve(Sigma_bs, mu_bs))


def mv_c_m(mu, Sigma, M):
    if C.DGU_CONSTRAINED_BUDGET_INSIDE:
        return budget_mean_variance(mu, Sigma)
    return normalise(nonneg_mean_variance(mu, Sigma))


def bs_c_m(mu, Sigma, M):
    mu_bs, Sigma_bs, _ = bayes_stein_from_moments(mu, _to_mnm2(Sigma, M), M)
    if C.DGU_CONSTRAINED_BUDGET_INSIDE:
        return budget_mean_variance(mu_bs, Sigma_bs)
    return normalise(nonneg_mean_variance(mu_bs, Sigma_bs))


def min_c_m(mu, Sigma, M):
    return constrained_min_variance(Sigma, lower=0.0)


def g_min_c_m(mu, Sigma, M):
    return constrained_min_variance(Sigma, lower=C.DGU_GMINC_LOWER_BOUND_FRACTION / len(mu))


MOMENT_RULES = {
    "ew": ew_m,
    "mv": mv_m,
    "bs": bs_m,
    "min": min_m,
    "mv-c": mv_c_m,
    "bs-c": bs_c_m,
    "min-c": min_c_m,
    "g-min-c": g_min_c_m,
}


# The registry. vw needs the market column and is built per dataset with vw(index).
RULES = {
    "ew": ew,
    "mv": mv,
    "bs": bs,
    "min": min_variance,
    "mv-c": mv_c,
    "bs-c": bs_c,
    "min-c": min_c,
    "g-min-c": g_min_c,
}
