"""Semantic permission registry interpreter.

The permission registry is a runtime guard over reviewed discrete semantic links.
It prevents a mapped semantic label from implicitly becoming a scoring rule.
"""
from __future__ import annotations
import ast, json


def _records(obj):
    return obj.to_dict("records") if hasattr(obj, "to_dict") else list(obj or [])


def _list(v):
    if isinstance(v, list): return v
    if v is None: return []
    if isinstance(v, str):
        for fn in (json.loads, ast.literal_eval):
            try:
                x=fn(v)
                return list(x) if isinstance(x, (list,tuple)) else []
            except Exception: pass
    return []


def permitted_rules(context, release) -> dict:
    rows = _records(release.assets.postmapping["semantic_permission_registry"])
    d = context["discovery"]
    selected = []
    if d.discovery_status == "reliable_parent_and_fine_group" and d.fine_id is not None:
        selected.append(("fine", int(d.fine_id)))
    if d.discovery_status != "unknown_mixed" and d.raw_visual_leaf_id is not None:
        selected.append(("raw_visual", int(d.raw_visual_leaf_id)))

    central, sensitivity, issues, matched = set(), set(), [], []
    for stage, sid in selected:
        rr = [r for r in rows if str(r.get("stage")) == stage and int(r.get("structure_id")) == sid]
        if not rr:
            issues.append(f"NO_PERMISSION_ROW:{stage}:{sid}")
            continue
        row = rr[0]; matched.append(row)
        c = set(_list(row.get("central_effect_rule_ids")))
        s = set(_list(row.get("sensitivity_rule_ids")))
        central |= c; sensitivity |= s
        if bool(row.get("nuisance_zero_effect_required")) and (c or s):
            issues.append(f"NUISANCE_NONZERO_EFFECT:{stage}:{sid}")
    return {
        "central_rule_ids": central,
        "sensitivity_rule_ids": sensitivity,
        "matched_rows": matched,
        "issues": issues,
    }
