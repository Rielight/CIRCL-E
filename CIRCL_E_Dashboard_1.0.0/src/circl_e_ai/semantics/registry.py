"""Reviewed Stage-2 semantic registry normalization."""
from __future__ import annotations
import math


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def records(df_or_records):
    if hasattr(df_or_records, "to_dict"):
        rows = df_or_records.to_dict("records")
    else:
        rows = list(df_or_records or [])
    return [{k: _clean(v) for k, v in row.items()} for row in rows]


def load_semantic_registries(release) -> dict:
    sem = release.assets.semantics
    return {
        "structure": records(sem["semantic_structure_map"]),
        "factors": records(sem["factor_semantics"]),
        "patch": records(sem["patch_semantics"]),
        "ontology": sem.get("ontology"),
        "manifest": sem.get("mapping_manifest"),
    }
