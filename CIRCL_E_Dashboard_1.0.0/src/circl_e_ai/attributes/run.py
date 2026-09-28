"""Frozen attribute branch orchestration."""
from __future__ import annotations
import numpy as np
from circl_e_ai.contracts.models import AttributeResult
from circl_e_ai.reference.knn import cosine_knn
from .global_ica import compute_global_ica
from .family_ica import compute_family_ica
from .patch import compute_patch_atypicality
from .patch_rank import parent_patch_percentile


def _identity_neighbors(features, discovery, release, k: int = 40) -> dict:
    X = np.asarray(release.assets.reference["identity_X"])
    parents = np.asarray(release.assets.reference["parent_ids"])
    allowed = parents == int(discovery.parent_id)
    ids, _, sims = cosine_knn(features.G_dual, X, k=k, allowed_mask=allowed)
    return {"ids": ids, "similarities": sims}


def run_attributes(features, discovery, release) -> AttributeResult:
    # Attribute coordinates can still be computed for internal diagnostics on a low-support item;
    # publication/scoring policies decide whether they are exposed downstream.
    max_k = max(
        int(release.assets.method_config["global_ica"]["selected_neighbors"]),
        int(release.assets.method_config["family_ica"]["neighbors"]),
        20,
    )
    neigh = _identity_neighbors(features, discovery, release, k=max_k)
    global_ica = compute_global_ica(features, discovery, neigh, release)
    family_ica = compute_family_ica(features, discovery, neigh, release)
    patch = compute_patch_atypicality(features.dense_patch_g16, neigh["ids"], int(discovery.parent_id), release)
    patch["identity_reference_neighbor_ids"] = [int(x) for x in neigh["ids"]]
    patch["percentile_within_parent"] = parent_patch_percentile(
        patch["local_percentile_q99"], int(discovery.parent_id), release
    )
    return AttributeResult(global_ica=global_ica, family_ica=family_ica, patch=patch)
