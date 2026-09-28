"""Identity-relative local visual atypicality; no heatmap rendering is required."""
from __future__ import annotations
import numpy as np
from circl_e_ai.features.math import normalize_rows_l2


def compute_patch_atypicality(dense_patch_g16, neighbor_ids, parent_id: int, release) -> dict:
    ref = release.assets.reference
    ids = np.asarray(neighbor_ids, int)
    local_k = int(release.assets.method_config["patch"]["reference_neighbors"])
    proto_ids = ids[:local_k]
    prot = np.asarray(release.assets.patch_prototypes)
    if len(proto_ids):
        reference_prototypes = prot[proto_ids].reshape(-1, prot.shape[-1]).astype(np.float32)
    else:
        # This should be unreachable for a valid parent bank, but keep a deterministic fallback.
        parent_rows = np.flatnonzero(np.asarray(ref["parent_ids"]) == int(parent_id))
        reference_prototypes = prot[parent_rows[:1]].reshape(-1, prot.shape[-1]).astype(np.float32)
    q = normalize_rows_l2(np.asarray(dense_patch_g16, np.float32))
    rp = normalize_rows_l2(reference_prototypes)
    deviations = 1.0 - np.max(q @ rp.T, axis=1)
    q90, q95, q99 = [float(np.quantile(deviations, p)) for p in (0.90, 0.95, 0.99)]
    mean, std = float(deviations.mean()), float(deviations.std())

    norm_ids = ids[:max(20, local_k)]
    patch_q99_ref = np.asarray(ref["patch_q99"], float)
    if len(norm_ids):
        vals = patch_q99_ref[norm_ids]
    else:
        vals = patch_q99_ref[np.asarray(ref["parent_ids"]) == int(parent_id)]
    vals = vals[np.isfinite(vals)]
    med = float(np.median(vals)) if len(vals) else 0.0
    mad = float(np.median(np.abs(vals - med))) if len(vals) else 0.0
    local_z = float((q99 - med) / max(1.4826 * mad, 1e-4))
    local_pct = float((1 + np.count_nonzero(vals <= q99)) / (len(vals) + 1)) if len(vals) else float("nan")
    return {
        "q90": q90, "q95": q95, "q99": q99, "mean": mean, "std": std,
        "local_z_q99": local_z, "local_percentile_q99": local_pct,
        "reference_neighbor_ids": proto_ids.tolist(),
    }
