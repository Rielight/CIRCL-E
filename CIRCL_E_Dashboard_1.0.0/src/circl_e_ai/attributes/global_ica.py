"""Frozen global ICA projection from identity-relative 512-concept residuals."""
from __future__ import annotations
import numpy as np
from .residuals import identity_neighbor_residual_new
from .factor_state import factor_state


def compute_global_ica(features, discovery, identity_neighbors, release) -> list[dict]:
    k = int(release.assets.method_config["global_ica"]["selected_neighbors"])
    ids = identity_neighbors["ids"][:k]
    sims = identity_neighbors["similarities"][:k]
    ref = release.assets.reference
    residual = identity_neighbor_residual_new(
        features.HSOFT,
        np.asarray(ref["hist512_base"])[ids],
        sims,
        ref["hist512_base_parent_mean"].get(int(discovery.parent_id)),
        ref["hist512_base_global_mean"],
        k=k,
    )
    raw = release.assets.global_ica.transform(residual.reshape(1, -1)).astype(np.float32)
    scores = (raw @ np.asarray(release.assets.global_ica_postmap, np.float32))[0]
    out = []
    for fid, score in enumerate(scores):
        out.append(factor_state("global", None, int(fid), float(score), release))
    return out
