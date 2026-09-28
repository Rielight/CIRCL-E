"""Conservative publication policy for information-card semantics."""
from __future__ import annotations


def publication_filter(semantics, reference_state: str, discovery_status: str, release) -> list[dict]:
    if discovery_status == "unknown_mixed":
        return [{
            "semantic_key": "diagnostic:unresolved_visual_assignment",
            "label": "Unresolved / mixed visual assignment",
            "role": "diagnostic",
            "status": "unresolved",
            "confidence": None,
            "rationale": "Frozen routing-support requirements were not met; no device/subtype assertion is published.",
        }]
    if reference_state == "OUTSIDE_REFERENCE":
        return [{
            "semantic_key": "diagnostic:outside_reference",
            "label": "Outside frozen reference domain",
            "role": "diagnostic",
            "status": "outside_reference",
            "confidence": None,
            "rationale": "Deployment reference-conformity gate suppresses substantive semantic publication.",
        }]
    out = []
    for r in semantics:
        q = dict(r)
        if reference_state == "CAUTION":
            q["deployment_caution"] = True
        out.append(q)
    return out
