"""Rendering helpers and result sections for the CIRCL-E dashboard.

This module contains **presentation only**. It reads the view model built by
:mod:`circl_e_app.presentation` and never recomputes, re-derives or mutates a
scientific value. Evidence is grouped into three levels:

* Summary   - image, best-available identity, reference conformity,
              circular-economy profile, highest-affinity route;
* Evidence  - discovery/support, circular-economy criteria, route levels,
              attribute (ICA) evidence, patch atypicality;
* Technical - release/model identifiers, raw IDs, hashes, rule ids, provenance.
"""
from __future__ import annotations

import html
import json
from typing import Any

import streamlit as st

from circl_e_app import (
    display_value,
    drop_empty_columns,
    format_percentile,
    humanize_token,
    to_json_safe,
)

from styles import DASHBOARD_VERSION, DIMENSION_ORDER, MODEL_RELEASE_NOTE


# --------------------------------------------------------------------------- #
# Primitive HTML helpers
# --------------------------------------------------------------------------- #
def esc(value: object) -> str:
    return html.escape(str(value))


def card(
    label: str,
    value: object = None,
    *,
    meta: str | None = None,
    pill_text: str | None = None,
    tone: str = "neutral",
    large: bool = False,
    help_text: str | None = None,
) -> str:
    """Return one card as an HTML fragment (no scientific logic)."""
    value_cls = "ce-value ce-value-lg" if large else "ce-value"
    title = f' title="{esc(help_text)}"' if help_text else ""
    parts = [f'<div class="ce-card"{title}><div class="ce-label">{esc(label)}</div>']
    if pill_text is not None:
        parts.append(
            f'<div class="{value_cls}"><span class="ce-pill ce-pill-{esc(tone)}">'
            f"{esc(pill_text)}</span></div>"
        )
    else:
        parts.append(f'<div class="{value_cls}">{esc(value)}</div>')
    if meta:
        parts.append(f'<div class="ce-meta">{esc(meta)}</div>')
    parts.append("</div>")
    return "".join(parts)


def card_row(cards: list[str], *, min_width: str = "9rem") -> None:
    """Render cards in a wrapping flex row so narrow views never clip them."""
    st.markdown(
        f'<div class="ce-card-row" style="--ce-card-min:{esc(min_width)}">'
        + "".join(cards)
        + "</div>",
        unsafe_allow_html=True,
    )


def muted(text: str) -> None:
    st.markdown(f'<div class="ce-muted">{esc(text)}</div>', unsafe_allow_html=True)


def kv_table(pairs: list[tuple[str, object]]) -> None:
    st.dataframe(
        [{"Field": key, "Value": display_value(value)} for key, value in pairs],
        hide_index=True,
        width="stretch",
    )


def show_error(message: str, detail: str | None) -> None:
    from circl_e_app import cuda_guidance

    st.error(message)
    hint = cuda_guidance(detail)
    if hint:
        st.info(hint)
    if detail:
        with st.expander("Technical details", expanded=False):
            st.code(str(detail))


def placeholder() -> None:
    st.markdown(
        '<div class="ce-placeholder">'
        '<div class="ce-placeholder-title">Upload an image to begin</div>'
        '<div class="ce-muted">Upload an electronic-device image to inspect identity, '
        "reference conformity, circular-economy indicators and route affinity.</div>"
        "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #
def _dimension_help(dim: str, display: dict) -> str | None:
    names = [
        entry.get("name")
        for entry in ((display.get("labels") or {}).get("dimensions") or {}).get(dim) or []
        if entry.get("name")
    ]
    if not names:
        return None
    return "Criteria: " + "; ".join(names)


def _identity_properties(identity: dict) -> list[dict[str, Any]]:
    """Meaningful, non-empty identity/attribute fields (never Unknown cards)."""
    fields: list[dict[str, Any]] = []
    for field in identity.get("primary_fields", []):
        if field.get("key") == "device_family":
            continue  # already the headline
        if field.get("value") is not None:
            fields.append(field)
    for field in identity.get("secondary_fields", []):
        if field.get("value") is not None:
            fields.append(field)
    return fields


def _render_identity(display: dict) -> None:
    identity = display["device_identity"]
    best = identity.get("best_available") or {}
    headline = best.get("headline") or identity.get("resolution_label") or "Device identity unresolved"
    st.markdown(f'<div class="ce-headline">{esc(headline)}</div>', unsafe_allow_html=True)
    if best.get("kind") == "unresolved":
        st.markdown('<div class="ce-headline-detail">Device family unresolved.</div>', unsafe_allow_html=True)
    if best.get("detail"):
        st.markdown(f'<div class="ce-headline-detail">{esc(best["detail"])}</div>', unsafe_allow_html=True)

    fields = _identity_properties(identity)
    if fields:
        card_row(
            [card(field["label"], field["display"], meta=field.get("meta")) for field in fields],
            min_width="7.5rem",
        )


def _reference_meta(ref: dict) -> str | None:
    bits = []
    if ref.get("global_percentile") is not None:
        bits.append(f"Global {format_percentile(ref['global_percentile'])}")
    if ref.get("parent_percentile") is not None:
        bits.append(f"Parent-local {format_percentile(ref['parent_percentile'])}")
    return " · ".join(bits) or None


def _render_reference_compact(display: dict) -> None:
    ref = display["reference_conformity"]
    card_row(
        [
            card(
                "Reference conformity",
                pill_text=ref["state_label"],
                tone=ref["tone"],
                meta=_reference_meta(ref),
            )
        ],
        min_width="14rem",
    )


def _render_circular_economy_summary(display: dict) -> None:
    st.markdown("#### Circular-economy profile")
    post = display["post_mapping"]
    cards = []
    for dim in DIMENSION_ORDER:
        entry = post.get(dim) or {}
        value = (entry.get("display") or "Unresolved") if entry else "Not available"
        cards.append(card(dim, value, help_text=_dimension_help(dim, display)))
    card_row(cards, min_width="6.5rem")
    if post and all(
        (entry or {}).get("display_state") == "suppressed" for entry in post.values() if entry
    ):
        muted("Dimensions are suppressed because the image falls outside the reference domain.")


def _render_route_summary(display: dict) -> None:
    routing = display["routing"]
    if routing["suppressed"]:
        return
    if not routing["has_highest"]:
        muted("No route affinity could be resolved for this image.")
        return
    affinity = routing.get("highest_affinity_label") or display_value(routing["highest_affinity_level"])
    if routing["tie"]:
        st.markdown(
            card(
                "Highest-affinity routes",
                " · ".join(routing["highest_display"]),
                meta=f"Tie · Affinity: {affinity}",
                large=True,
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            card(
                "Highest-affinity route",
                routing["highest_display"][0],
                meta=f"Affinity: {affinity}",
                large=True,
            ),
            unsafe_allow_html=True,
        )
    muted("Affinity reflects compatibility with the inferred profile, not a prescriptive recommendation.")


def render_summary(display: dict, *, image: Any = None, image_caption: str | None = None) -> None:
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        if image is not None:
            st.image(image, caption=image_caption, width="stretch")
    with right:
        _render_identity(display)
        _render_reference_compact(display)

    _render_circular_economy_summary(display)
    _render_route_summary(display)


# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #
def _render_identification_evidence(display: dict) -> None:
    st.markdown("#### Identification evidence")
    rel = display["reliability"]
    card_row(
        [
            card("Discovery status", rel["discovery_status_label"]),
            card("Support state", rel["support_state_label"]),
        ],
        min_width="11rem",
    )
    card_row(
        [
            card("Parent support score", display_value(rel["parent_score"])),
            card("Fine-group support score", display_value(rel["fine_score"])),
        ],
        min_width="11rem",
    )
    muted(
        "Support scores are calibrated assignment-support values, not semantic confidence, "
        "correctness probability or a combined score."
    )
    ref = display["reference_conformity"]
    muted(
        f"Reference conformity: {_reference_meta(ref) or 'not available'}. "
        "Ranks are descriptive research signals, not calibrated probabilities."
    )


def _render_circular_economy_evidence(display: dict) -> None:
    st.markdown("#### Circular-economy evidence")
    post = display["post_mapping"]
    for dim in DIMENSION_ORDER:
        entry = post.get(dim) or {}
        if not entry:
            continue
        with st.expander(f"{dim} — criteria & drivers", expanded=False):
            status = entry.get("status") or {}
            if dim == "WRO" and status.get("whole_device_reuse_applicability"):
                muted(f"Whole-device reuse applicability: {humanize_token(status['whole_device_reuse_applicability'])}")
            if status.get("profile_status"):
                muted(f"Profile status: {humanize_token(status['profile_status'])}")
            rows = entry.get("criteria_rows") or []
            if rows:
                st.dataframe(
                    [
                        {"Criterion": row["name"], "Level": row["level_label"], "Meaning": row.get("meaning")}
                        for row in rows
                    ],
                    hide_index=True,
                    width="stretch",
                )
            drivers = entry.get("main_drivers") or []
            if drivers:
                for driver in drivers:
                    st.markdown(f"- {driver}")
    muted(
        "RRP/WRO/CSO/TPC/IRP are ordinal decision-support dimensions; levels are not a ratio "
        "scale. IRP is inspection/resolution priority, not risk or failure probability. WRO reflects "
        "visible integrity, not functionality."
    )


def _render_route_evidence(display: dict) -> None:
    st.markdown("#### Route evidence")
    routing = display["routing"]
    if routing["suppressed"]:
        st.warning("Route affinity is suppressed because the image falls outside the reference domain.")
    rows = routing["level_rows"]
    if rows:
        st.dataframe(
            [{"Route": row["display"], "Affinity": row["level_label"]} for row in rows],
            hide_index=True,
            width="stretch",
        )
    muted(routing["interpretation"])


_ATTRIBUTE_COLUMNS = ("Attribute", "State", "Reference percentile", "Interpretation")


def _attribute_table(reviewed: list[dict[str, Any]]) -> None:
    """Human-readable attribute table; all-empty presentation columns are dropped.

    Raw ``semantic_key`` and factor ids are deliberately not shown here (they are
    available under Technical). No scientific value is renamed or hidden: only a
    column with no value at all is omitted.
    """
    raw = [
        {
            "Attribute": row["label"],
            "State": row["state_label"],
            "Reference percentile": row.get("reference_percentile"),
            "Interpretation": row.get("active_side"),
        }
        for row in reviewed
    ]
    keep = drop_empty_columns(raw, _ATTRIBUTE_COLUMNS)
    formatted = []
    for row in raw:
        values = {
            "Attribute": row["Attribute"],
            "State": row["State"],
            "Reference percentile": format_percentile(row["Reference percentile"]),
            "Interpretation": humanize_token(row["Interpretation"]) or None,
        }
        formatted.append({column: values[column] for column in keep})
    st.dataframe(formatted, hide_index=True, width="stretch")


def _render_attribute_evidence(display: dict) -> None:
    attrs = display["attributes"]
    st.markdown("#### Attribute evidence")
    for title, rows, note in (
        ("Global attributes", attrs["global_rows"], "Comparable across device families."),
        ("Family-local attributes", attrs["family_rows"], "Parent-local; not comparable across device families."),
    ):
        reviewed = [row for row in rows if row.get("label")]
        if reviewed:
            st.markdown(f"**{title}** — {note}")
            _attribute_table(reviewed)
        numeric_only = len(rows) - len(reviewed)
        if numeric_only:
            st.caption(
                f"{numeric_only} {title.lower()} factor(s) are numerical-only "
                "(not semantically reviewed) and are listed under Technical."
            )

    if attrs["attribute_semantics"]:
        st.markdown("**Reviewed attribute interpretations**")
        st.dataframe(
            [
                {
                    "Attribute": row.get("label"),
                    "State": row.get("state_label") or humanize_token(row.get("activation_state")),
                    "Review confidence": row.get("confidence"),
                }
                for row in attrs["attribute_semantics"]
            ],
            hide_index=True,
            width="stretch",
        )

    declared = display["device_identity"]["labels"]
    if declared:
        st.markdown("**Declared semantic assertions**")
        st.dataframe(
            [
                {
                    "Label": row.get("label"),
                    "Role": humanize_token(row.get("role")),
                    "Tier": "operational" if row.get("operational") else "descriptive provenance",
                    "Status": humanize_token(row.get("status")),
                    "Review confidence": row.get("confidence"),
                }
                for row in declared
            ],
            hide_index=True,
            width="stretch",
        )
        if any(not row.get("operational") for row in declared):
            muted(
                "Rows marked 'descriptive provenance' are raw-visual annotations retained as evidence; "
                "they are not operational device assertions."
            )


def _render_patch_evidence(display: dict) -> None:
    patch = display["patch"]
    st.markdown("#### Visual atypicality")
    if patch.get("interpretation"):
        st.markdown(f"**{patch['interpretation']}**")
    card_row(
        [
            card("Atypicality q90", display_value(patch["q90"])),
            card("Atypicality q95", display_value(patch["q95"])),
            card("Atypicality q99", display_value(patch["q99"])),
        ],
        min_width="7rem",
    )
    metrics = []
    if patch.get("percentile_within_parent") is not None:
        metrics.append(
            f"Within-parent percentile {format_percentile(patch['percentile_within_parent'])}"
        )
    if patch.get("local_z_q99") is not None:
        metrics.append(f"Local z (q99) {display_value(patch['local_z_q99'])}")
    if patch.get("local_percentile_q99") is not None:
        metrics.append(
            f"Local percentile (q99) {format_percentile(patch['local_percentile_q99'])}"
        )
    if patch.get("condition_relevance"):
        metrics.append(f"Condition relevance {humanize_token(patch['condition_relevance'])}")
    if metrics:
        muted(" · ".join(metrics))
    muted(patch["note"])


def render_evidence(display: dict) -> None:
    _render_identification_evidence(display)
    _render_circular_economy_evidence(display)
    _render_route_evidence(display)
    _render_attribute_evidence(display)
    _render_patch_evidence(display)


# --------------------------------------------------------------------------- #
# Technical
# --------------------------------------------------------------------------- #
def render_technical(display: dict, result: Any) -> None:
    prov = display["provenance"]
    rel = display["reliability"]
    ref = display["reference_conformity"]
    inp = display["input"]
    release = display["release"]
    routing = display["routing"]

    st.markdown("#### Release")
    kv_table([
        ("dashboard_version", DASHBOARD_VERSION),
        ("software_note", MODEL_RELEASE_NOTE),
        ("model_release_status", release.get("status_label")),
        ("release_id", release.get("release_id")),
        ("verified", release.get("verified")),
        ("discovery_version", release.get("discovery_version")),
        ("semantic_version", release.get("semantic_version")),
        ("postmapping_version", release.get("postmapping_version")),
        ("dino_path", release.get("dino_path")),
        ("cradio_path", release.get("cradio_path")),
    ])

    st.markdown("#### Input")
    kv_table([
        ("filename", inp.get("filename")),
        ("format", inp.get("format")),
        ("mode", inp.get("mode")),
        ("converted_from_mode", inp.get("converted_from_mode")),
        ("dimensions", inp.get("display_size")),
        ("byte_size", inp.get("byte_size")),
        ("byte_sha256", inp.get("byte_sha256")),
        ("pixel_sha256", inp.get("pixel_sha256")),
        ("foreground_bbox", prov["image"].get("foreground_bbox")),
    ])

    st.markdown("#### Discovery / assignment support")
    kv_table([
        ("provisional_parent_id", rel["provisional_parent_id"]),
        ("parent_id", rel["parent_id"]),
        ("fine_id", rel["fine_id"]),
        ("raw_visual_leaf_id", rel["raw_visual_leaf_id"]),
        ("discovery_status", rel["discovery_status"]),
        ("parent_score", rel["parent_score"]),
        ("parent_threshold", rel["parent_threshold"]),
        ("parent_passed", rel["parent_passed"]),
        ("parent_features", rel["parent_features"]),
        ("fine_score", rel["fine_score"]),
        ("fine_threshold", rel["fine_threshold"]),
        ("fine_passed", rel["fine_passed"]),
        ("fine_features", rel["fine_features"]),
    ])

    st.markdown("#### Reference gate")
    kv_table([
        ("state", ref["state"]),
        ("global_distance", ref["global_distance"]),
        ("global_percentile", ref["global_percentile"]),
        ("parent_distance", ref["parent_distance"]),
        ("parent_percentile", ref["parent_percentile"]),
        ("reasons", ref["reasons"]),
    ])

    st.markdown("#### Post-mapping (raw)")
    post = display["post_mapping"]
    kv_table([
        (
            dim,
            {
                "level": (post.get(dim) or {}).get("level"),
                "profile_status": ((post.get(dim) or {}).get("status") or {}).get("profile_status"),
                "image_state_status": ((post.get(dim) or {}).get("status") or {}).get("image_state_status"),
                "whole_device_reuse_applicability": ((post.get(dim) or {}).get("status") or {}).get("whole_device_reuse_applicability"),
                "class_reuse_anchor_origin": ((post.get(dim) or {}).get("status") or {}).get("class_reuse_anchor_origin"),
                "applied_rule_ids": (post.get(dim) or {}).get("applied_rule_ids"),
            },
        )
        for dim in DIMENSION_ORDER
    ])

    irp = post.get("IRP") or {}
    if irp:
        st.markdown("#### IRP inspection-priority reasons (raw)")
        muted(
            "IRP reasons are inspection/resolution-priority rule ids, not risk, damage or "
            "failure-probability evidence."
        )
        kv_table([
            ("level", irp.get("level")),
            ("main_reason_set", irp.get("reason_ids")),
            ("criterion_rule_ids", irp.get("criterion_rule_ids")),
        ])

    st.markdown("#### Routing")
    kv_table([
        ("profile_status", routing["profile_status"]),
        ("levels", routing["levels"]),
        ("highest_affinity_route_set", routing["highest_affinity_route_set"]),
        ("second_route_set", routing["second_route_set"]),
        ("route_margin", routing["route_margin"]),
        ("applied_rule_ids", routing["applied_rule_ids"]),
        ("resolution_rule_ids", routing["resolution_rule_ids"]),
    ])

    st.markdown("#### Patch statistics (raw)")
    patch_raw = display["patch"]
    kv_table([
        ("q90", patch_raw.get("q90")),
        ("q95", patch_raw.get("q95")),
        ("q99", patch_raw.get("q99")),
        ("mean", patch_raw.get("mean")),
        ("std", patch_raw.get("std")),
        ("local_z_q99", patch_raw.get("local_z_q99")),
        ("local_percentile_q99", patch_raw.get("local_percentile_q99")),
        ("percentile_within_parent", patch_raw.get("percentile_within_parent")),
        ("condition_relevance", patch_raw.get("condition_relevance")),
        ("nuisance_risk", patch_raw.get("nuisance_risk")),
        ("context_confidence", patch_raw.get("context_confidence")),
    ])

    st.markdown("#### Factor states (raw)")
    kv_table([
        ("global_factor_states", prov["factor_states"].get("global")),
        ("family_factor_states", prov["factor_states"].get("family")),
    ])
    kv_table([
        ("global_ica_factors", display["attributes"]["global_factors"]),
        ("family_ica_factors", display["attributes"]["family_factors"]),
    ])

    st.markdown("#### Reviewed attribute interpretations (raw)")
    attr_rows = display["attributes"]["attribute_semantics"]
    if attr_rows:
        st.dataframe(
            [
                {
                    "semantic_key": row.get("semantic_key"),
                    "label": row.get("label"),
                    "role": row.get("role"),
                    "scope": row.get("scope"),
                    "parent_id": row.get("parent_id"),
                    "factor_id": row.get("factor_id"),
                    "activation_state": row.get("activation_state"),
                    "active_side": row.get("active_side"),
                    "reference_percentile": row.get("reference_percentile"),
                    "score": row.get("score"),
                    "confidence": row.get("confidence"),
                    "status": row.get("status"),
                    "rationale": row.get("rationale"),
                }
                for row in attr_rows
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        muted("No reviewed continuous attribute semantics were published for this image.")

    st.markdown("#### Reference neighbours consulted")
    kv_table([
        ("parent_support", prov["neighbor_ids"].get("parent_support")),
        ("fine_support", prov["neighbor_ids"].get("fine_support")),
        ("identity_reference", prov["neighbor_ids"].get("identity_reference")),
        ("patch_reference", prov["neighbor_ids"].get("patch_reference")),
    ])

    st.markdown("#### Provenance")
    kv_table([
        ("rule_ids", prov["rule_ids"]),
        ("evidence_source_ids", prov["evidence_source_ids"]),
        ("semantic_keys", prov["semantic_keys"]),
        ("profile_status", prov["profile_status"]),
        ("source_freezes", (prov["release"] or {}).get("source_freezes")),
        ("sensitivity_available", prov["sensitivity_available"]),
    ])
    if prov.get("nonclaims"):
        st.caption(prov["nonclaims"])

    st.download_button(
        "Download result JSON",
        json.dumps(to_json_safe(result), indent=2),
        file_name="circl_e_inference.json",
        mime="application/json",
    )
    with st.expander("Raw inference JSON", expanded=False):
        st.code(json.dumps(to_json_safe(result), indent=2), language="json")
