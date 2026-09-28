"""Typed contracts for the AI-only pipeline. Outline: fields may expand during parity work."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ReferenceState = Literal["IN_REFERENCE", "CAUTION", "OUTSIDE_REFERENCE"]
DiscoveryStatus = Literal[
    "unknown_mixed",
    "reliable_parent_only",
    "reliable_parent_and_fine_group",
]

@dataclass(frozen=True)
class ImageInput:
    path: Path

@dataclass
class FeatureBundle:
    image_sha256: str
    foreground_bbox: list[float]
    G_whole: Any
    G_foreground: Any
    G_dual: Any
    L_whole: Any
    L_foreground: Any
    L_dual: Any
    HSOFT: Any
    HFG_hires: Any
    dense_patch_g16: Any
    named_views: dict[str, Any] = field(default_factory=dict)

@dataclass
class AssignmentSupport:
    routed_label: int | None
    score: float | None
    threshold: float | None
    passed: bool
    features: dict[str, float] = field(default_factory=dict)
    neighbor_ids: list[int] = field(default_factory=list)

@dataclass
class ReferenceGateResult:
    state: ReferenceState
    global_distance: float | None = None
    global_percentile: float | None = None
    parent_distance: float | None = None
    parent_percentile: float | None = None
    reasons: list[str] = field(default_factory=list)

@dataclass
class DiscoveryResult:
    provisional_parent_id: int | None
    parent_id: int | None
    parent_support: AssignmentSupport
    fine_id: int | None
    fine_support: AssignmentSupport | None
    raw_visual_leaf_id: int | None
    discovery_status: DiscoveryStatus

@dataclass
class AttributeResult:
    global_ica: list[dict[str, Any]] = field(default_factory=list)
    family_ica: list[dict[str, Any]] = field(default_factory=list)
    patch: dict[str, Any] = field(default_factory=dict)

@dataclass
class InferenceResult:
    release_id: str
    image_sha256: str
    reference: ReferenceGateResult
    discovery: DiscoveryResult
    attributes: AttributeResult
    semantics: list[dict[str, Any]]
    decision_support: dict[str, Any]
    routes: dict[str, Any]
    sensitivity: dict[str, Any]
    provenance: dict[str, Any]
