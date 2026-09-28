"""Frozen ordinal route compatibility/affinity for one image."""
from __future__ import annotations
import ast, json, math
from .transitions import apply_central_transitions

ROUTES=("reuse_refurbish","parts_harvest","bulk_material_recovery","specialist_pcb","battery_specialist","crt_specialist","sorting_dismantling","residual_treatment")


def _records(obj): return obj.to_dict("records") if hasattr(obj,"to_dict") else list(obj or [])
def _none(v): return v is None or (isinstance(v,float) and math.isnan(v))
def _list(v):
    if isinstance(v,list): return v
    if isinstance(v,str):
        for fn in (json.loads,ast.literal_eval):
            try:
                x=fn(v); return list(x) if isinstance(x,(list,tuple)) else []
            except Exception: pass
    return []


def base_route_anchors(context, release):
    pid=int(context["parent_id"]); out={r:None for r in ROUTES}; meta={}
    for row in _records(release.assets.postmapping["parent_route_affinity_map"]):
        if int(row["parent_id"]) != pid: continue
        rid=str(row["route_id"]); val=None if _none(row.get("reference_level")) else int(row["reference_level"])
        out[rid]=val; meta[rid]=dict(row)
    return out,meta


def _resolve_unknown(routes, context, release):
    if context["discovery_status"] != "unknown_mixed": return routes,[]
    out=dict(routes); applied=[]
    rows=sorted(_records(release.assets.postmapping["route_resolution_rule_registry"]),key=lambda r:int(r.get("priority",0)))
    for r in rows:
        if str(r.get("condition")) != "discovery_status == unknown_mixed": continue
        targets=_list(r.get("target_routes"))
        for route in targets:
            if r["action"]=="SET_UNRESOLVED": out[route]=None
            elif r["action"]=="SET_LEVEL": out[route]=int(float(r["level"]))
            else: raise ValueError(r["action"])
        applied.append(str(r["rule_id"]))
    return out,applied


def _top(routes):
    vals={k:int(v) for k,v in routes.items() if v is not None}
    if not vals: return {"highest_affinity_route_set":[],"highest_affinity_level":None,"highest_affinity_route":"UNRESOLVED","route_margin":None,"second_route_set":[]}
    mx=max(vals.values()); top=sorted([k for k,v in vals.items() if v==mx]); uniq=sorted(set(vals.values()),reverse=True)
    sec=uniq[1] if len(uniq)>1 else None; second=sorted([k for k,v in vals.items() if sec is not None and v==sec])
    return {"highest_affinity_route_set":top,"highest_affinity_level":mx,"highest_affinity_route":top[0] if len(top)==1 else "TIE","route_margin":0 if len(top)>1 else (mx-sec if sec is not None else None),"second_route_set":second}


def compute_routes(context, permissions, release) -> dict:
    base,meta=base_route_anchors(context,release)
    central,applied=apply_central_transitions(base,context,permissions,release,"route")
    final,resolution=_resolve_unknown(central,context,release)
    pid=int(context["parent_id"])
    status=("DIAGNOSTIC_FALLBACK_UNRESOLVED_ASSIGNMENT" if context["discovery_status"]=="unknown_mixed" else "SCENE_OR_RESIDUAL_COMPATIBILITY" if pid in {0,8} else "ITEM_LEVEL_COMPATIBILITY")
    return {"levels":final,"profile_status":status,"applied_rule_ids":[r["rule_id"] for r in applied],"resolution_rule_ids":resolution,"base_metadata":meta,**_top(final),"interpretation":"ordinal route compatibility/affinity; not recommendation, optimality probability or profitability estimate"}
