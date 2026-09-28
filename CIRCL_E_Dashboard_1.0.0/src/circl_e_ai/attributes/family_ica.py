"""Frozen parent-local family ICA projection from high-resolution foreground concepts."""
from __future__ import annotations
import numpy as np
from .residuals import identity_neighbor_residual_new
from .factor_state import factor_state


def compute_family_ica(features, discovery, identity_neighbors, release) -> list[dict]:
    pid = int(discovery.parent_id)
    model = release.assets.family_ica.get(pid)
    post = release.assets.family_ica_postmap.get(pid)
    if model is None or post is None:
        return []
    k = int(release.assets.method_config["family_ica"]["neighbors"])
    ids = identity_neighbors["ids"][:k]
    sims = identity_neighbors["similarities"][:k]
    ref = release.assets.reference
    residual = identity_neighbor_residual_new(
        features.HFG_hires,
        np.asarray(ref["hist512_hires_fg"])[ids],
        sims,
        ref["hist512_hires_parent_mean"].get(pid),
        ref["hist512_hires_global_mean"],
        k=k,
    )
    raw = model.transform(residual.reshape(1, -1)).astype(np.float32)
    scores = (raw @ np.asarray(post, np.float32))[0]
    return [factor_state("family", pid, int(fid), float(score), release) for fid, score in enumerate(scores)]
