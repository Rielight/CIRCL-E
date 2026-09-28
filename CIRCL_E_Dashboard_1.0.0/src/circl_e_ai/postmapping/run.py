"""Frozen single-image post-mapping orchestrator."""
from __future__ import annotations
import math
from .permissions import permitted_rules
from .evidence import resolve_criterion_anchors
from .transitions import apply_semantic_transitions
from .dimensions import compute_rrp, compute_wro, compute_cso, compute_tpc, compute_irp
from .routes import compute_routes
from .sensitivity import compute_sensitivity

LEVEL_LABEL={1:"LOW",2:"MODERATE-LOW",3:"MODERATE-HIGH",4:"HIGH"}


def _derive_irp_b_map(release):
    pm=release.assets.postmapping
    if "irp_b_by_parent" in pm: return pm["irp_b_by_parent"]
    obj=pm["criterion_evidence_map"]
    rows=obj.to_dict("records") if hasattr(obj,"to_dict") else list(obj)
    out={}; mandatory={"RRP_A_resource_relevance","WRO_A_product_reuse","CSO_A_component_salvage"}
    image_state={"WRO_B_visual_integrity","WRO_C_configuration_completeness","CSO_B_accessibility_dismantling"}
    for pid in range(16):
        g=[r for r in rows if int(r["parent_id"])==pid]
        if pid in {0,8}: lvl,reason=4,"IRP_B_RESIDUAL_SCENE"
        elif any(r["criterion_id"] in mandatory and (r.get("reference_level") is None or (isinstance(r.get("reference_level"),float) and math.isnan(r["reference_level"]))) for r in g): lvl,reason=3,"IRP_B_MANDATORY_UNRESOLVED"
        else:
            inherent=[r for r in g if r["criterion_id"] not in image_state]
            high_share=sum(str(r.get("transfer_risk"))=="HIGH" for r in inherent)/max(1,len(inherent))
            model_share=sum(str(r.get("anchor_origin"))=="MODEL_RATIONALE" for r in inherent)/max(1,len(inherent))
            if high_share>=.5: lvl,reason=3,"IRP_B_HIGH_TRANSFER"
            elif model_share>=.5: lvl,reason=3,"IRP_B_MODEL_RATIONALE"
            elif any(str(r.get("transfer_risk"))=="HIGH" or str(r.get("anchor_origin"))=="MODEL_RATIONALE" for r in inherent): lvl,reason=2,"IRP_B_MIXED"
            else: lvl,reason=1,"IRP_B_STRONG"
        out[pid]={"level":lvl,"rule_id":reason}
    pm["irp_b_by_parent"]=out
    return out


def _dimension_record(level, criterion_values, applied, anchor_bundle, dim):
    cids=[k for k in criterion_values if k.startswith(dim+"_")]
    origins=sorted(set(str(anchor_bundle["metadata"][c].get("anchor_origin")) for c in cids if c in anchor_bundle["metadata"]))
    drivers=[]
    for c in cids:
        r=anchor_bundle["metadata"].get(c,{}).get("rationale")
        if isinstance(r,str) and len(r)>8: drivers.append(r)
    drivers += [r.get("rationale") for r in applied if str(r.get("target_id","")).startswith(dim+"_") and r.get("rationale")]
    drivers=list(dict.fromkeys(drivers))
    return {"level":level,"label":LEVEL_LABEL.get(level,"UNRESOLVED") if level is not None else "UNRESOLVED","criteria":{c:criterion_values.get(c) for c in cids},"anchor_origin_summary":";".join(origins),"applied_rule_ids":[r["rule_id"] for r in applied if str(r.get("target_id","")).startswith(dim+"_")],"main_drivers":drivers or ["No defensible class/image-specific driver beyond the unresolved state."]}


def run_postmapping(context, release, *, with_sensitivity: bool = True):
    # Cache/derive IRP-B map before compute_irp accesses it.
    _derive_irp_b_map(release)
    permissions=permitted_rules(context,release)
    if permissions["issues"]:
        raise RuntimeError("Semantic permission invariant failed: "+"; ".join(permissions["issues"]))
    anchors=resolve_criterion_anchors(context,release)
    criteria,applied=apply_semantic_transitions(anchors["criteria"],context,permissions,release)
    scoreable=context["discovery_status"]!="unknown_mixed" and int(context["parent_id"]) not in {0,8}
    if not scoreable: criteria={k:None for k in criteria}

    levels={"RRP":compute_rrp(criteria),"WRO":compute_wro(criteria),"CSO":compute_cso(criteria),"TPC":compute_tpc(criteria)}
    decision={d:_dimension_record(levels[d],criteria,applied,anchors,d) for d in levels}

    applicability=anchors.get("whole_device_reuse_applicability")
    wro_meta=anchors["metadata"].get("WRO_A_product_reuse",{})
    class_anchor=wro_meta.get("reference_level")
    if context["discovery_status"]=="unknown_mixed" or applicability!="WHOLE_DEVICE": class_anchor=None
    if context["discovery_status"]=="unknown_mixed": wro_status="UNRESOLVED_VISUAL_ASSIGNMENT"
    elif applicability=="COMPONENT_LEVEL_NA": wro_status="NOT_APPLICABLE_COMPONENT_LEVEL"
    elif applicability=="SCENE_OR_RESIDUAL_NA": wro_status="NOT_APPLICABLE_SCENE_OR_RESIDUAL"
    elif levels["WRO"] is not None: wro_status="RESOLVED_IMAGE_CONDITIONED"
    else: wro_status="UNRESOLVED_IMAGE_STATE"
    image_state=("REVIEWED_IMAGE_STATE_AVAILABLE" if wro_status=="RESOLVED_IMAGE_CONDITIONED" else "NO_REVIEWED_IMAGE_STATE_CUE" if wro_status=="UNRESOLVED_IMAGE_STATE" else "NOT_APPLICABLE" if wro_status.startswith("NOT_APPLICABLE") else "UNRESOLVED_ASSIGNMENT")
    decision["WRO"].update({"whole_device_reuse_applicability":applicability,"class_reuse_anchor_level":class_anchor,"class_reuse_anchor_label":LEVEL_LABEL.get(class_anchor) if class_anchor else None,"class_reuse_anchor_origin":wro_meta.get("anchor_origin") if class_anchor is not None else "UNRESOLVED_OR_NOT_APPLICABLE","profile_status":wro_status,"image_state_status":image_state})

    irp_context={**context,"evidence_anchor_rows":anchors["rows"]}
    irp=compute_irp(irp_context,release)
    irp["label"]=LEVEL_LABEL[int(irp["level"])]
    decision["IRP"]=irp
    routes=compute_routes(context,permissions,release)
    central={"decision_support":decision,"routes":routes,"criteria":criteria,"applied_transition_rules":applied,"permissions":permissions,"anchor_bundle":anchors}
    sensitivity=compute_sensitivity(context,central,permissions,release) if with_sensitivity else {}
    return {"decision_support":decision,"routes":routes,"sensitivity":sensitivity,"criteria":criteria,"applied_transition_rules":applied,"permissions":{"issues":permissions["issues"],"central_rule_ids":sorted(permissions["central_rule_ids"]),"sensitivity_rule_ids":sorted(permissions["sensitivity_rule_ids"])} ,"evidence":{"whole_device_reuse_applicability":applicability,"criterion_metadata":anchors["metadata"]},"profile_status":"UNRESOLVED_VISUAL_ASSIGNMENT" if context["discovery_status"]=="unknown_mixed" else "UNRESOLVED_ITEM_PROFILE_SCENE_OR_RESIDUAL" if int(context["parent_id"]) in {0,8} else "FINAL_ORDINAL_PROFILE","nonclaims":"not monetary value/price/payout/profit; not functionality probability; not exact composition; not battery chemistry; not legal classification; not calibrated assignment probability; not route optimality probability; ordinal levels are not a ratio scale"}
