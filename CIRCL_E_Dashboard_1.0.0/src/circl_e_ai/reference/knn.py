"""Exact brute-force cosine reference search.

The outline intentionally starts with exact NumPy search. Approximate indexes can
be introduced only after parity tests show they do not change routing/state.
"""
from __future__ import annotations
import numpy as np


def _rows_l2(x, eps=1e-12):
    a = np.asarray(x, dtype=np.float32)
    if a.ndim == 1:
        a = a[None, :]
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), eps)


def cosine_knn(query, reference, k: int, allowed_mask=None):
    """Return ordered reference row indices, distances and similarities."""
    q = _rows_l2(query)[0]
    x = _rows_l2(reference)
    ids = np.arange(len(x))
    if allowed_mask is not None:
        m = np.asarray(allowed_mask, dtype=bool)
        x, ids = x[m], ids[m]
    if len(x) == 0:
        return np.array([], int), np.array([], float), np.array([], float)
    sims = np.clip(x @ q, -1.0, 1.0)
    order = np.argsort(-sims, kind="stable")[: min(int(k), len(sims))]
    chosen_ids = ids[order]
    chosen_sims = sims[order]
    return chosen_ids, 1.0 - chosen_sims, chosen_sims


def weighted_vote_features(query, reference_X, reference_y, k: int = 15):
    """Notebook-compatible routed label and 5 assignment-support features.

    Similarity for voting is ``max(cosine_similarity, 0)``. Every neighbor also
    receives a 1e-6 vote floor. Returned features are ordered exactly as the
    source calibrator expects: support, margin, nn1, nn5, density.
    """
    ids, _, sims_raw = cosine_knn(query, reference_X, k=k)
    if len(ids) == 0:
        raise ValueError("empty reference bank")
    y = np.asarray(reference_y)[ids]
    sims = np.maximum(sims_raw, 0.0)
    labels = np.unique(y)
    votes = {lab: float(sims[y == lab].sum() + 1e-6 * np.count_nonzero(y == lab)) for lab in labels}
    # Source `score` dict is constructed from np.unique(labs), which is numeric-ascending;
    # Python sort is stable and sorts by vote only. Therefore exact vote ties retain
    # numeric label order. Do not use string ordering (e.g. "10" < "2").
    ordered = sorted(votes.items(), key=lambda kv: -kv[1])
    routed = ordered[0][0]
    total = max(sum(votes.values()), 1e-12)
    top = ordered[0][1]
    second = ordered[1][1] if len(ordered) > 1 else 0.0
    support = top / total
    margin = (top - second) / total if len(ordered) > 1 else 1.0
    nn1 = float(sims[0])
    nn5 = float(np.mean(sims[: min(5, len(sims))]))
    density = float(np.mean(sims))
    return routed, np.asarray([support, margin, nn1, nn5, density], dtype=np.float32), ids.tolist()
