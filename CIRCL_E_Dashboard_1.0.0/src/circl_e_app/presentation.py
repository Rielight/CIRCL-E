"""Transform a frozen :class:`InferenceResult` into a stable dashboard view model.

This module performs **presentation grouping only**. It never computes,
re-derives or mutates scientific values, and it never converts non-finite
frozen values into zeros. Where a frozen float is NaN/Inf it is surfaced as
``None`` in the structured model and rendered as ``"N/A"`` by
:func:`display_value`.

UNKNOWN / NOT_APPLICABLE / unresolved states are preserved as ``None`` (or as
their literal frozen strings such as ``"unknown_mixed"`` or
``"SUPPRESSED_OUTSIDE_REFERENCE"``); they are never replaced with fabricated
values.

The view model separates three information tiers so the UI can keep them apart:

* primary   - device profile, reference conformity, circular-economy profile,
              route affinity (human-readable states, no internal IDs);
* evidence  - identification evidence, attribute (ICA) evidence, patch
              atypicality;
* technical - raw numeric structure IDs, thresholds, rule/evidence IDs,
              neighbour IDs, source freezes.
"""
from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from .ui_helpers import humanize_token

DISPLAY_NA = "N/A"
DISPLAY_UNKNOWN = "UNKNOWN"

_STATE_LABELS = {
    "IN_REFERENCE": "In reference",
    "CAUTION": "Caution",
    "OUTSIDE_REFERENCE": "Outside reference",
}

_STATE_TONES = {
    "IN_REFERENCE": "ok",
    "CAUTION": "warn",
    "OUTSIDE_REFERENCE": "bad",
}

_DISCOVERY_LABELS = {
    "reliable_parent_and_fine_group": "Reliable parent + fine group",
    "reliable_parent_only": "Reliable parent only",
    "unknown_mixed": "Unknown / mixed",
}

_SUPPORT_STATE_LABELS = {
    "reliable_parent_and_fine_group": "Parent and fine group supported",
    "reliable_parent_only": "Parent supported; fine group unresolved",
    "unknown_mixed": "Abstained (unresolved / mixed)",
}

_RESOLUTION_LABELS = {
    "identified": "Identified",
    "unresolved_mixed": "Unresolved / mixed",
    "outside_reference": "Suppressed (outside reference)",
    "unavailable": "Not available",
}

_FACTOR_STATE_LABELS = {
    "STRONG_LOW": "Strong low",
    "STRONG_HIGH": "Strong high",
    "MID": "Mid",
    "UNRESOLVED": "Unresolved",
}

_REFERENCE_NOTE = (
    "Conformity to the CIRCL-E reference distribution. Percentiles are "
    "within-reference empirical ranks (0-100%); this is provisional research "
    "evidence and not a calibrated probability."
)

_ATTRIBUTE_FIELDS = ("condition", "configuration", "viewpoint", "scene_type", "acquisition_style")
_IDENTITY_FIELDS = ("device_family", "device_subtype", "component_type")

_IDENTITY_SPECS = (
    ("device_family", "Device family"),
    ("device_subtype", "Subtype"),
    ("component_type", "Component"),
)
_ATTRIBUTE_SPECS = (
    ("condition", "Condition"),
    ("configuration", "Configuration"),
    ("viewpoint", "Viewpoint"),
    ("scene_type", "Scene"),
    ("acquisition_style", "Acquisition"),
)


# --------------------------------------------------------------------------- #
# Plain / finiteness helpers
# --------------------------------------------------------------------------- #
def _to_plain(value: Any) -> Any:
    """Recursively convert dataclasses/arrays to plain Python, keeping floats."""
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    # numpy scalars/arrays without importing numpy at module import time
    tolist = getattr(value, "tolist", None)
    if callable(tolist) and type(value).__module__.split(".")[0] == "numpy":
        return _to_plain(tolist())
    return value


def _sanitize_nonfinite(value: Any) -> Any:
    """Replace NaN/Inf floats with ``None``. Never mutates the source object."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _sanitize_nonfinite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_nonfinite(v) for v in value]
    return value


def display_value(value: Any, *, unknown: bool = False) -> str:
    """Render a value for the UI; non-finite/None become an explicit label."""
    if value is None:
        return DISPLAY_UNKNOWN if unknown else DISPLAY_NA
    if isinstance(value, float) and not math.isfinite(value):
        return DISPLAY_NA
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def format_percentile(value: Any) -> str:
    """Render a within-reference empirical percentile as an explicit percentage.

    Frozen percentiles are fractions in ``[0, 1]``. Showing them as bare
    fractions (``0.878``) invites reading them as a probability or calibrated
    confidence; this renders ``87.8%`` instead and never invents a value.
    """
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return DISPLAY_NA
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return DISPLAY_NA


def _text_or_na(value: Any) -> str:
    if value is None:
        return DISPLAY_NA
    text = str(value).strip()
    return text or DISPLAY_NA


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #
def _is_operational_row(row: dict) -> bool:
    """True when a frozen semantics row may carry operational device semantics.

    Raw-visual rows are emitted with ``semantic_layer="descriptive_provenance"``
    and ``operationally_mapped=False``; they are provenance only and must not be
    rendered as confident operational device/attribute assertions.
    """
    return (
        row.get("semantic_layer") == "operational_structure"
        or row.get("operationally_mapped") is True
    )


def _semantics_by_role(semantics: list[dict]) -> dict[str, Any]:
    identity: dict[str, Any] = {k: None for k in _IDENTITY_FIELDS}
    fields: dict[str, Any] = {k: None for k in _ATTRIBUTE_FIELDS}
    field_meta: dict[str, Any] = {}
    labels: list[dict[str, Any]] = []
    attribute_rows: list[dict[str, Any]] = []
    patch_context: dict[str, Any] | None = None
    diagnostics: list[dict[str, Any]] = []

    for row in semantics:
        if not isinstance(row, dict):
            continue
        row = _sanitize_nonfinite(row)
        # Only operationally-mapped structure rows may populate the primary
        # device identity and attribute fields. Raw-visual rows are emitted as
        # ``semantic_layer="descriptive_provenance"`` / ``operationally_mapped=False``
        # and must never be promoted to operational device semantics. This is a
        # project invariant; the frozen values themselves are untouched.
        if _is_operational_row(row):
            for key in _IDENTITY_FIELDS:
                if identity[key] is None and row.get(key) is not None:
                    identity[key] = row.get(key)
                    field_meta[key] = _row_meta(row)
            for key in _ATTRIBUTE_FIELDS:
                if fields[key] is None and row.get(key) is not None:
                    fields[key] = row.get(key)
                    field_meta[key] = _row_meta(row)
        if row.get("semantic_layer") == "continuous_attribute":
            attribute_rows.append({
                "semantic_key": row.get("semantic_key"),
                "label": row.get("label"),
                "role": row.get("role"),
                "scope": row.get("scope"),
                "parent_id": row.get("parent_id"),
                "factor_id": row.get("factor_id"),
                "activation_state": row.get("activation_state"),
                "state_label": _FACTOR_STATE_LABELS.get(
                    row.get("activation_state"), _text_or_na(row.get("activation_state"))
                ),
                "active_side": row.get("active_side"),
                "reference_percentile": row.get("reference_percentile"),
                "score": row.get("score"),
                "confidence": row.get("confidence"),
                "status": row.get("status"),
                "rationale": row.get("rationale"),
            })
        elif row.get("role") == "patch_context":
            patch_context = {
                "label": row.get("label"),
                "condition_relevance": row.get("condition_relevance"),
                "nuisance_risk": row.get("nuisance_risk"),
                "rationale": row.get("rationale"),
                "confidence": row.get("confidence"),
            }
        elif row.get("role") == "diagnostic":
            diagnostics.append({
                "semantic_key": row.get("semantic_key"),
                "label": row.get("label"),
                "status": row.get("status"),
                "rationale": row.get("rationale"),
            })
        elif row.get("role") in {"device_family", "condition", "configuration", "viewpoint", "scene_type"} or row.get("label"):
            if row.get("semantic_key"):
                labels.append({
                    "semantic_key": row.get("semantic_key"),
                    "label": row.get("label"),
                    "role": row.get("role"),
                    "status": row.get("status"),
                    "confidence": row.get("confidence"),
                    "rationale": row.get("rationale"),
                    "semantic_layer": row.get("semantic_layer"),
                    "operationally_mapped": bool(row.get("operationally_mapped")),
                    "operational": _is_operational_row(row),
                })
    return {
        "identity": identity,
        "fields": fields,
        "field_meta": field_meta,
        "labels": labels,
        "diagnostics": diagnostics,
        "attribute_semantics": attribute_rows,
        "patch_context": patch_context,
    }


def _row_meta(row: dict) -> dict[str, Any]:
    return {
        "semantic_key": row.get("semantic_key"),
        "label": row.get("label"),
        "status": row.get("status"),
        "confidence": row.get("confidence"),
        "role": row.get("role"),
    }


def _meta_text(meta: dict[str, Any] | None) -> str | None:
    if not meta:
        return None
    bits = []
    if meta.get("status"):
        bits.append(humanize_token(meta["status"]))
    if meta.get("confidence"):
        bits.append(f"{meta['confidence']} confidence")
    return " · ".join(bits) or None


def _build_input(input_info: Any, raw: dict) -> dict[str, Any]:
    if input_info is None:
        return {
            "filename": None,
            "width": None,
            "height": None,
            "mode": None,
            "format": None,
            "byte_size": None,
            "byte_sha256": None,
            "pixel_sha256": raw.get("image_sha256"),
            "converted_from_mode": None,
            "display_size": None,
        }
    as_dict = input_info.as_dict() if hasattr(input_info, "as_dict") else dict(input_info)
    width = as_dict.get("width")
    height = as_dict.get("height")
    return {
        "filename": as_dict.get("filename"),
        "width": width,
        "height": height,
        "mode": as_dict.get("mode"),
        "format": as_dict.get("format"),
        "byte_size": as_dict.get("byte_size"),
        "byte_sha256": as_dict.get("sha256"),
        "pixel_sha256": raw.get("image_sha256"),
        "converted_from_mode": as_dict.get("converted_from_mode"),
        "display_size": f"{width} × {height}" if width and height else None,
    }


def _build_release(release_info: Any, raw: dict) -> dict[str, Any]:
    if release_info is not None:
        info = release_info.as_dict() if hasattr(release_info, "as_dict") else dict(release_info)
    else:
        prov_release = (raw.get("provenance") or {}).get("release") or {}
        info = {
            "release_id": raw.get("release_id") or prov_release.get("release_id"),
            "verified": prov_release.get("verified"),
            "development": not bool(prov_release.get("verified")),
            "discovery_version": prov_release.get("discovery_version"),
            "semantic_version": prov_release.get("semantic_version"),
            "postmapping_version": prov_release.get("postmapping_version"),
            "dino_path": None,
            "cradio_path": None,
            "root": None,
        }
        info["status_label"] = _release_status_label(info["verified"])
    info.setdefault("development", not bool(info.get("verified")))
    info.setdefault("status_label", _release_status_label(info.get("verified")))
    return info


def _release_status_label(verified: Any) -> str:
    """Neutral, truthful user-facing release-status wording.

    The scientific ``verified`` flag itself is never changed or hidden; it is
    shown as a boolean under Technical. This only names the user-facing status.
    """
    return "Verified canonical release" if bool(verified) else "Research / decision-support release"


def _build_reference(raw: dict) -> dict[str, Any]:
    ref = dict(raw.get("reference") or {})
    state = ref.get("state")
    reasons = [str(r) for r in (ref.get("reasons") or [])]
    return {
        "state": state,
        "state_label": _STATE_LABELS.get(state, DISPLAY_UNKNOWN),
        "tone": _STATE_TONES.get(state, "neutral"),
        "global_distance": ref.get("global_distance"),
        "global_percentile": ref.get("global_percentile"),
        "parent_distance": ref.get("parent_distance"),
        "parent_percentile": ref.get("parent_percentile"),
        "reasons": reasons,
        "reason_count": len(reasons),
        "provisional": True,
        "note": _REFERENCE_NOTE,
    }


def _build_reliability(raw: dict) -> dict[str, Any]:
    disc = dict(raw.get("discovery") or {})
    parent_support = dict(disc.get("parent_support") or {})
    fine_support = disc.get("fine_support")
    fine_support = dict(fine_support) if isinstance(fine_support, dict) else {}
    status = disc.get("discovery_status")
    return {
        "discovery_status": status,
        "discovery_status_label": _DISCOVERY_LABELS.get(status, DISPLAY_UNKNOWN),
        "support_state_label": _SUPPORT_STATE_LABELS.get(status, DISPLAY_UNKNOWN),
        "abstained": status == "unknown_mixed",
        "provisional_parent_id": disc.get("provisional_parent_id"),
        "parent_id": disc.get("parent_id"),
        "fine_id": disc.get("fine_id"),
        "raw_visual_leaf_id": disc.get("raw_visual_leaf_id"),
        "parent_routed_label": parent_support.get("routed_label"),
        "parent_score": parent_support.get("score"),
        "parent_threshold": parent_support.get("threshold"),
        "parent_passed": parent_support.get("passed"),
        "parent_features": dict(parent_support.get("features") or {}),
        "fine_routed_label": fine_support.get("routed_label"),
        "fine_score": fine_support.get("score"),
        "fine_threshold": fine_support.get("threshold"),
        "fine_passed": fine_support.get("passed"),
        "fine_features": dict(fine_support.get("features") or {}),
    }


def _factor_rows(scope: str, factors: list[dict], semantic_rows: list[dict]) -> list[dict[str, Any]]:
    index: dict[tuple[Any, Any], dict] = {}
    for row in semantic_rows:
        if row.get("scope") == scope:
            index[(row.get("parent_id"), row.get("factor_id"))] = row
    out: list[dict[str, Any]] = []
    for factor in factors:
        if not isinstance(factor, dict):
            continue
        key = (factor.get("parent_id"), factor.get("factor_id"))
        semantic = index.get(key, {})
        state = factor.get("state")
        out.append({
            "scope": scope,
            "parent_id": factor.get("parent_id"),
            "factor_id": factor.get("factor_id"),
            "label": semantic.get("label"),
            "semantic_key": semantic.get("semantic_key"),
            "state": state,
            "state_label": _FACTOR_STATE_LABELS.get(state, _text_or_na(state)),
            "reference_percentile": factor.get("reference_percentile"),
            "score": factor.get("score"),
            "active_side": semantic.get("active_side"),
            "status": semantic.get("status"),
            "confidence": semantic.get("confidence"),
            "rationale": semantic.get("rationale"),
        })
    return out


def _build_attributes(raw: dict, grouped: dict) -> dict[str, Any]:
    attrs = dict(raw.get("attributes") or {})
    semantics = grouped["attribute_semantics"]
    global_factors = [f for f in (attrs.get("global_ica") or []) if isinstance(f, dict)]
    family_factors = [f for f in (attrs.get("family_ica") or []) if isinstance(f, dict)]
    return {
        "fields": grouped["fields"],
        "field_meta": grouped["field_meta"],
        "attribute_semantics": semantics,
        "global_factors": global_factors,
        "family_factors": family_factors,
        "global_rows": _factor_rows("global", global_factors, semantics),
        "family_rows": _factor_rows("family", family_factors, semantics),
        "patch_context": grouped["patch_context"],
    }


def _build_patch(raw: dict, grouped: dict) -> dict[str, Any]:
    attrs = dict(raw.get("attributes") or {})
    patch = dict(attrs.get("patch") or {})
    context = grouped["patch_context"] or {}
    return {
        "q90": patch.get("q90"),
        "q95": patch.get("q95"),
        "q99": patch.get("q99"),
        "mean": patch.get("mean"),
        "std": patch.get("std"),
        "local_z_q99": patch.get("local_z_q99"),
        "local_percentile_q99": patch.get("local_percentile_q99"),
        "percentile_within_parent": patch.get("percentile_within_parent"),
        "interpretation": context.get("label"),
        "condition_relevance": context.get("condition_relevance"),
        "nuisance_risk": context.get("nuisance_risk"),
        "context_confidence": context.get("confidence"),
        "note": "Patch atypicality is a descriptive visual statistic, not damage probability.",
    }


def _level_label(level: Any) -> str:
    if level is None:
        return "Unresolved"
    if isinstance(level, bool):
        return str(level)
    if isinstance(level, int):
        return {1: "LOW", 2: "MODERATE-LOW", 3: "MODERATE-HIGH", 4: "HIGH"}.get(level, str(level))
    return str(level)


#: Display-only title-case spelling of the frozen ordinal level labels. Casing
#: only; the underlying levels, thresholds and meanings are untouched.
_AFFINITY_LABELS = {
    1: "Low",
    2: "Moderate-low",
    3: "Moderate-high",
    4: "High",
}


def _affinity_label(level: Any) -> str:
    """Human-readable spelling of an ordinal level for normal-UI display."""
    if isinstance(level, bool) or level is None:
        return _level_label(level)
    if isinstance(level, int):
        return _AFFINITY_LABELS.get(level, str(level))
    return str(level)



def _dimension_display(entry: dict) -> dict[str, Any]:
    label = entry.get("label")
    level = entry.get("level")
    profile_status = entry.get("profile_status") or ""
    if label == "SUPPRESSED_OUTSIDE_REFERENCE" or profile_status == "SUPPRESSED_OUTSIDE_REFERENCE":
        return {"display": "Suppressed (outside reference)", "state": "suppressed"}
    if str(profile_status).startswith("NOT_APPLICABLE"):
        anchor = entry.get("class_reuse_anchor_label")
        return {"display": anchor or "Not applicable", "state": "not_applicable"}
    if label and label != "UNRESOLVED":
        return {"display": humanize_token(label), "state": "resolved"}
    return {"display": "Unresolved", "state": "unresolved"}


def _build_post_mapping(raw: dict, labels: dict) -> dict[str, Any]:
    ds = dict(raw.get("decision_support") or {})
    criteria_labels = (labels or {}).get("criteria") or {}
    out: dict[str, Any] = {}
    for dim in ("RRP", "WRO", "CSO", "TPC", "IRP"):
        value = ds.get(dim)
        if not isinstance(value, dict) or not value:
            out[dim] = {}
            continue
        entry = dict(value)
        criteria = dict(entry.get("criteria") or {})
        rows = []
        for cid in sorted(criteria):
            info = criteria_labels.get(cid) or {}
            level = criteria[cid]
            rows.append({
                "criterion_id": cid,
                "name": info.get("name") or humanize_token(cid),
                "meaning": info.get("meaning") or None,
                "level": level,
                "level_label": _level_label(level),
            })
        display = _dimension_display(entry)
        entry.update({
            "display": display["display"],
            "display_state": display["state"],
            "criteria_rows": rows,
            "applied_rule_ids": [str(r) for r in (entry.get("applied_rule_ids") or [])],
            "reason_ids": [str(r) for r in (entry.get("main_reason_set") or [])],
            "criterion_rule_ids": {
                str(k): [str(x) for x in (v or [])]
                for k, v in dict(entry.get("criterion_rule_ids") or {}).items()
            },
            "status": {
                "profile_status": entry.get("profile_status"),
                "whole_device_reuse_applicability": entry.get("whole_device_reuse_applicability"),
                "image_state_status": entry.get("image_state_status"),
                "class_reuse_anchor_label": entry.get("class_reuse_anchor_label"),
                "class_reuse_anchor_origin": entry.get("class_reuse_anchor_origin"),
            },
        })
        out[dim] = entry
    return out


def _build_routing(raw: dict, labels: dict) -> dict[str, Any]:
    routes = dict(raw.get("routes") or {})
    levels = dict(routes.get("levels") or {})
    highest = [str(r) for r in (routes.get("highest_affinity_route_set") or [])]
    highest_route = routes.get("highest_affinity_route")
    suppressed = highest_route == "SUPPRESSED_OUTSIDE_REFERENCE" or routes.get("profile_status") == "SUPPRESSED_OUTSIDE_REFERENCE"
    unresolved = (not highest) and not suppressed
    route_interpretation = routes.get("interpretation") or labels.get("route_interpretation")
    level_rows = [
        {"route": route, "display": humanize_token(route), "level": lvl, "level_label": _affinity_label(lvl)}
        for route, lvl in sorted(
            levels.items(),
            key=lambda kv: (-(kv[1] if isinstance(kv[1], int) else -1), str(kv[0])),
        )
    ]
    return {
        "levels": levels,
        "level_rows": level_rows,
        "highest_affinity_route_set": highest,
        "highest_display": [humanize_token(r) for r in highest],
        "highest_affinity_level": routes.get("highest_affinity_level"),
        "highest_affinity_label": _affinity_label(routes.get("highest_affinity_level")),
        "highest_affinity_route": highest_route,
        "tie": len(highest) > 1,
        "has_highest": bool(highest),
        "suppressed": bool(suppressed),
        "unresolved": bool(unresolved),
        "second_route_set": [str(r) for r in (routes.get("second_route_set") or [])],
        "route_margin": routes.get("route_margin"),
        "applied_rule_ids": [str(r) for r in (routes.get("applied_rule_ids") or [])],
        "resolution_rule_ids": [str(r) for r in (routes.get("resolution_rule_ids") or [])],
        "profile_status": routes.get("profile_status"),
        "interpretation": route_interpretation or "ordinal route compatibility/affinity; not a recommendation",
        "deployment_caution": bool(routes.get("deployment_caution")),
    }


def _build_provenance(raw: dict) -> dict[str, Any]:
    prov = dict(raw.get("provenance") or {})
    post = dict(prov.get("postmapping") or {})
    sem = dict(prov.get("semantics") or {})
    image = dict(prov.get("image") or {})
    discovery = dict(prov.get("discovery") or {})
    attrs = dict(prov.get("attributes") or {})
    return {
        "release": dict(prov.get("release") or {}),
        "rule_ids": list(post.get("rule_ids") or []),
        "evidence_source_ids": list(post.get("evidence_source_ids") or []),
        "profile_status": post.get("profile_status"),
        "nonclaims": post.get("nonclaims"),
        "semantic_keys": list(sem.get("semantic_keys") or []),
        "image": {
            "pixel_sha256": image.get("sha256") or raw.get("image_sha256"),
            "foreground_bbox": list(image.get("foreground_bbox") or []),
        },
        "discovery_detail": {
            "provisional_parent_id": discovery.get("provisional_parent_id"),
            "parent_id": discovery.get("parent_id"),
            "fine_id": discovery.get("fine_id"),
            "raw_visual_leaf_id": discovery.get("raw_visual_leaf_id"),
            "discovery_status": discovery.get("discovery_status"),
        },
        "neighbor_ids": {
            "parent_support": list(discovery.get("parent_support_neighbor_ids") or []),
            "fine_support": list(discovery.get("fine_support_neighbor_ids") or []),
            "identity_reference": list(attrs.get("identity_reference_neighbor_ids") or []),
            "patch_reference": list(attrs.get("patch_reference_neighbor_ids") or []),
        },
        "factor_states": {
            "global": dict(attrs.get("global_factor_states") or {}),
            "family": dict(attrs.get("family_factor_states") or {}),
        },
        "sensitivity_available": bool(raw.get("sensitivity")),
    }


def _device_identity(raw: dict, grouped: dict) -> dict[str, Any]:
    disc_status = (raw.get("discovery") or {}).get("discovery_status")
    ref_state = (raw.get("reference") or {}).get("state")
    diagnostic_keys = {d.get("semantic_key") for d in grouped["diagnostics"]}

    if disc_status == "unknown_mixed":
        resolution = "unresolved_mixed"
    elif "diagnostic:outside_reference" in diagnostic_keys or ref_state == "OUTSIDE_REFERENCE":
        resolution = "outside_reference"
    elif any(grouped["identity"][k] is not None for k in _IDENTITY_FIELDS):
        resolution = "identified"
    else:
        resolution = "unavailable"

    def field_display(value: Any) -> str:
        if value is not None:
            return humanize_token(value)
        if resolution == "unresolved_mixed":
            return "Unresolved"
        if resolution == "outside_reference":
            return "Suppressed"
        if resolution == "identified":
            return "Unknown"
        return "Not available"

    def spec_rows(specs) -> list[dict[str, Any]]:
        rows = []
        for key, label in specs:
            rows.append({
                "key": key,
                "label": label,
                "value": grouped["identity" if key in _IDENTITY_FIELDS else "fields"].get(key),
                "display": field_display(grouped["identity" if key in _IDENTITY_FIELDS else "fields"].get(key)),
                "meta": _meta_text(grouped["field_meta"].get(key)),
                "meta_raw": grouped["field_meta"].get(key) or {},
            })
        return rows

    identity = dict(grouped["identity"])
    identity.update({
        "resolution": resolution,
        "resolution_label": _RESOLUTION_LABELS.get(resolution, DISPLAY_UNKNOWN),
        "primary_fields": spec_rows(_IDENTITY_SPECS),
        "secondary_fields": spec_rows(_ATTRIBUTE_SPECS),
        "labels": grouped["labels"],
        "diagnostics": grouped["diagnostics"],
        "declared_semantics": [
            s for s in (raw.get("semantics") or []) if isinstance(s, dict)
        ],
    })
    identity["best_available"] = best_available_identity(identity)
    return identity


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def best_available_identity(identity: Mapping[str, Any] | None) -> dict[str, Any]:
    """Pick the strongest honest identity headline from authoritative fields.

    Strict fallback hierarchy (never fabricates a family):

    * a resolved device family -> its own (humanized) name;
    * otherwise a resolved component -> a generic board/component headline;
    * outside the reference domain -> an explicit suppression label;
    * otherwise -> an explicit unresolved label.

    The returned ``detail`` is an optional one-line explanation and is ``None``
    when the headline is self-explanatory.
    """
    identity = identity or {}
    resolution = identity.get("resolution")

    if resolution == "outside_reference":
        return {
            "headline": "Device identity suppressed",
            "kind": "suppressed",
            "detail": "The image falls outside the reference domain.",
        }

    family = identity.get("device_family")
    if family:
        return {"headline": humanize_token(family), "kind": "family", "detail": None}

    subtype = identity.get("device_subtype")
    if subtype:
        return {"headline": humanize_token(subtype), "kind": "subtype", "detail": None}

    component = identity.get("component_type")
    if component:
        return {
            "headline": "Electronic board or component",
            "kind": "component",
            "detail": f"Component: {humanize_token(component)}",
        }

    if resolution == "unresolved_mixed":
        return {
            "headline": "Device identity unresolved",
            "kind": "unresolved",
            "detail": "The routing-support requirement was not met, so no device-family assertion is published.",
        }
    return {"headline": "Device identity unresolved", "kind": "unresolved", "detail": None}


def to_json_safe(result: Any) -> Any:
    """Return a JSON-safe copy of a result/payload with non-finite floats as None.

    The source object is never mutated; no NaN is converted to zero.
    """
    return _sanitize_nonfinite(_to_plain(result))


def prepare_display_result(
    result: Any,
    *,
    input_info: Any = None,
    release_info: Any = None,
    labels: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable, JSON-safe presentation model from an ``InferenceResult``.

    The source ``result`` is never mutated. Non-finite frozen floats are surfaced
    as ``None`` (rendered as ``"N/A"``); no value is coerced to zero.

    ``labels`` optionally carries authoritative, display-only names read from the
    frozen release (see :mod:`circl_e_app.labels`); it never changes scientific
    values.
    """
    raw = _to_plain(result)
    semantics = [s for s in (raw.get("semantics") or []) if isinstance(s, dict)]
    grouped = _semantics_by_role(semantics)
    label_map = labels or {}

    view = {
        "input": _build_input(input_info, raw),
        "release": _build_release(release_info, raw),
        "reference_conformity": _build_reference(raw),
        "device_identity": _device_identity(raw, grouped),
        "reliability": _build_reliability(raw),
        "attributes": _build_attributes(raw, grouped),
        "patch": _build_patch(raw, grouped),
        "post_mapping": _build_post_mapping(raw, label_map),
        "routing": _build_routing(raw, label_map),
        "provenance": _build_provenance(raw),
        "labels": {
            "dimensions": dict(label_map.get("dimensions") or {}),
            "criteria": dict(label_map.get("criteria") or {}),
            "route_interpretation": label_map.get("route_interpretation"),
        },
    }
    return _sanitize_nonfinite(view)
