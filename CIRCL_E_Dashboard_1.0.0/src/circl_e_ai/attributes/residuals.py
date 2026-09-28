"""Reference-relative residuals for ICA."""
import numpy as np


def identity_neighbor_residual_new(query_hist, neighbor_hist, neighbor_sim, parent_mean, global_mean, k: int):
    """Notebook-compatible single-query log residual."""
    ns = np.asarray(neighbor_hist, np.float32)[:k]
    ss = np.asarray(neighbor_sim, np.float32)[:k]
    if len(ns) < max(3, k // 3):
        mu = np.asarray(parent_mean if parent_mean is not None else global_mean, np.float32)
    else:
        w = np.exp((ss - ss.max()) / 0.07)
        w /= max(float(w.sum()), 1e-12)
        mu = (ns * w[:, None]).sum(0)
    q = np.asarray(query_hist, np.float32)
    return np.clip(np.log(q + 1e-4) - np.log(mu + 1e-4), -4, 4)
