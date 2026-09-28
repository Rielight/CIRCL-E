"""Frozen assignment-support calculation.

This module contains no fitting. Calibrators and thresholds are release assets.
"""
from __future__ import annotations
import numpy as np
from circl_e_ai.reference.knn import weighted_vote_features
from circl_e_ai.contracts.models import AssignmentSupport

FEATURE_NAMES = ("support", "margin", "nn1", "nn5", "density")


def _score(calibrator, base_score, feature_vector):
    if calibrator is None:
        return float(base_score)
    return float(calibrator.predict_proba(np.asarray(feature_vector)[None, :])[:, 1][0])


def parent_assignment_support(root_vector, kmeans_parent: int, release) -> AssignmentSupport:
    """Evaluate frozen root routing support for an unseen image.

    Release contract:
      reference['root_support_X'], reference['root_support_parent_y']
      support_models['parent_calibrator'], support_models['parent_base_score']
      support_models['parent_threshold_by_parent'] (fallback global threshold)
      support_models['parent_operational_reliability'][parent]
    """
    ref = release.assets.reference
    sm = release.assets.support_models
    routed, fv, nids = weighted_vote_features(root_vector, ref["root_support_X"], ref["root_support_parent_y"], k=15)
    score = _score(sm.get("parent_calibrator"), sm["parent_base_score"], fv)
    thresholds = sm.get("parent_threshold_by_parent", {})
    threshold = float(thresholds.get(int(kmeans_parent), sm["parent_global_threshold"]))
    operational_reliability = float(sm["parent_operational_reliability"].get(int(kmeans_parent), 0.0))
    passed = int(routed) == int(kmeans_parent) and score >= threshold and operational_reliability >= 0.85
    return AssignmentSupport(
        routed_label=int(routed), score=score, threshold=threshold, passed=bool(passed),
        features={k: float(v) for k, v in zip(FEATURE_NAMES, fv)}, neighbor_ids=nids,
    )


def fine_assignment_support(fine_vector, parent_id: int, fine_global_id: int | None, release) -> AssignmentSupport:
    """Evaluate frozen parent-specific fine routing support.

    Reference rows must contain only known/validated fine labels for this parent.
    The exact configured fine view is selected before this function.
    """
    bank = release.assets.reference["fine_support_by_parent"][int(parent_id)]
    model = release.assets.support_models["fine_calibrator_by_parent"].get(int(parent_id))
    meta = release.assets.support_models["fine_meta_by_parent"][int(parent_id)]
    routed, fv, nids = weighted_vote_features(fine_vector, bank["X"], bank["global_fine_y"], k=15)
    score = _score(model, meta["base_score"], fv)
    threshold = float(meta["threshold"])
    passed = fine_global_id is not None and int(routed) == int(fine_global_id) and score >= threshold
    return AssignmentSupport(
        routed_label=int(routed), score=score, threshold=threshold, passed=bool(passed),
        features={k: float(v) for k, v in zip(FEATURE_NAMES, fv)}, neighbor_ids=nids,
    )
