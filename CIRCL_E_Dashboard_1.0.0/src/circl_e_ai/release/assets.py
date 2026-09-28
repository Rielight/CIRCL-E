"""Typed container for immutable runtime assets."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class FrozenAssets:
    cradio_model: Any=None; cradio_processor: Any=None; dino_model: Any=None; dino_processor: Any=None
    transforms: dict[str,Any]=field(default_factory=dict)
    runtime_config: dict[str,Any]=field(default_factory=dict)
    root_model: Any=None; root_remap: dict[int,int]=field(default_factory=dict)
    fine_models: dict[int,Any]=field(default_factory=dict); raw_models: dict[int,Any]=field(default_factory=dict)
    support_models: dict[str,Any]=field(default_factory=dict); method_config: dict=field(default_factory=dict)
    reference: dict[str,Any]=field(default_factory=dict)
    global_ica: Any=None; global_ica_postmap: Any=None
    family_ica: dict[int,Any]=field(default_factory=dict); family_ica_postmap: dict[int,Any]=field(default_factory=dict)
    patch_prototypes: Any=None
    ood: dict=field(default_factory=dict); semantics: dict=field(default_factory=dict); postmapping: dict=field(default_factory=dict)
