"""Load one immutable AI release. No fitting occurs here."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json,re,platform,importlib.metadata
import numpy as np, pandas as pd, joblib
from .manifest import ReleaseManifest
from .assets import FrozenAssets
from .verifier import verify_release_tree

@dataclass
class FrozenRelease:
    root: Path
    manifest: ReleaseManifest
    assets: FrozenAssets

def _json(path): return json.loads(Path(path).read_text())
def _intdict(d): return {int(k):v for k,v in d.items()}
def _npzdict(path):
    z=np.load(path); return {k:z[k] for k in z.files}

def merge_backbone_paths(bound:dict|None, overrides:dict|None)->dict:
    """Merge manifest-bound backbone paths with deployment-time overrides.

    Only non-empty override values replace a bound path; an unset/blank override
    leaves the manifest value untouched (the historical behavior). Paths are the
    only thing this changes — the weights and files loaded are identical.
    """
    merged=dict(bound or {})
    for key,value in (overrides or {}).items():
        if value: merged[key]=value
    return merged

def _load_backbones(manifest,device,backbone_paths=None):
    import torch
    from transformers import AutoModel,AutoImageProcessor,CLIPImageProcessor
    b=merge_backbone_paths(manifest.backbones,backbone_paths)
    cp=b.get('cradio_path'); dp=b.get('dino_path')
    if not cp or not dp: raise RuntimeError('Manifest must bind local cradio_path and dino_path to run pixel inference')
    try:
        from timm.layers import set_fused_attn; set_fused_attn(False)
    except Exception: pass
    dev=torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
    cproc=CLIPImageProcessor.from_pretrained(cp,local_files_only=True)
    cmodel=AutoModel.from_pretrained(cp,trust_remote_code=True,local_files_only=True,low_cpu_mem_usage=True).eval().to(dev,dtype=torch.float32)
    for p in cmodel.parameters(): p.requires_grad_(False)
    if hasattr(cmodel,'input_conditioner') and hasattr(cmodel.input_conditioner,'dtype'): cmodel.input_conditioner.dtype=torch.float32
    dproc=AutoImageProcessor.from_pretrained(dp,local_files_only=True)
    ddtype=torch.bfloat16 if dev.type=='cuda' and torch.cuda.is_bf16_supported() else torch.float16 if dev.type=='cuda' else torch.float32
    dmodel=AutoModel.from_pretrained(dp,local_files_only=True,low_cpu_mem_usage=True,dtype=ddtype,attn_implementation='sdpa').eval().to(dev)
    for p in dmodel.parameters(): p.requires_grad_(False)
    return cmodel,cproc,dmodel,dproc

def _check_environment(manifest, *, pixel_inference: bool):
    expected=manifest.training_environment or {}
    checks={'scikit-learn':'scikit-learn'}
    if pixel_inference: checks.update({'transformers':'transformers','timm':'timm'})
    errors=[]
    for key,pkg in checks.items():
        want=expected.get(key)
        if not want: continue
        try: got=importlib.metadata.version(pkg)
        except Exception: got=None
        if got != want: errors.append(f'{pkg}: expected {want}, got {got}')
    return errors

def load_release(root:str|Path,*,require_verified:bool=True,load_backbones:bool=True,device:str|None=None,strict_environment:bool=True,backbone_paths:dict|None=None)->FrozenRelease:
    root=Path(root); manifest=ReleaseManifest.load(root/'manifest.json')
    errs=verify_release_tree(root)
    if errs: raise RuntimeError('Release verification failed: '+'; '.join(errs[:20]))
    if require_verified and not manifest.verified: raise RuntimeError('Release is not marked verified/canonical')
    env_errors=_check_environment(manifest,pixel_inference=load_backbones)
    if strict_environment and env_errors: raise RuntimeError('Runtime environment does not match frozen source environment: '+'; '.join(env_errors))
    d=root/'discovery'; gen=root/'generated'; a=FrozenAssets()
    a.method_config=_json(d/'handoff/final_method_config.json')
    a.runtime_config={'dino_short':512,'dino_max_long':1024,'dino_mid_fraction':.75,'cradio_short':512,'cradio_max_long':1024,'attr_short':768,'attr_max_long':1024,'foreground_canvas':512,'foreground_margin':.04,'foreground_fill':(127,127,127)}
    a.transforms={
      'cradio_slot1_pca256':_npzdict(d/'models/cradio_slot1_pca256.npz'),
      'vlad_patch_pca64':_npzdict(d/'models/vlad_patch_pca64.npz'),
      'vlad32_centers':np.load(d/'models/vlad32_centers.npy'),
      'vlad32_pca512_alpha05':_npzdict(d/'models/vlad32_pca512_alpha05.npz'),
      'concept_mid_pca64':_npzdict(d/'models/concept_mid_pca64.npz'),
      'concept_late_pca64':_npzdict(d/'models/concept_late_pca64.npz'),
      'concept512_centers':np.load(d/'models/concept512_centers.npy'),
    }
    a.root_model=joblib.load(d/'models/root_kmeans.joblib'); a.root_remap=_intdict(_json(d/'models/root_label_remap.json'))
    maps=_json(gen/'reference/maps.json')
    ref={'fine_global_by_parent_local':{tuple(map(int,k.split('|'))):int(v) for k,v in maps['fine_local_to_global'].items()},'raw_global_by_parent_local':{tuple(map(int,k.split('|'))):int(v) for k,v in maps['raw_local_to_global'].items()}}
    for ps,spec in a.method_config['fine_selection_space']['selected'].items():
        pid=int(ps)
        if not spec.get('deployed'): continue
        pat=f"fine_parent_{pid:02d}_{spec['view']}_K{int(spec['k'])}.joblib"
        model=joblib.load(d/'models'/pat); rem=_intdict(_json(d/'models'/f'fine_parent_{pid:02d}_remap.json'))
        a.fine_models[pid]={'model':model,'remap':rem}
    for ps,spec in a.method_config['raw_visual_selection_space']['selected'].items():
        pid=int(ps)
        if spec['view']=='parent_only' or int(spec['k'])==1: continue
        model=joblib.load(d/'models'/f"raw_visual_parent_{pid:02d}_{spec['view']}_K{int(spec['k'])}.joblib")
        rem=_intdict(_json(d/'models'/f'raw_visual_parent_{pid:02d}_remap.json')); a.raw_models[pid]={'model':model,'remap':rem}
    pmeta=_json(d/'models/parent_confidence_meta.json'); fmeta=_json(d/'models/fine_confidence_meta.json')
    rel=pd.read_csv(d/'metrics/parent_reliability_selection.csv')
    a.support_models={'parent_calibrator':joblib.load(d/'models/parent_confidence_calibrator.joblib'),'parent_base_score':float(pmeta['base_score']),'parent_global_threshold':float(pmeta['global_threshold']),'parent_threshold_by_parent':_intdict(_json(d/'models/parent_confidence_thresholds.json')),'parent_operational_reliability':{int(r.parent_id):float(r.operational_reliability) for r in rel.itertuples()},'fine_calibrator_by_parent':{},'fine_meta_by_parent':{int(k):v for k,v in fmeta.items()}}
    for pid,meta in a.support_models['fine_meta_by_parent'].items():
        a.support_models['fine_calibrator_by_parent'][pid]=joblib.load(d/'models'/f'fine_confidence_parent_{pid:02d}.joblib')
    core=np.load(gen/'reference/core.npz'); rootb=np.load(gen/'reference/root_support.npz'); dist=np.load(gen/'reference/distributions.npz'); fs=np.load(gen/'reference/factor_scores.npz')
    ref.update({'canonical_id':core['canonical_id'],'parent_ids':core['parent_ids'],'identity_X':core['G_dual'],'hist512_base':core['hist512_base'],'hist512_hires_fg':core['hist512_hires_fg'],'patch_q99':core['patch_q99'],'root_support_X':rootb['X'],'root_support_parent_y':rootb['y'],'fine_support_by_parent':{},'parent_support_scores_by_parent':{},'fine_support_scores_by_global_fine':{},'patch_local_percentile_by_parent':{},'hist512_base_parent_mean':{},'hist512_hires_parent_mean':{},'factor_scores':{}})
    ref['hist512_base_global_mean']=dist['global_mean_base']; ref['hist512_hires_global_mean']=dist['global_mean_hires']
    for pid in range(16):
        ref['parent_support_scores_by_parent'][pid]=dist[f'parent_support_p{pid:02d}']; ref['patch_local_percentile_by_parent'][pid]=dist[f'patch_local_percentile_p{pid:02d}']; ref['hist512_base_parent_mean'][pid]=dist[f'parent_mean_base_p{pid:02d}']; ref['hist512_hires_parent_mean'][pid]=dist[f'parent_mean_hires_p{pid:02d}']
        fp=gen/'reference'/f'fine_support_parent_{pid:02d}.npz'
        if fp.is_file():
            z=np.load(fp); ref['fine_support_by_parent'][pid]={'X':z['X'],'global_fine_y':z['y']}
    for key in dist.files:
        m=re.fullmatch(r'fine_support_f(\d+)',key)
        if m: ref['fine_support_scores_by_global_fine'][int(m.group(1))]=dist[key]
    for key in fs.files:
        m=re.fullmatch(r'global_f(\d+)',key)
        if m: ref['factor_scores'][('global',None,int(m.group(1)))]=fs[key]; continue
        m=re.fullmatch(r'family_p(\d+)_f(\d+)',key)
        if m: ref['factor_scores'][('family',int(m.group(1)),int(m.group(2)))]=fs[key]
    a.reference=ref
    a.global_ica=joblib.load(d/f"models/global_ica_k{a.method_config['global_ica']['selected_neighbors']}_rank{a.method_config['global_ica']['selected_rank']}.joblib"); a.global_ica_postmap=np.load(d/'models/global_ica_postmap.npy')
    for ps,rank in a.method_config['family_ica']['selected_ranks'].items():
        pid=int(ps); a.family_ica[pid]=joblib.load(d/'models'/f'family_ica_parent_{pid:02d}_rank{int(rank)}.joblib'); a.family_ica_postmap[pid]=np.load(d/'models'/f'family_ica_parent_{pid:02d}_postmap.npy')
    a.patch_prototypes=np.load(d/'models/reference_patch_prototypes_g16.npy',mmap_mode='r')
    oz=np.load(gen/'ood/ood_reference.npz'); policy=_json(gen/'ood/ood_policy.json')
    a.ood={'k':int(policy['k']),'policy':policy,'reference_X':oz['reference_X'],'parent_ids':oz['parent_ids'],'loo_global_distances':oz['loo_global_distances'],'loo_parent_distances_by_parent':{pid:oz[f'loo_parent_p{pid:02d}'] for pid in range(16)}}
    a.semantics={'semantic_structure_map':pd.read_csv(root/'semantics/semantic_structure_map.csv'),'factor_semantics':pd.read_csv(root/'semantics/factor_semantics.csv'),'patch_semantics':pd.read_csv(root/'semantics/patch_semantics.csv'),'mapping_manifest':_json(root/'semantics/semantic_mapping_manifest.json') if (root/'semantics/semantic_mapping_manifest.json').is_file() else None,'ontology':_json(root/'semantics/semantic_ontology.json') if (root/'semantics/semantic_ontology.json').is_file() else None}
    a.postmapping={}
    for name in ['criterion_evidence_map','criterion_definitions','external_source_registry','semantic_permission_registry','semantic_transition_registry','continuous_transition_registry','parent_route_affinity_map','route_resolution_rule_registry','irp_rule_registry']:
        p=root/'postmapping'/f'{name}.csv'
        if p.is_file(): a.postmapping[name]=pd.read_csv(p)
    if load_backbones:
        a.cradio_model,a.cradio_processor,a.dino_model,a.dino_processor=_load_backbones(manifest,device,backbone_paths)
    return FrozenRelease(root=root,manifest=manifest,assets=a)
