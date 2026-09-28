"""Machine-readable causal/audit trace for one frozen inference."""
from __future__ import annotations
from dataclasses import asdict, is_dataclass


def _semantic_keys(rows):
    return [str(r.get('semantic_key')) for r in rows if isinstance(r,dict) and r.get('semantic_key')]


def _rule_ids(postmapping):
    out=[]
    out.extend(postmapping.get('applied_transition_rules',[]))
    ids=[]
    for r in out:
        if isinstance(r,dict) and r.get('rule_id'): ids.append(str(r['rule_id']))
    routes=postmapping.get('routes',{})
    ids += [str(x) for x in routes.get('applied_rule_ids',[])]
    ids += [str(x) for x in routes.get('resolution_rule_ids',[])]
    for d in postmapping.get('decision_support',{}).values():
        if isinstance(d,dict):
            ids += [str(x) for x in d.get('applied_rule_ids',[])]
            for v in d.get('criterion_rule_ids',{}).values(): ids += [str(x) for x in (v or [])]
    return list(dict.fromkeys(ids))


def _evidence_ids(postmapping):
    meta=postmapping.get('evidence',{}).get('criterion_metadata',{})
    ids=[]
    for row in meta.values():
        if not isinstance(row,dict): continue
        for key in ('source_ids','reference_source_ids','supporting_source_ids'):
            v=row.get(key)
            if isinstance(v,list): ids += [str(x) for x in v]
            elif isinstance(v,str) and v.strip():
                # preserve opaque serialized source sets as one auditable value
                ids.append(v)
        if row.get('source_id'): ids.append(str(row['source_id']))
    return list(dict.fromkeys(ids))


def build_provenance(release, features, reference, discovery, attributes, semantics, postmapping) -> dict:
    """Return traceable frozen inputs and causal rule/evidence identifiers.

    This intentionally records *which* frozen assets and reference rows were
    consulted without claiming that neighbor IDs or rule IDs are probabilities.
    """
    patch=attributes.patch or {}
    return {
        'release': {
            'release_id': release.manifest.release_id,
            'verified': bool(release.manifest.verified),
            'schema_version': release.manifest.schema_version,
            'discovery_version': release.manifest.discovery_version,
            'semantic_version': release.manifest.semantic_version,
            'postmapping_version': release.manifest.postmapping_version,
            'source_freezes': dict(release.manifest.source_freezes or {}),
            'manifest_file_count': len(release.manifest.files or {}),
        },
        'image': {'sha256': features.image_sha256, 'foreground_bbox': list(features.foreground_bbox)},
        'reference_gate': {
            'state': reference.state,
            'global_distance': reference.global_distance,
            'global_percentile': reference.global_percentile,
            'parent_distance': reference.parent_distance,
            'parent_percentile': reference.parent_percentile,
            'reasons': list(reference.reasons),
        },
        'discovery': {
            'provisional_parent_id': discovery.provisional_parent_id,
            'parent_id': discovery.parent_id,
            'fine_id': discovery.fine_id,
            'raw_visual_leaf_id': discovery.raw_visual_leaf_id,
            'discovery_status': discovery.discovery_status,
            'parent_support_neighbor_ids': list(discovery.parent_support.neighbor_ids),
            'fine_support_neighbor_ids': list(discovery.fine_support.neighbor_ids) if discovery.fine_support else [],
        },
        'attributes': {
            'identity_reference_neighbor_ids': list(patch.get('identity_reference_neighbor_ids',[])),
            'patch_reference_neighbor_ids': list(patch.get('reference_neighbor_ids',[])),
            'global_factor_states': {str(x['factor_id']):x.get('state') for x in attributes.global_ica},
            'family_factor_states': {str(x['factor_id']):x.get('state') for x in attributes.family_ica},
        },
        'semantics': {'semantic_keys': _semantic_keys(semantics)},
        'postmapping': {
            'rule_ids': _rule_ids(postmapping),
            'evidence_source_ids': _evidence_ids(postmapping),
            'profile_status': postmapping.get('profile_status'),
            'nonclaims': postmapping.get('nonclaims'),
        },
    }
