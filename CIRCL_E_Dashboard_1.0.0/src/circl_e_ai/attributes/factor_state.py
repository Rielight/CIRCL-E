"""Convert frozen ICA coordinates to source-compatible activation states.

The source post-mapping notebook derives factor states by applying
``Series.rank(pct=True, method='average')`` to the frozen reference cohort.
For an unseen image, we emulate the rank obtained if its score were appended to
that immutable reference distribution. Uploaded images are never allowed to
change one another's factor states.
"""
from __future__ import annotations
import numpy as np


def empirical_percentile(score: float, reference_scores) -> float:
    """Percentile of a new score under pandas average-rank insertion semantics.

    For ``n`` frozen reference scores, let L be the number strictly lower than
    the query and E the number exactly equal. Appending the query creates an
    equal-value group of size E+1 occupying ranks L+1..L+E+1. Its average rank
    is ``L + (E+2)/2`` and pandas ``pct=True`` divides by ``n+1``.

    Exact floating ties should be rare for ICA coordinates but the formula is
    explicit to make parity testable.
    """
    ref = np.asarray(reference_scores, dtype=float)
    ref = ref[np.isfinite(ref)]
    if not np.isfinite(score) or len(ref) == 0:
        return float("nan")
    lower = int(np.count_nonzero(ref < score))
    equal = int(np.count_nonzero(ref == score))
    avg_rank = lower + (equal + 2.0) / 2.0
    return float(avg_rank / (len(ref) + 1.0))


def state_from_percentile(pct: float) -> str:
    if not np.isfinite(pct):
        return "UNRESOLVED"
    if pct <= 0.20:
        return "STRONG_LOW"
    if pct >= 0.80:
        return "STRONG_HIGH"
    return "MID"


def factor_state(scope: str, parent_id: int | None, factor_id: int, score: float, release) -> dict:
    """Resolve an ICA score into a frozen-reference activation state.

    Global reference distributions span the full frozen canonical cohort.
    Family distributions are parent-specific and MUST NOT be compared across
    parents.
    """
    ref = release.assets.reference["factor_scores"][(scope, parent_id, factor_id)]
    pct = empirical_percentile(score, ref)
    return {
        "scope": scope,
        "parent_id": parent_id,
        "factor_id": factor_id,
        "score": float(score),
        "reference_percentile": pct,
        "state": state_from_percentile(pct),
        "comparable_across_parents": scope == "global",
    }
