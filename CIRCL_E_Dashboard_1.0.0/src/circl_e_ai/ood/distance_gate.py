"""Frozen OOD/reference-conformity evaluation."""
from __future__ import annotations
import numpy as np
from circl_e_ai.contracts.models import ReferenceGateResult
from circl_e_ai.reference.knn import cosine_knn
from circl_e_ai.ood.policy import classify_reference_state


def _mean_knn_distance(query, X, k):
    _, distances, _ = cosine_knn(query, X, k=k)
    return float(np.mean(distances)) if len(distances) else None


def _upper_empirical_percentile(value, frozen_values):
    """Insertion-style CDF for a distance where larger is less reference-like."""
    if value is None:
        return None
    ref = np.asarray(frozen_values, dtype=float)
    ref = ref[np.isfinite(ref)]
    if not len(ref):
        return None
    # Smoothed empirical CDF; query itself contributes one pseudo-count.
    return float((1 + np.count_nonzero(ref <= value)) / (len(ref) + 1))


def evaluate_reference_state(root_vector, provisional_parent: int, release) -> ReferenceGateResult:
    """Evaluate new image against the frozen reference geometry; never fit here."""
    ood = release.assets.ood
    k = int(ood["k"])
    global_d = _mean_knn_distance(root_vector, ood["reference_X"], k)
    mask = np.asarray(ood["parent_ids"]) == int(provisional_parent)
    parent_d = _mean_knn_distance(root_vector, np.asarray(ood["reference_X"])[mask], k)
    # Global kNN distance is measured against the whole reference bank, but its
    # percentile is normalized within the provisional parent. This prevents
    # sparse/heterogeneous parents from being systematically labeled OOD merely
    # because their legitimate reference rows live farther from the global bank.
    parent_mask = np.asarray(ood["parent_ids"]) == int(provisional_parent)
    global_ref_dist = np.asarray(ood["loo_global_distances"])[parent_mask]
    global_pct = _upper_empirical_percentile(global_d, global_ref_dist)
    parent_ref_dist = ood["loo_parent_distances_by_parent"][int(provisional_parent)]
    parent_pct = _upper_empirical_percentile(parent_d, parent_ref_dist)
    metrics = {
        "global_distance": global_d,
        "global_percentile": global_pct,
        "parent_distance": parent_d,
        "parent_percentile": parent_pct,
    }
    state, reasons = classify_reference_state(metrics, ood["policy"])
    return ReferenceGateResult(state=state, reasons=reasons, **metrics)
