"""Parent-conditional validated fine inference using frozen KMeans/remap tables."""
from __future__ import annotations


def predict_fine(named_views: dict, parent_id: int, release) -> dict:
    cfg = release.assets.method_config["fine_selection_space"]["selected"].get(str(int(parent_id)))
    if not cfg or not cfg.get("deployed", False):
        return {"status": "NOT_EXPOSED", "fine_id": None, "local_child": None, "view": None}
    entry = release.assets.fine_models[int(parent_id)]
    model = entry["model"] if isinstance(entry, dict) else entry
    remap = entry.get("remap", {}) if isinstance(entry, dict) else release.assets.reference["fine_remap_by_parent"][int(parent_id)]
    view = str(cfg["view"])
    x = named_views[view]
    raw_cluster = int(model.predict(x)[0])
    local_child = int(remap.get(raw_cluster, remap.get(str(raw_cluster), raw_cluster)))
    accepted = {int(v) for v in cfg.get("accepted_local", [])}
    if local_child not in accepted:
        return {"status": "REJECTED_CHILD", "fine_id": None, "local_child": local_child, "view": view}
    mapping = release.assets.reference["fine_global_by_parent_local"]
    fine_id = mapping.get((int(parent_id), local_child))
    if fine_id is None:
        raise KeyError(f"No global validated fine ID for parent={parent_id} local_child={local_child}")
    return {"status": "CANDIDATE", "fine_id": int(fine_id), "local_child": local_child, "view": view}
