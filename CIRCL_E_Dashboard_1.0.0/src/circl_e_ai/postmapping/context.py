"""Assemble immutable single-image inputs for post-mapping."""
from __future__ import annotations
from circl_e_ai.discovery.relative_support import parent_support_relative_state


def _global_factor_state(attributes, factor_id: int):
    for row in attributes.global_ica:
        if int(row.get("factor_id", -1)) == int(factor_id):
            return row.get("state")
    return None


def build_context(reference, discovery, attributes, semantics, release) -> dict:
    rel = parent_support_relative_state(
        discovery.parent_support.score,
        discovery.parent_id,
        discovery.discovery_status,
        release,
    )
    return {
        "reference": reference,
        "discovery": discovery,
        "attributes": attributes,
        "semantics": semantics,
        "release_id": release.manifest.release_id,
        "parent_id": discovery.parent_id,
        "fine_id": discovery.fine_id,
        "raw_visual_leaf_id": discovery.raw_visual_leaf_id,
        "discovery_status": discovery.discovery_status,
        "relative_support_state": rel["state"],
        "parent_support_percentile_within_parent": rel["percentile"],
        "patch_atypicality_percentile_within_parent": attributes.patch.get("percentile_within_parent"),
        "global_factor_11_state": _global_factor_state(attributes, 11),
    }
