"""Frozen central semantic/continuous transition interpreter.

Single-image equivalent of the source notebook's mask + precedence logic:
fine (priority 0) -> raw visual (1) -> continuous (2), keyed by
(target_id, redundancy_group). Only CENTRAL and
CENTRAL_WITH_NO_EFFECT_SENSITIVITY rules alter the central profile.
"""
from __future__ import annotations
import math

CENTRAL_POLICIES = {"CENTRAL", "CENTRAL_WITH_NO_EFFECT_SENSITIVITY"}


def _records(obj):
    return obj.to_dict("records") if hasattr(obj, "to_dict") else list(obj or [])


def apply_action(value, action: str):
    if action == "NO_CHANGE": return value
    if action.startswith("SET_"): return int(action.split("_")[1])
    if value is None or (isinstance(value,float) and math.isnan(value)): return value
    if action == "UP_1": return min(4, int(value)+1)
    if action == "DOWN_1": return max(1, int(value)-1)
    raise ValueError(f"Unsupported action: {action}")


def _active_discrete(row, context):
    d=context["discovery"]
    if d.discovery_status == "unknown_mixed" or int(row["parent_id"]) != int(d.parent_id): return False
    if row["stage"] == "fine":
        return d.discovery_status == "reliable_parent_and_fine_group" and d.fine_id is not None and int(row["structure_id"]) == int(d.fine_id)
    if row["stage"] == "raw_visual":
        return d.raw_visual_leaf_id is not None and int(row["structure_id"]) == int(d.raw_visual_leaf_id)
    return False


def _active_continuous(row, context):
    d=context["discovery"]
    if d.discovery_status == "unknown_mixed": return False
    scope=str(row["scope"]); fid=int(row["factor_id"]); wanted=str(row["activation_state"])
    rows = context["attributes"].global_ica if scope == "global" else context["attributes"].family_ica
    for x in rows:
        if x.get("scope") != scope or int(x.get("factor_id",-1)) != fid: continue
        if scope == "family" and int(x.get("parent_id",-1)) != int(row["parent_id"]): continue
        return str(x.get("state")) == wanted
    return False


def active_rules(context, permissions, release, target_kind: str) -> list[dict]:
    sem = _records(release.assets.postmapping["semantic_transition_registry"])
    con = _records(release.assets.postmapping["continuous_transition_registry"])
    rows=[]
    allowed_discrete = permissions["central_rule_ids"] | permissions["sensitivity_rule_ids"]
    for order,r in enumerate(sem):
        if str(r.get("target_kind")) != target_kind or not _active_discrete(r,context): continue
        # Reviewed rule must appear in permission registry for this discrete structure.
        if str(r["rule_id"]) not in allowed_discrete: continue
        q=dict(r); q["_priority"] = 0 if r["stage"]=="fine" else 1; q["_order"]=order; rows.append(q)
    for order,r in enumerate(con):
        if str(r.get("target_kind")) != target_kind or not _active_continuous(r,context): continue
        q=dict(r); q["stage"]="continuous"; q["_priority"]=2; q["_order"]=order; rows.append(q)
    rows.sort(key=lambda r:(r["_priority"],r["_order"]))
    used=set(); out=[]
    for r in rows:
        key=(str(r["target_id"]),str(r.get("redundancy_group")))
        if key in used: continue
        used.add(key); out.append(r)
    return out


def apply_central_transitions(base: dict, context, permissions, release, target_kind: str):
    out=dict(base); applied=[]
    for r in active_rules(context, permissions, release, target_kind):
        if str(r.get("central_policy")) not in CENTRAL_POLICIES: continue
        tid=str(r["target_id"])
        out[tid]=apply_action(out.get(tid),str(r["action"]))
        applied.append({k:r.get(k) for k in ["rule_id","stage","target_kind","target_id","action","central_policy","redundancy_group","anchor_origin","rationale"]})
    return out, applied


def apply_semantic_transitions(base, context, permissions, release):
    return apply_central_transitions(base, context, permissions, release, "criterion")


def apply_continuous_transitions(base, context, permissions, release):
    # Kept for compatibility: central criterion application already merges both
    # discrete and continuous rules with source precedence.
    return apply_central_transitions(base, context, permissions, release, "criterion")
