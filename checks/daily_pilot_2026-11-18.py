"""Design pilot on made-up data only: the size of the variance test on daily pairs with clustered volatility."""
import sys, time
sys.path.insert(0, 'src')
import numpy as np
from bp import paired as P

def test_chunked(r1, r2, block, draws, seed, periods=252, ddof=1, level=0.95, chunk=100):
    rng = np.random.default_rng(seed)
    t = len(r1); scale = P._scale(t, periods, ddof)
    mu1, mu2, g1, g2 = P._moments(r1, r2)
    dl, ds = float(P._delta_log(mu1, mu2, g1, g2)), float(P._delta_sd(mu1, mu2, g1, g2, scale))
    se = P.standard_errors(r1, r2, periods, ddof)
    idx = P.circular_block_indices(t, block, draws, rng)
    n = idx.shape[1]; nb = n // block
    sl, ss = [], []
    for c in range(0, draws, chunk):
        ix = idx[c:c + chunk]; a, b = r1[ix], r2[ix]
        m1, m2 = a.mean(axis=1), b.mean(axis=1); h1, h2 = (a ** 2).mean(axis=1), (b ** 2).mean(axis=1)
        y = np.stack([a - m1[:, None], b - m2[:, None], a ** 2 - h1[:, None], b ** 2 - h2[:, None]], axis=-1)
        zeta = np.sqrt(block) * y.reshape(len(ix), nb, block, 4).mean(axis=2)
        psi = np.einsum("dki,dkj->dij", zeta, zeta) / nb
        gl, gs = P._gradient_log(m1, m2, h1, h2), P._gradient_sd(m1, m2, h1, h2, scale)
        sel = np.sqrt(np.einsum("di,dij,dj->d", gl, psi, gl) / n); ses = np.sqrt(np.einsum("di,dij,dj->d", gs, psi, gs) / n)
        sl.append(np.abs(P._delta_log(m1, m2, h1, h2) - dl) / sel); ss.append(np.abs(P._delta_sd(m1, m2, h1, h2, scale) - ds) / ses)
    sl, ss = np.concatenate(sl), np.concatenate(ss)
    p = (int((sl >= abs(dl) / se["se_log"]).sum()) + 1) / (draws + 1)
    z = float(np.quantile(ss, level)); half = z * se["se_sd"]
    return {"p": p, "diff": ds, "se": se["se_sd"], "z": z, "half": half, "excl": abs(ds) > half}

def garch_pair(n, sd_annual, rho, dof, alpha, beta, rng, burn=1000):
    """Two daily series with equal variances, correlation rho, one common GARCH(1,1) volatility and Student-t shocks."""
    sc = np.sqrt(dof / (dof - 2)); z = rng.standard_t(dof, size=(3, n + burn)) / sc
    omega = 1 - alpha - beta; h = np.empty(n + burn); h[0] = 1.0; mkt = np.empty(n + burn)
    for t in range(n + burn):
        if t: h[t] = omega + alpha * mkt[t - 1] ** 2 + beta * h[t - 1]
        mkt[t] = np.sqrt(h[t]) * z[0, t]
    s = np.sqrt(h); e1 = np.sqrt(rho) * mkt + np.sqrt(1 - rho) * s * z[1]; e2 = np.sqrt(rho) * mkt + np.sqrt(1 - rho) * s * z[2]
    k = sd_annual / np.sqrt(252)
    return k * e1[burn:], k * e2[burn:]

if __name__ == "__main__":
    block, pairs, draws = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]); alpha, beta = float(sys.argv[4]), float(sys.argv[5])
    root = np.random.SeedSequence(20261118); ds, bs = root.spawn(2); drng = np.random.default_rng(ds); brs = bs.spawn(pairs)
    rej = exc = 0; ses = []; zs = []; diffs = []; t0 = time.time()
    for k in range(pairs):
        r1, r2 = garch_pair(11900, 0.0085, 0.99, 5, alpha, beta, drng)
        o = test_chunked(r1, r2, block, draws, brs[k]); rej += o["p"] < 0.05; exc += o["excl"]; ses.append(o["se"]); zs.append(o["z"]); diffs.append(o["diff"])
    print(f"block {block} alpha {alpha} beta {beta}: pairs {pairs} draws {draws} | rejected {rej/pairs:.3f} | interval excludes zero {exc/pairs:.3f} | mean se {np.mean(ses)*1e4:.3f} bp | sd of differences {np.std(diffs)*1e4:.3f} bp | mean critical {np.mean(zs):.2f} | secs {time.time()-t0:.0f}", flush=True)
