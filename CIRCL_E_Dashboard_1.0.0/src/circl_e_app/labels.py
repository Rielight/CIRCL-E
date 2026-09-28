"""Display-only labels read from the frozen release metadata.

The dashboard must never invent, rename or expand a scientific term. This module
reads the authoritative strings that already ship inside the frozen release
(post-mapping criterion definitions and route rubrics) and exposes them for
presentation only.

It deliberately does **not** load the release, the reference bank or any
backbone: it reads two small CSVs and fails soft (returning empty mappings) when
they are unavailable, so the UI can fall back to the raw frozen identifiers.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

#: Display order of the five decision-support dimensions.
DIMENSION_ORDER = ("RRP", "WRO", "CSO", "TPC", "IRP")

#: Ordinal level labels as frozen in the post-mapping runtime.
LEVEL_LABELS = {1: "LOW", 2: "MODERATE-LOW", 3: "MODERATE-HIGH", 4: "HIGH"}


@lru_cache(maxsize=8)
def _read_rows(path_str: str) -> tuple[dict[str, str], ...]:
    try:
        with open(path_str, newline="", encoding="utf-8") as handle:
            return tuple(
                {key: (value if value is not None else "") for key, value in row.items()}
                for row in csv.DictReader(handle)
            )
    except Exception:  # noqa: BLE001 - labels must never break the dashboard
        return ()


def load_display_labels(release_dir: str | Path) -> dict[str, Any]:
    """Return authoritative, presentation-only labels for one release directory."""
    root = Path(release_dir)
    postmapping = root / "postmapping"

    criteria: dict[str, dict[str, Any]] = {}
    dimensions: dict[str, list[dict[str, str]]] = {}

    for row in _read_rows(str(postmapping / "criterion_definitions.csv")):
        dim = (row.get("score_dimension") or "").strip()
        cid = (row.get("criterion_id") or "").strip()
        if not dim or not cid:
            continue
        name = (row.get("criterion_name") or "").strip()
        criteria[cid] = {
            "dimension": dim,
            "name": name,
            "meaning": (row.get("meaning") or "").strip(),
            "validity_role": (row.get("validity_role") or "").strip(),
        }
        dimensions.setdefault(dim, []).append({"criterion_id": cid, "name": name})

    ordered_dimensions = {d: dimensions[d] for d in DIMENSION_ORDER if d in dimensions}
    for dim in sorted(dimensions):
        ordered_dimensions.setdefault(dim, dimensions[dim])

    route_interpretation = None
    for row in _read_rows(str(postmapping / "parent_route_affinity_map.csv")):
        text = (row.get("interpretation") or "").strip()
        if text:
            route_interpretation = text
            break

    return {
        "dimensions": ordered_dimensions,
        "criteria": criteria,
        "route_interpretation": route_interpretation,
    }
