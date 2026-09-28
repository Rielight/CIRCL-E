"""Scientific result invariants checked for every frozen inference."""
from __future__ import annotations
from dataclasses import asdict, is_dataclass


def _obj(x): return asdict(x) if is_dataclass(x) else x

def validate_inference_result(result) -> None:
    r=_obj(result)
    ref=_obj(r['reference']); disc=_obj(r['discovery']); attrs=_obj(r['attributes'])
    decision=r.get('decision_support',{}); routes=r.get('routes',{})
    if ref['state'] not in {'IN_REFERENCE','CAUTION','OUTSIDE_REFERENCE'}:
        raise AssertionError('invalid reference state')
    if disc['discovery_status'] not in {'unknown_mixed','reliable_parent_only','reliable_parent_and_fine_group'}:
        raise AssertionError('invalid discovery status')
    if disc['discovery_status']=='reliable_parent_and_fine_group' and disc.get('fine_id') is None:
        raise AssertionError('fine-resolved status requires fine_id')
    if disc['discovery_status']=='unknown_mixed':
        sem=r.get('semantics',[])
        if any(x.get('role') not in {'diagnostic'} for x in sem if isinstance(x,dict)):
            raise AssertionError('unknown_mixed must not publish substantive semantics')
    for row in attrs.get('family_ica',[]):
        if row.get('parent_id') is None or row.get('comparable_across_parents') is not False:
            raise AssertionError('family ICA must retain parent scope and non-comparability')
    wro=decision.get('WRO',{})
    if wro.get('profile_status')=='NOT_APPLICABLE_COMPONENT_LEVEL' and wro.get('level') is not None:
        raise AssertionError('component-level WRO must not have numeric resolved level')
    if routes and routes.get('profile_status') != 'SUPPRESSED_OUTSIDE_REFERENCE':
        interp=str(routes.get('interpretation','')).lower()
        if 'compatibility' not in interp or 'not recommendation' not in interp:
            raise AssertionError('route outputs must remain compatibility, not recommendations')
    irp=decision.get('IRP',{})
    if irp and irp.get('profile_status') != 'SUPPRESSED_OUTSIDE_REFERENCE':
        interp=str(irp.get('interpretation','')).lower()
        if 'relative inspection/resolution priority' not in interp or 'not risk' not in interp:
            raise AssertionError('IRP interpretation invariant failed')
    # Support and OOD are deliberately independent concepts.
    if 'reference' not in r or not disc.get('parent_support'):
        raise AssertionError('reference gate and assignment support must both be present')
