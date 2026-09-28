"""Frozen hierarchical evidence/model sensitivity for a single image.

This mirrors the source notebook's 256 deterministic balanced scenarios. It is
technical robustness metadata, not a statistical confidence interval or probability.
"""
from __future__ import annotations
import ast, hashlib, json, math
import numpy as np
from .dimensions import compute_rrp, compute_wro, compute_cso, compute_tpc
from .transitions import active_rules, apply_action
from .routes import ROUTES, base_route_anchors

N_SCENARIOS=256
SCENARIO_SEED=20260925


def _parse_list(v):
    if isinstance(v,list): return v
    if v is None: return []
    if isinstance(v,float) and math.isnan(v): return []
    if isinstance(v,str):
        for fn in (json.loads,ast.literal_eval):
            try:
                x=fn(v); return list(x) if isinstance(x,(list,tuple)) else []
            except Exception: pass
    return []


def balanced_sequence(options, n, key):
    opts=list(options)
    if not opts: return np.full(n,np.nan,dtype=object)
    if len(opts)==1: return np.full(n,opts[0],dtype=object)
    arr=np.resize(np.array(opts,dtype=object),n)
    seed=(int(hashlib.sha256(str(key).encode('utf-8')).hexdigest()[:8],16)+SCENARIO_SEED)%(2**32-1)
    rng=np.random.default_rng(seed); rng.shuffle(arr); return arr


def _isnan(v):
    return v is None or (isinstance(v,float) and math.isnan(v))


def _aggregate(criteria):
    return {
        "RRP": compute_rrp(criteria),
        "WRO": compute_wro(criteria),
        "CSO": compute_cso(criteria),
        "TPC": compute_tpc(criteria),
    }


def compute_sensitivity(context, central_profile, permissions, release) -> dict:
    anchors=central_profile["anchor_bundle"]
    pid=int(context["parent_id"])
    scoreable=context["discovery_status"]!="unknown_mixed" and pid not in {0,8}

    anchor_seq={}
    for cid,m in anchors["metadata"].items():
        ref=m.get("reference_level"); origin=str(m.get("anchor_origin"))
        if ref is None and origin in {"FROZEN_SEMANTIC","UNSUPPORTED"}: opts=[np.nan]
        else:
            opts=_parse_list(m.get("allowed_levels")) or [np.nan]
        anchor_seq[cid]=balanced_sequence(opts,N_SCENARIOS,f"anchor:{pid}:{cid}")

    all_active={r["rule_id"]:r for kind in ("criterion","route") for r in active_rules(context,permissions,release,kind)}
    rule_seq={rid:balanced_sequence(_parse_list(r.get("scenario_actions")) or [r.get("action")],N_SCENARIOS,f"rule:{rid}") for rid,r in all_active.items()}

    dim_values={d:[] for d in ("RRP","WRO","CSO","TPC")}
    route_values={r:[] for r in ROUTES}
    route_top_sets=[]
    base_routes,route_meta=base_route_anchors(context,release)

    for s in range(N_SCENARIOS):
        crit={cid:(None if _isnan(seq[s]) else int(seq[s])) for cid,seq in anchor_seq.items()}
        if not scoreable:
            crit={cid:None for cid in crit}
        for r in active_rules(context,permissions,release,"criterion"):
            act=rule_seq[r["rule_id"]][s]
            if _isnan(act) or act=="NO_CHANGE": continue
            crit[r["target_id"]]=apply_action(crit.get(r["target_id"]),str(act))
        dims=_aggregate(crit)
        for d,v in dims.items(): dim_values[d].append(v)

        routes={}
        for rid,base in base_routes.items():
            m=route_meta.get(rid,{})
            opts=_parse_list(m.get("allowed_levels")) or [np.nan]
            seq=balanced_sequence(opts,N_SCENARIOS,f"route:{pid}:{rid}")
            val=seq[s]; routes[rid]=None if _isnan(val) else int(val)
        for r in active_rules(context,permissions,release,"route"):
            act=rule_seq[r["rule_id"]][s]
            if _isnan(act) or act=="NO_CHANGE": continue
            routes[r["target_id"]]=apply_action(routes.get(r["target_id"]),str(act))
        if context["discovery_status"]=="unknown_mixed":
            for rid in ["reuse_refurbish","parts_harvest","bulk_material_recovery","specialist_pcb","battery_specialist","crt_specialist"]: routes[rid]=None
            routes["sorting_dismantling"]=4; routes["residual_treatment"]=3
        for rid in ROUTES: route_values[rid].append(routes.get(rid))
        vals={k:v for k,v in routes.items() if v is not None}
        if vals:
            mx=max(vals.values()); route_top_sets.append(sorted([k for k,v in vals.items() if v==mx]))
        else: route_top_sets.append([])

    def mm(vals):
        x=[int(v) for v in vals if v is not None and not _isnan(v)]
        return (min(x),max(x)) if x else (None,None)
    dims_out={}
    for d,vals in dim_values.items():
        lo,hi=mm(vals); ref=central_profile["decision_support"][d].get("level")
        valid=[int(v) for v in vals if v is not None and not _isnan(v)]
        retention=None if ref is None or not valid else float(np.mean(np.asarray(valid)==int(ref)))
        dims_out[d]={"model_min":lo,"model_max":hi,"reference_level_retention":retention}
    routes_out={}
    for rid,vals in route_values.items():
        lo,hi=mm(vals); routes_out[rid]={"model_min":lo,"model_max":hi}
    refset=central_profile["routes"].get("highest_affinity_route_set",[])
    valid_sets=[x for x in route_top_sets if x]
    set_ret=None if not valid_sets else float(np.mean([x==refset for x in valid_sets]))
    return {
        "dimensions":dims_out,
        "routes":routes_out,
        "route_reference_set_retention":set_ret,
        "n_scenarios":N_SCENARIOS,
        "scenario_seed":SCENARIO_SEED,
        "interpretation":"declared evidence/model sensitivity range; not confidence interval or probability",
    }
