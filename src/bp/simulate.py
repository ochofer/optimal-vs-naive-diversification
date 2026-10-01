"""
DGU's simulated market, section 5.1 (pp. 1941-1942), with an optional
fat-tailed version that the paper does not run.

One factor. N risky assets: the factor portfolio itself plus N - 1 assets
whose excess returns follow R = alpha + beta R_f + e, with alpha = 0, betas
evenly spread between 0.5 and 1.5, and independent noise whose annual
volatility is drawn once per asset, uniformly between 10% and 30%, so the
cross-sectional average idiosyncratic volatility is 20%. The factor's excess
return is normal with annual mean 8% and standard deviation 16%. Everything
is monthly, i.i.d., normal. The paper draws T = 24,000 months once and runs
every rule through that one simulated history.

Because the true mean and covariance are known here, the tangency portfolio
can be held as a benchmark ("mv (true)" in Table 6). With alpha = 0 in a
one-factor model the tangency portfolio is the factor itself, so its Sharpe
ratio is the factor's, 0.08 / 0.16 a year, about 0.144 a month.

Fat tails (notebook 05). With dof set, every shock is multiplied by one
scale factor per month, sqrt((dof - 2) / W) with W chi-squared on dof degrees
of freedom, which turns the normal shocks into multivariate Student-t shocks
with the same mean and covariance: E[(dof - 2) / W] = 1. The normal shocks
are the same draws as the normal market's, so the two markets are paired
month by month and differ only in the tails.

Volatility clustering (notebook 06). With garch=True, each shock series (the
factor's and every asset's own) is multiplied by its own GARCH(1,1) scale,
s_t = sqrt(h_t) with h_t = omega + alpha (s_{t-1} z_{t-1})^2 + beta h_{t-1}
on the standardised shock z, and omega = 1 - alpha - beta so that the
unconditional variance of the scaled shock is one. A large shock raises next
month's volatility, and the rise decays at the rate alpha + beta. Because the
factor's volatility and each asset's own move separately, the correlations
between assets change through time: high when the factor is volatile, low
when it is quiet. The unconditional mean and covariance are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import constants as C


@dataclass
class Market:
    N: int
    betas: np.ndarray          # length N, first entry 1.0 for the factor itself
    idio_var: np.ndarray       # monthly idiosyncratic variance per asset, 0 for the factor
    mu: np.ndarray             # true monthly excess means
    Sigma: np.ndarray          # true monthly covariance
    returns: np.ndarray        # (T, N) simulated monthly excess returns
    seed: int
    dof: float | None = None   # Student-t degrees of freedom of the shocks; None for normal
    garch: bool = False        # True when the shocks carry GARCH(1,1) volatility
    scales: np.ndarray | None = None   # (T, N) volatility multipliers applied to the shocks, when any

    @property
    def true_tangency_weights(self) -> np.ndarray:
        x = np.linalg.solve(self.Sigma, self.mu)
        return x / abs(x.sum())


def build_market(N: int, T: int = C.SIM_T, seed: int = C.SIM_SEED, dof: float | None = None,
                 garch: bool = False) -> Market:
    """One simulated history. The factor's returns depend on the seed only, so the
    three universes (N = 10, 25, 50) share it, as Table 6's identical "mv (true)"
    column across N implies; the idiosyncratic volatilities and shocks depend on
    the seed and on N. With dof set, the shocks are Student-t with that many
    degrees of freedom, scaled to the same covariance; the scale draws depend on
    the seed and on dof, and are shared across N like the factor. With garch
    set, each shock series carries its own GARCH(1,1) volatility. One relaxation
    at a time: dof and garch cannot both be set."""
    if dof is not None and dof <= 2:
        raise ValueError("dof must exceed 2 for the variance to exist")
    if dof is not None and garch:
        raise ValueError("one relaxation at a time: set dof or garch, not both")
    rng_factor = np.random.default_rng([seed, 0])
    rng = np.random.default_rng([seed, N])
    mu_f = C.SIM_FACTOR_MEAN_ANNUAL / 12.0
    sd_f = C.SIM_FACTOR_SD_ANNUAL / np.sqrt(12.0)
    lo, hi = C.SIM_BETA_RANGE
    betas = np.concatenate([[1.0], np.linspace(lo, hi, N - 1)])
    vlo, vhi = C.SIM_IDIO_VOL_RANGE
    idio_sd_annual = np.concatenate([[0.0], rng.uniform(vlo, vhi, size=N - 1)])
    idio_var = (idio_sd_annual / np.sqrt(12.0)) ** 2
    mu = C.SIM_ALPHA + betas * mu_f
    Sigma = sd_f**2 * np.outer(betas, betas) + np.diag(idio_var)
    f_shock = rng_factor.normal(0.0, sd_f, size=T)
    eps = rng.normal(0.0, np.sqrt(idio_var), size=(T, N))
    eps[:, 0] = 0.0
    scales = None
    if dof is not None:
        rng_scale = np.random.default_rng([seed, 1_000_000 + int(round(dof * 1000))])
        scale = np.sqrt((dof - 2.0) / rng_scale.chisquare(dof, size=T))
        f_shock = scale * f_shock
        eps = scale[:, None] * eps
        scales = np.repeat(scale[:, None], N, axis=1)
    if garch:
        # standardised shocks: the factor's in column 0 (the factor asset has no idiosyncratic shock),
        # each asset's own in columns 1 to N-1
        z = np.empty((T, N))
        z[:, 0] = f_shock / sd_f
        z[:, 1:] = eps[:, 1:] / np.sqrt(idio_var[1:])
        scales = garch_scales(z, C.SIM_GARCH_ALPHA, C.SIM_GARCH_BETA)
        f_shock = scales[:, 0] * f_shock
        eps[:, 1:] = scales[:, 1:] * eps[:, 1:]
    f = mu_f + f_shock
    returns = C.SIM_ALPHA + np.outer(f, betas) + eps
    return Market(N=N, betas=betas, idio_var=idio_var, mu=mu, Sigma=Sigma, returns=returns, seed=seed,
                  dof=dof, garch=garch, scales=scales)


def garch_scales(z: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """GARCH(1,1) volatility multipliers for standardised shocks z of shape (T, K), one process per column.

    h_t = omega + alpha (s_{t-1} z_{t-1})^2 + beta h_{t-1}, s_t = sqrt(h_t), with
    omega = 1 - alpha - beta so that the unconditional variance of s_t z_t is one;
    h_0 is set to that unconditional value.
    """
    if not 0 <= alpha and 0 <= beta and alpha + beta < 1:
        raise ValueError("need alpha, beta >= 0 and alpha + beta < 1")
    omega = 1.0 - alpha - beta
    T, K = z.shape
    h = np.empty((T, K))
    h[0] = 1.0
    for t in range(1, T):
        h[t] = omega + alpha * h[t - 1] * z[t - 1] ** 2 + beta * h[t - 1]
    return np.sqrt(h)


def autocorrelation(x: np.ndarray, lag: int = 1) -> float:
    """Sample autocorrelation of a series at the given lag."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    return float(np.sum(x[lag:] * x[:-lag]) / np.sum(x * x))


def excess_kurtosis(x: np.ndarray) -> float:
    """Sample kurtosis minus 3; zero for a normal distribution."""
    x = np.asarray(x, dtype=float)
    z = (x - x.mean()) / x.std(ddof=0)
    return float(np.mean(z**4) - 3.0)
