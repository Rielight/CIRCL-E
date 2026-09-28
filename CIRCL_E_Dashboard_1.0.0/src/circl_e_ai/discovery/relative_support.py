"""Post-mapping relative assignment support under a frozen parent cohort."""
from __future__ import annotations
from circl_e_ai.attributes.factor_state import empirical_percentile


def parent_support_relative_state(score: float | None, parent_id: int | None,
                                  discovery_status: str, release) -> dict:
    """Reproduce the source within-parent parent-support state for a new image.

    The source ranks accepted parent assignment-support scores within each
    frozen parent using average percentile rank, then labels top 25% HIGH,
    middle 50% MEDIUM, bottom 25% LOW. This is not probability.
    """
    if discovery_status == "unknown_mixed" or parent_id is None or score is None:
        return {"state": "UNRESOLVED", "percentile": None}
    ref = release.assets.reference["parent_support_scores_by_parent"][int(parent_id)]
    pct = empirical_percentile(float(score), ref)
    state = (
        "HIGH_RELATIVE_SUPPORT" if pct >= 0.75
        else "MEDIUM_RELATIVE_SUPPORT" if pct >= 0.25
        else "LOW_RELATIVE_SUPPORT"
    )
    return {"state": state, "percentile": pct}
