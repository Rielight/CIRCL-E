"""Release integrity/shape/compatibility checks."""
from __future__ import annotations
from pathlib import Path
import hashlib,json

def sha256_file(p:Path,block=1<<20):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(block),b''): h.update(b)
    return h.hexdigest()

def verify_release_tree(root) -> list[str]:
    root=Path(root); errors=[]
    mp=root/'manifest.json'
    if not mp.is_file(): return ['MISSING_MANIFEST']
    m=json.loads(mp.read_text())
    for rel,digest in m.get('files',{}).items():
        p=root/rel
        if not p.is_file(): errors.append(f'MISSING:{rel}')
        elif sha256_file(p)!=digest: errors.append(f'HASH_MISMATCH:{rel}')
    required=['discovery/handoff/final_method_config.json','generated/reference/core.npz','generated/reference/root_support.npz','generated/reference/distributions.npz','generated/reference/factor_scores.npz','generated/ood/ood_reference.npz','generated/ood/ood_policy.json','semantics/semantic_structure_map.csv','semantics/factor_semantics.csv','semantics/patch_semantics.csv','postmapping/criterion_evidence_map.csv','postmapping/semantic_permission_registry.csv','postmapping/semantic_transition_registry.csv','postmapping/continuous_transition_registry.csv','postmapping/parent_route_affinity_map.csv','postmapping/route_resolution_rule_registry.csv']
    for rel in required:
        if not (root/rel).is_file(): errors.append(f'MISSING_REQUIRED:{rel}')
    return errors
