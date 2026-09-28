"""Exact frozen numerical discovery orchestration for a new image."""
from __future__ import annotations
from circl_e_ai.contracts.models import DiscoveryResult
from .root import predict_root
from .fine import predict_fine
from .raw_visual import predict_raw_visual
from .support import parent_assignment_support, fine_assignment_support
from .status import resolve_discovery_status


def run_discovery(features, release) -> DiscoveryResult:
    parent = int(predict_root(features.named_views, release))
    root_view = release.assets.method_config["root_selection_space"]["selected_view"]
    parent_support = parent_assignment_support(features.named_views[root_view], parent, release)
    reliability = float(release.assets.support_models["parent_operational_reliability"].get(parent, 0.0))

    fine = predict_fine(features.named_views, parent, release)
    fine_id = fine["fine_id"]
    fine_support = None
    if fine_id is not None:
        fine_support = fine_assignment_support(features.named_views[fine["view"]], parent, fine_id, release)

    raw = predict_raw_visual(features.named_views, parent, release)
    status = resolve_discovery_status(
        parent, parent_support, reliability, fine_id, fine_support, residual_threshold=0.85
    )
    return DiscoveryResult(
        provisional_parent_id=parent,
        parent_id=parent,
        parent_support=parent_support,
        fine_id=int(fine_id) if fine_id is not None else None,
        fine_support=fine_support,
        raw_visual_leaf_id=int(raw["raw_visual_leaf_id"]),
        discovery_status=status,
    )
