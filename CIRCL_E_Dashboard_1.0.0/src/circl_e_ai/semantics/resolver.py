"""Frozen numerical structures/attributes -> typed reviewed semantic assertions."""
from __future__ import annotations
from .registry import load_semantic_registries


def _structure_assertion(row, source_type, source_id, *, operationally_mapped: bool):
    rec = dict(row)
    rec.update({
        "source_structure": source_type,
        "source_id": int(source_id),
        "semantic_layer": "operational_structure" if operationally_mapped else "descriptive_provenance",
        "operationally_mapped": bool(operationally_mapped),
    })
    return rec


def resolve_semantics(discovery, attributes, release) -> list[dict]:
    regs = load_semantic_registries(release)
    out = []
    pid = int(discovery.parent_id)

    # Parent meaning is retained internally even if routing later abstains; publication_filter controls exposure.
    for r in regs["structure"]:
        if r.get("structure_type") == "parent" and int(r.get("structure_id")) == pid:
            out.append(_structure_assertion(
                r, "parent", pid, operationally_mapped=discovery.discovery_status != "unknown_mixed"
            ))

    if discovery.discovery_status == "reliable_parent_and_fine_group" and discovery.fine_id is not None:
        for r in regs["structure"]:
            if r.get("structure_type") == "fine" and int(r.get("structure_id")) == int(discovery.fine_id):
                out.append(_structure_assertion(r, "fine", int(discovery.fine_id), operationally_mapped=True))

    # Stage-2 always retains raw-visual annotation as descriptive provenance/evidence,
    # even when operational parent/fine semantics abstain. It is never silently
    # merged into the mapped_* operational fields.
    if discovery.raw_visual_leaf_id is not None:
        for r in regs["structure"]:
            if r.get("structure_type") == "raw_visual" and int(r.get("structure_id")) == int(discovery.raw_visual_leaf_id):
                out.append(_structure_assertion(
                    r, "raw_visual", int(discovery.raw_visual_leaf_id), operationally_mapped=False
                ))

    # Only reviewed accepted continuous attributes become semantic attributes. Other stable factors stay numerical/audit-only.
    factor_rows = regs["factors"]
    for fr in list(attributes.global_ica) + list(attributes.family_ica):
        scope, fid, fpid = fr["scope"], int(fr["factor_id"]), fr.get("parent_id")
        for r in factor_rows:
            rp = r.get("parent_id")
            parent_match = (scope == "global" and rp is None) or (scope == "family" and rp is not None and int(rp) == int(fpid))
            if r.get("scope") == scope and int(r.get("factor_id")) == fid and parent_match:
                if r.get("status") != "accepted_attribute":
                    break
                state = fr["state"]
                side = r.get("low_side") if state == "STRONG_LOW" else r.get("high_side") if state == "STRONG_HIGH" else None
                out.append({
                    "semantic_key": f"factor:{scope}:{'global' if fpid is None else int(fpid)}:{fid}",
                    "label": r.get("axis_name"),
                    "role": r.get("role"),
                    "status": r.get("status"),
                    "confidence": r.get("confidence"),
                    "rationale": r.get("rationale"),
                    "source_structure": "ica_factor",
                    "semantic_layer": "continuous_attribute",
                    "operationally_mapped": False,
                    "scope": scope,
                    "parent_id": fpid,
                    "factor_id": fid,
                    "score": fr["score"],
                    "reference_percentile": fr["reference_percentile"],
                    "activation_state": state,
                    "active_side": side,
                    "low_side": r.get("low_side"),
                    "high_side": r.get("high_side"),
                })
                break

    # Patch semantics are interpretive context only; the numeric atypicality remains separate.
    for r in regs["patch"]:
        if int(r.get("parent_id")) == pid:
            out.append({
                "semantic_key": f"patch_context:p{pid:02d}",
                "label": r.get("interpretation"),
                "role": "patch_context",
                "status": "contextual",
                "confidence": r.get("confidence"),
                "condition_relevance": r.get("condition_relevance"),
                "nuisance_risk": r.get("nuisance_risk"),
                "rationale": r.get("rationale"),
                "source_structure": "patch_atypicality",
                "semantic_layer": "patch_context",
                "operationally_mapped": False,
                "local_percentile_q99": attributes.patch.get("local_percentile_q99"),
                "percentile_within_parent": attributes.patch.get("percentile_within_parent"),
            })
            break
    return out
