"""Pure frozen OOD/reference-conformity threshold policy."""
from __future__ import annotations


def classify_reference_state(metrics: dict, policy: dict) -> tuple[str, list[str]]:
    """Classify using release-frozen distance/percentile thresholds.

    Recommended policy data contains percentile thresholds such as
    ``caution_percentile`` and ``outside_percentile``. Higher distance percentile
    means less reference-like. The function is intentionally simple/auditable.
    """
    caution = float(policy.get("caution_percentile", 0.95))
    outside = float(policy.get("outside_percentile", 0.99))
    gp = metrics.get("global_percentile")
    pp = metrics.get("parent_percentile")
    vals = [x for x in (gp, pp) if x is not None]
    if not vals:
        return "CAUTION", ["OOD_METRICS_UNRESOLVED"]
    worst = max(vals)
    if worst >= outside:
        reasons = [name for name, val in (("GLOBAL_DISTANCE", gp), ("PARENT_DISTANCE", pp)) if val is not None and val >= outside]
        return "OUTSIDE_REFERENCE", reasons
    if worst >= caution:
        reasons = [name for name, val in (("GLOBAL_DISTANCE", gp), ("PARENT_DISTANCE", pp)) if val is not None and val >= caution]
        return "CAUTION", reasons
    return "IN_REFERENCE", []
