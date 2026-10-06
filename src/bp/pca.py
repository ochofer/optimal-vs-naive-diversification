"""Principal components of a panel of excess returns (notebook 09).

A covariance matrix of N assets holds N(N+1)/2 numbers. Its principal components
are the combinations of assets that account for most of the shared movement,
ordered by how much each explains: the first eigenvector of the covariance matrix
is the direction of largest variance, the second the direction of largest variance
among those uncorrelated with the first, and so on. Each eigenvalue is the variance
of the corresponding component, and the eigenvalues sum to the total variance of
the panel. The functions here return the components with their signs fixed by a
rule (an eigenvector and its negative are the same direction), the share of total
variance each explains, the components' monthly returns (their scores), a stability
measure between two sets of loadings, a parallel analysis against pure noise, and
a rolling view of the first component.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import constants as C


@dataclass
class PCA:
    """Eigenvalues (descending), loadings (one column per component, rows in the order of the assets), variance shares and the asset names."""
    eigenvalues: np.ndarray
    loadings: np.ndarray
    shares: np.ndarray
    assets: list[str]
    months: int

    def frame(self, n: int | None = None) -> pd.DataFrame:
        n = n or len(self.eigenvalues)
        return pd.DataFrame(self.loadings[:, :n], index=self.assets, columns=[f"PC{k + 1}" for k in range(n)])


def covariance(excess: pd.DataFrame) -> np.ndarray:
    """The sample covariance of the columns (denominator T-1), on the months with no missing value."""
    X = excess.dropna().to_numpy(dtype=float)
    return np.cov(X, rowvar=False, ddof=1)


def fit(excess: pd.DataFrame, reference: pd.Series | np.ndarray | None = None) -> PCA:
    """Principal components of the covariance of `excess` (months by assets).

    reference: a weight vector over the assets (the benchmark's weights, for
    example) used by the sign rule: each component is flipped, if needed, so
    that its loading on the reference portfolio (loadings dot reference) is
    positive. With no reference the rule uses 1/N weights, so that a
    component whose loadings are mostly positive keeps them positive.
    """
    clean = excess.dropna()
    Sigma = np.cov(clean.to_numpy(dtype=float), rowvar=False, ddof=1)
    vals, vecs = np.linalg.eigh(Sigma)               # ascending
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    vals = np.clip(vals, 0.0, None)                   # rounding can give -1e-20
    ref = np.ones(Sigma.shape[0]) / Sigma.shape[0] if reference is None else np.asarray(reference, dtype=float)
    for k in range(vecs.shape[1]):
        if vecs[:, k] @ ref < 0:
            vecs[:, k] = -vecs[:, k]
    return PCA(eigenvalues=vals, loadings=vecs, shares=vals / vals.sum(), assets=list(excess.columns), months=len(clean))


def scores(excess: pd.DataFrame, pca: PCA, n: int | None = None) -> pd.DataFrame:
    """The components' scores: their monthly returns, the demeaned excess returns projected on the loadings."""
    n = n or len(pca.eigenvalues)
    clean = excess.dropna()
    X = clean.to_numpy(dtype=float)
    X = X - X.mean(axis=0)
    S = X @ pca.loadings[:, :n]
    return pd.DataFrame(S, index=clean.index, columns=[f"PC{k + 1}" for k in range(n)])


def loading_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """The absolute correlation between two loading vectors: 1 means the same combination of assets, 0 means unrelated."""
    return float(abs(np.corrcoef(np.asarray(a, dtype=float), np.asarray(b, dtype=float))[0, 1]))


def explained_in_window(excess_window: pd.DataFrame, loadings: np.ndarray, n: int) -> float:
    """The share of a window's total variance that the first n given loading vectors explain inside that window.

    The share of the window's own components is the largest possible for n
    components; a lower share for loadings estimated elsewhere measures how much
    the structure moved.
    """
    Sigma = covariance(excess_window)
    L = loadings[:, :n]
    Q, _ = np.linalg.qr(L)                            # orthonormal basis of the same subspace
    return float(np.trace(Q.T @ Sigma @ Q) / np.trace(Sigma))


def parallel_analysis(excess: pd.DataFrame, draws: int = C.PCA_PARALLEL_DRAWS, percentile: float = C.PCA_PARALLEL_PERCENTILE,
                      seed: int = C.PCA_PARALLEL_SEED) -> pd.DataFrame:
    """How many components exceed what pure noise would produce.

    Draws `draws` panels of independent normal returns with the same number of
    months and assets and the same variances as the data (so no shared movement
    at all), takes the eigenvalues of each, and reports for each component the
    data's eigenvalue, the noise percentile and whether the data exceed it. The
    count of components above the bar is the number of components that carry
    structure the noise cannot imitate.
    """
    clean = excess.dropna()
    X = clean.to_numpy(dtype=float)
    T, N = X.shape
    sd = X.std(axis=0, ddof=1)
    rng = np.random.default_rng(seed)
    noise_vals = np.empty((draws, N))
    for d in range(draws):
        Z = rng.standard_normal((T, N)) * sd
        noise_vals[d] = np.sort(np.linalg.eigvalsh(np.cov(Z, rowvar=False, ddof=1)))[::-1]
    bar = np.percentile(noise_vals, percentile, axis=0)
    data_vals = np.sort(np.linalg.eigvalsh(np.cov(X, rowvar=False, ddof=1)))[::-1]
    out = pd.DataFrame({"eigenvalue": data_vals, f"noise_p{int(percentile)}": bar, "above_noise": data_vals > bar},
                       index=[f"PC{k + 1}" for k in range(N)])
    out.attrs["n_above_noise"] = int(out["above_noise"].to_numpy().cumprod().sum())   # the leading run of components above the bar
    return out


def rolling_first_component(excess: pd.DataFrame, benchmark_excess: pd.Series, window: int = C.EXT_ESTIMATION_WINDOW,
                            reference: np.ndarray | None = None) -> pd.DataFrame:
    """For every window of `window` months ending at each month: the first component's variance share and its correlation with the benchmark's excess return inside the window."""
    rows = []
    idx = excess.index
    bench = benchmark_excess.reindex(idx)
    for end in range(window - 1, len(idx)):
        sl = excess.iloc[end - window + 1: end + 1]
        if sl.isna().any().any():
            continue
        p = fit(sl, reference)
        s1 = scores(sl, p, 1)["PC1"]
        rows.append({"month": idx[end], "pc1_share": float(p.shares[0]), "pc1_corr_benchmark": float(np.corrcoef(s1, bench.iloc[end - window + 1: end + 1])[0, 1]),
                     "first_five_share": float(p.shares[:5].sum())})
    return pd.DataFrame(rows).set_index("month")
