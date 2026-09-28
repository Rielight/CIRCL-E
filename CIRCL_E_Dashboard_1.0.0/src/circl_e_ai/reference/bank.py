"""Frozen canonical-row-aligned reference bank."""
from dataclasses import dataclass
from typing import Any

@dataclass
class ReferenceBank:
    canonical_ids: Any
    parent_ids: Any
    fine_ids: Any
    raw_visual_ids: Any
    G_whole: Any
    G_foreground: Any
    G_dual: Any
    L_whole: Any
    L_foreground: Any
    L_dual: Any
    HSOFT: Any
    HFG_hires: Any
    patch_stats: Any
    patch_prototypes: Any
