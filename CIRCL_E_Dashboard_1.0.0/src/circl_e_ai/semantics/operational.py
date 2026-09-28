"""Stage-2-compatible operational semantic flattening.

The Stage-2 notebook deliberately separates:
- parent/fine fields that are operationally mapped only when routing is reliable;
- raw-visual semantics that are retained descriptively as provenance/evidence;
- continuous attributes and patch context, which are separate typed assertions.

This module reproduces the parent-then-fine precedence used for the exported
``mapped_*`` information-card fields without allowing raw visual labels to
silently become operational device/subtype fields.
"""
from __future__ import annotations

COMMON_FIELDS=(
    'device_family','device_subtype','component_type','condition','configuration',
    'viewpoint','scene_type','acquisition_style',
)


def flatten_operational_structure_semantics(assertions, discovery_status:str) -> dict:
    out={f'mapped_{c}':None for c in COMMON_FIELDS}
    out.update({'mapped_parent_label':None,'mapped_fine_label':None,'parent_semantic_confidence':None,'fine_semantic_confidence':None})
    if discovery_status == 'unknown_mixed':
        return out
    parents=[r for r in assertions if r.get('source_structure')=='parent']
    fines=[r for r in assertions if r.get('source_structure')=='fine']
    if parents:
        r=parents[0]; out['mapped_parent_label']=r.get('label'); out['parent_semantic_confidence']=r.get('confidence')
        for c in COMMON_FIELDS:
            v=r.get(c)
            if v is not None and str(v)!='': out[f'mapped_{c}']=v
    if discovery_status == 'reliable_parent_and_fine_group' and fines:
        r=fines[0]; out['mapped_fine_label']=r.get('label'); out['fine_semantic_confidence']=r.get('confidence')
        for c in COMMON_FIELDS:
            v=r.get(c)
            if v is not None and str(v)!='': out[f'mapped_{c}']=v
    return out
