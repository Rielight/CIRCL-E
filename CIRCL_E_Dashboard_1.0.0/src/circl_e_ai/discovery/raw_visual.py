"""Parent-specific frozen raw-visual leaf inference."""
from __future__ import annotations


def predict_raw_visual(named_views: dict, parent_id: int, release) -> dict:
    cfg = release.assets.method_config["raw_visual_selection_space"]["selected"][str(int(parent_id))]
    mapping = release.assets.reference["raw_global_by_parent_local"]
    if cfg["view"] == "parent_only" or int(cfg["k"]) == 1:
        leaf = mapping.get((int(parent_id), 0))
        if leaf is None:
            raise KeyError(f"No singleton raw leaf for parent={parent_id}")
        return {"raw_visual_leaf_id": int(leaf), "local_visual": 0, "view": "parent_only"}
    entry = release.assets.raw_models[int(parent_id)]
    model = entry["model"] if isinstance(entry, dict) else entry
    remap = entry.get("remap", {}) if isinstance(entry, dict) else release.assets.reference["raw_remap_by_parent"][int(parent_id)]
    view = str(cfg["view"])
    raw_cluster = int(model.predict(named_views[view])[0])
    local_visual = int(remap.get(raw_cluster, remap.get(str(raw_cluster), raw_cluster)))
    leaf = mapping.get((int(parent_id), local_visual))
    if leaf is None:
        raise KeyError(f"No global raw leaf for parent={parent_id} local_visual={local_visual}")
    return {"raw_visual_leaf_id": int(leaf), "local_visual": local_visual, "view": view}
