"""Frozen criterion evidence-anchor resolution for one inferred item.

No web access or source mutation occurs here. The reviewed claim-level evidence map
is a release artifact. Runtime only selects the parent rows and exposes provenance.
"""
from __future__ import annotations
import ast, json, math


def _none(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def _parse(v, default):
    if _none(v):
        return default
    if isinstance(v, (list, dict)):
        return v
    if not isinstance(v, str):
        return v
    s = v.strip()
    if not s:
        return default
    for fn in (json.loads, ast.literal_eval):
        try:
            return fn(s)
        except Exception:
            pass
    return default


def _records(obj):
    if hasattr(obj, "to_dict"):
        return obj.to_dict("records")
    return list(obj or [])


def resolve_criterion_anchors(context, release) -> dict:
    pid = int(context["parent_id"])
    rows = [dict(r) for r in _records(release.assets.postmapping["criterion_evidence_map"])
            if int(r["parent_id"]) == pid]
    criteria = {}
    metadata = {}
    for r in rows:
        cid = str(r["criterion_id"])
        ref = None if _none(r.get("reference_level")) else int(r["reference_level"])
        criteria[cid] = ref
        metadata[cid] = {
            "parent_id": pid,
            "score_dimension": r.get("score_dimension"),
            "semantic_key": r.get("semantic_key"),
            "reference_level": ref,
            "allowed_levels": _parse(r.get("allowed_levels"), []),
            "anchor_origin": r.get("anchor_origin"),
            "evidence_strength": r.get("evidence_strength"),
            "source_ids": _parse(r.get("source_ids"), []),
            "source_roles": _parse(r.get("source_roles"), {}),
            "support_logic": r.get("support_logic"),
            "review_status": r.get("review_status"),
            "support_review_status": r.get("support_review_status"),
            "transfer_risk": r.get("transfer_risk"),
            "rationale": r.get("rationale"),
            "whole_device_reuse_applicability": r.get("whole_device_reuse_applicability"),
        }
    applicability = next((m.get("whole_device_reuse_applicability") for m in metadata.values()
                          if m.get("whole_device_reuse_applicability")), None)
    return {
        "criteria": criteria,
        "metadata": metadata,
        "rows": rows,
        "whole_device_reuse_applicability": applicability,
    }
