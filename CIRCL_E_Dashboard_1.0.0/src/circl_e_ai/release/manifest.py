"""Immutable CIRCL-E AI release manifest."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass(frozen=True)
class ReleaseManifest:
    release_id: str
    verified: bool
    discovery_version: str
    semantic_version: str
    postmapping_version: str
    files: dict[str,str]=field(default_factory=dict)
    schema_version: str="2.0"
    created_at: str|None=None
    backbones: dict=field(default_factory=dict)
    source_freezes: dict=field(default_factory=dict)
    training_environment: dict=field(default_factory=dict)
    notes: list[str]=field(default_factory=list)

    @classmethod
    def load(cls,path:Path)->"ReleaseManifest":
        data=json.loads(path.read_text()); known={f.name for f in __import__('dataclasses').fields(cls)}
        return cls(**{k:v for k,v in data.items() if k in known})
    def dump(self,path:Path):
        import dataclasses
        path.write_text(json.dumps(dataclasses.asdict(self),indent=2,sort_keys=True))
