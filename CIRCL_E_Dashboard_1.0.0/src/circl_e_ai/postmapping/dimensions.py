"""Central ordinal aggregation and exact IRP rule outline.

RRP/WRO/CSO/TPC aggregation is directly executable. IRP is implemented from
its exported rule registry and source notebook logic, assuming the context
builder supplies the named fields documented below.
"""
from __future__ import annotations
import math


def _notnull(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def safe_lower_median(values):
    vals = sorted(int(v) for v in values if _notnull(v))
    if len(vals) < 2:
        return None
    return vals[(len(vals) - 1) // 2]


def compute_rrp(c):
    a = c.get("RRP_A_resource_relevance")
    extras = [c.get("RRP_B_recovery_maturity"), c.get("RRP_C_feed_specificity")]
    if not _notnull(a) or not any(_notnull(x) for x in extras):
        return None
    consensus = safe_lower_median([a] + extras)
    return min(int(a), int(consensus))


def compute_wro(c):
    a = c.get("WRO_A_product_reuse")
    image_states = [c.get("WRO_B_visual_integrity"), c.get("WRO_C_configuration_completeness")]
    if not _notnull(a) or not any(_notnull(x) for x in image_states):
        return None
    return safe_lower_median([a] + image_states)


def compute_cso(c):
    a = c.get("CSO_A_component_salvage")
    extras = [c.get("CSO_B_accessibility_dismantling"), c.get("CSO_C_component_specificity")]
    if not _notnull(a) or not any(_notnull(x) for x in extras):
        return None
    return safe_lower_median([a] + extras)


def compute_tpc(c):
    return safe_lower_median([
        c.get("TPC_A_specialist_requirement"),
        c.get("TPC_B_separation_complexity"),
        c.get("TPC_C_screening_relevance"),
    ])


def irp_assignment_resolution(discovery_status: str, relative_support_state: str) -> tuple[int, str]:
    """IRP-A exact rule mapping from the exported registry."""
    if discovery_status == "unknown_mixed":
        return 4, "IRP_A_UNKNOWN"
    parent_only = discovery_status == "reliable_parent_only"
    fine = discovery_status == "reliable_parent_and_fine_group"
    s = relative_support_state
    if parent_only:
        return {
            "LOW_RELATIVE_SUPPORT": (4, "IRP_A_PARENT_ONLY_LOW"),
            "MEDIUM_RELATIVE_SUPPORT": (3, "IRP_A_PARENT_ONLY_MED"),
            "HIGH_RELATIVE_SUPPORT": (2, "IRP_A_PARENT_ONLY_HIGH"),
        }.get(s, (4, "IRP_A_PARENT_ONLY_LOW"))
    if fine:
        return {
            "LOW_RELATIVE_SUPPORT": (3, "IRP_A_FINE_LOW"),
            "MEDIUM_RELATIVE_SUPPORT": (2, "IRP_A_FINE_MED"),
            "HIGH_RELATIVE_SUPPORT": (1, "IRP_A_FINE_HIGH"),
        }.get(s, (3, "IRP_A_FINE_LOW"))
    return 4, "IRP_A_UNKNOWN"


def irp_semantic_evidence_resolution(parent_id: int | None, release) -> tuple[int, str]:
    """IRP-B is a frozen parent-level evidence-resolution lookup.

    The source notebook computes this once from ``criterion_evidence_map`` for
    each of the 16 parents, then applies the resulting level/rule to every image
    in that parent. The release builder should precompute and freeze that map.
    """
    if parent_id is None:
        return 4, "IRP_B_RESIDUAL_SCENE"
    rec = release.assets.postmapping["irp_b_by_parent"][int(parent_id)]
    return int(rec["level"]), str(rec["rule_id"])

def irp_visual_atypicality(parent_id: int | None, parent_patch_percentile: float | None,
                            global_factor_11_state: str | None) -> tuple[int, list[str]]:
    """IRP-C exact quartile rule plus accepted clutter override."""
    # Exact source rule: unknown is handled by caller via discovery status;
    # parent 8 (mixed scene) is forced to Q4. Parent 0 is not force-raised here.
    if parent_id == 8:
        return 4, ["IRP_C_Q4"]
    if parent_patch_percentile is None or not _notnull(parent_patch_percentile):
        level, reasons = 2, ["IRP_C_Q2"]  # source missing-value default
    elif parent_patch_percentile <= 0.25:
        level, reasons = 1, ["IRP_C_Q1"]
    elif parent_patch_percentile <= 0.50:
        level, reasons = 2, ["IRP_C_Q2"]
    elif parent_patch_percentile <= 0.75:
        level, reasons = 3, ["IRP_C_Q3"]
    else:
        level, reasons = 4, ["IRP_C_Q4"]
    if global_factor_11_state == "STRONG_HIGH" and level < 3:
        level = 3
        reasons = ["IRP_C_CLUTTER"]
    return level, reasons


def compute_irp(context, release=None) -> dict:
    """Return max-rule IRP while preserving all tied main reasons.

    Expected context keys:
      discovery_status, relative_support_state, parent_id,
      evidence_anchor_rows, patch_atypicality_percentile_within_parent,
      global_factor_11_state.
    """
    a, a_reason = irp_assignment_resolution(
        context["discovery_status"], context.get("relative_support_state", "UNRESOLVED")
    )
    b, b_reason = irp_semantic_evidence_resolution(context.get("parent_id"), release)
    if context["discovery_status"] == "unknown_mixed":
        c, c_reasons = 4, ["IRP_C_Q4"]
    else:
        c, c_reasons = irp_visual_atypicality(
            context.get("parent_id"),
            context.get("patch_atypicality_percentile_within_parent"),
            context.get("global_factor_11_state"),
        )
    levels = {
        "IRP_A_assignment_resolution": a,
        "IRP_B_semantic_evidence_resolution": b,
        "IRP_C_visual_atypicality_inventory": c,
    }
    max_level = max(levels.values())
    reason_ids = []
    if a == max_level:
        reason_ids.append(a_reason)
    if b == max_level:
        reason_ids.append(b_reason)
    if c == max_level:
        reason_ids.extend(c_reasons)
    return {
        "level": max_level,
        "criteria": levels,
        "criterion_rule_ids": {
            "IRP_A_assignment_resolution": [a_reason],
            "IRP_B_semantic_evidence_resolution": [b_reason],
            "IRP_C_visual_atypicality_inventory": c_reasons,
        },
        "main_reason_set": reason_ids,
        "interpretation": "relative inspection/resolution priority; not risk, damage, hazard or failure probability",
    }
