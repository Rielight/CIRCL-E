"""Shared deterministic numerical transforms."""
from __future__ import annotations
import numpy as np


def normalize_rows_l2(x, eps: float = 1e-12):
    a = np.asarray(x, np.float32)
    if a.ndim == 1:
        a = a[None, :]
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), eps)


def apply_npz_transform_raw(x, z):
    """PCA/alpha transform without final row normalization (used by concept patch descriptors)."""
    y = (np.asarray(x, np.float32) - z["mean"]) @ z["components"].T
    alpha = float(z["alpha"]) if "alpha" in z else 0.0
    if alpha:
        y *= np.power(np.maximum(z["explained_variance"], 1e-5), -0.5 * alpha)
    return y.astype(np.float32)


def apply_npz_transform(x, z):
    return normalize_rows_l2(apply_npz_transform_raw(x, z))


def weighted_feature_concat(a, b, wa: float, wb: float):
    return normalize_rows_l2(np.c_[
        np.sqrt(float(wa)) * normalize_rows_l2(a),
        np.sqrt(float(wb)) * normalize_rows_l2(b),
    ])
