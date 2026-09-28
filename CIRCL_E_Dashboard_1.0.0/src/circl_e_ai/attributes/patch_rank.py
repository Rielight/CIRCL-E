"""Parent-relative rank of identity-relative patch percentile used by IRP-C."""
from __future__ import annotations
from .factor_state import empirical_percentile


def parent_patch_percentile(local_percentile_q99: float, parent_id: int, release) -> float:
    ref = release.assets.reference["patch_local_percentile_by_parent"][int(parent_id)]
    return empirical_percentile(float(local_percentile_q99), ref)
