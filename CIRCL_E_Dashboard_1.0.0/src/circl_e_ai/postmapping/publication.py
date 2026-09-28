"""Deployment publication guard layered over source-faithful post-mapping.

OOD/reference conformity is a new deployment concept, not part of the original
post-mapping methodology. Therefore the internal source-faithful calculation is
retained for provenance, while substantive public decision-support is
suppressed when an upload is OUTSIDE_REFERENCE.
"""
from __future__ import annotations


def publication_filter(post: dict, reference_state: str) -> dict:
    if reference_state == 'IN_REFERENCE':
        return {'decision_support':post.get('decision_support',{}),'routes':post.get('routes',{}),'sensitivity':post.get('sensitivity',{})}
    if reference_state == 'CAUTION':
        decision={k:{**v,'deployment_caution':True} if isinstance(v,dict) else v for k,v in post.get('decision_support',{}).items()}
        routes={**post.get('routes',{}),'deployment_caution':True}
        return {'decision_support':decision,'routes':routes,'sensitivity':post.get('sensitivity',{})}
    return {
        'decision_support': {
            dim:{'level':None,'label':'SUPPRESSED_OUTSIDE_REFERENCE','profile_status':'SUPPRESSED_OUTSIDE_REFERENCE','reason':'Upload falls outside the frozen deployment reference domain; source-faithful internal values are retained only in the audit trace.'}
            for dim in ('RRP','WRO','CSO','TPC','IRP')
        },
        'routes': {'levels':{},'highest_affinity_route_set':[],'highest_affinity_level':None,'highest_affinity_route':'SUPPRESSED_OUTSIDE_REFERENCE','profile_status':'SUPPRESSED_OUTSIDE_REFERENCE','interpretation':'route affinity suppressed outside the frozen reference domain; not a recommendation'},
        'sensitivity': {},
    }
