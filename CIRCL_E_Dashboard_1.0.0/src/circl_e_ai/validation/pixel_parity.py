"""Pure helpers for the V1 raw-pixel -> frozen-feature parity gate.

Validation-only utilities: metric math, deterministic golden-sample selection,
farthest-point prototype reduction and the frozen-target comparison
specification. Nothing here trains, refits, recalibrates or mutates a frozen
asset, and none of it is imported by the online inference path.

The prototype reducer mirrors the discovery notebook's ``fps`` helper exactly so
that runtime dense descriptors can be compared against the frozen
``reference_patch_prototypes_g16`` artifact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from circl_e_ai.features.math import normalize_rows_l2


# A-priori parity gates. These are NOT tuned to observed golden-sample results:
# each band is derived from the numerical operation that produces the vector and
# the smallest divergence it can legitimately introduce. A representation is
# compact enough that a real preprocessing/backbone regression exceeds its band.
#
# - float32 PCA / VLAD vectors: matmul accumulation rounding floor ~1e-6, so a
#   1e-5 max-abs band (≈20x headroom) still catches any real divergence.
# - integer/histogram-derived vector (HFG_hires): deterministic accumulation, so
#   bit-exact on the same platform; 1e-6 tolerates only cross-platform rounding.
# - HSOFT: difference-of-normals histogram soft descriptor with bilinear
#   accumulation floor ~2e-4; 1e-3 band is justified by that accumulation.
# - dense_prototypes_g16: float16-quantized descriptor -> FPS selection; the
#   float16 rounding floor for an L2-normalized 128-D vector is ~1e-3, hence the
#   2e-3 band.
DEFAULT_VECTOR_TOLERANCE = {
    "cosine_min": 0.999,
    "rel_l2_max": 0.05,
    "max_abs_max": 0.05,
}

_FLOAT32_PCA = {"cosine_min": 1.0 - 1e-6, "rel_l2_max": 1e-5, "max_abs_max": 1e-5}
_HIST_EXACT = {"cosine_min": 1.0 - 1e-6, "rel_l2_max": 1e-6, "max_abs_max": 1e-6}
# HSOFT is a non-normalized difference-of-normals histogram whose frozen L2 norm
# varies ~0.09-0.36, so a fixed relative-L2 band is not an operation-invariant
# criterion (it conflates small target norm with error). Its derived gate is the
# per-bin absolute accumulation floor plus cosine shape agreement. rel_l2 stays
# reported as informational only.
_HSOFT = {"cosine_min": 0.9999, "rel_l2_max": None, "max_abs_max": 1e-3}
_F16_PROTO = {"cosine_min": 0.9999, "rel_l2_max": 2e-3, "max_abs_max": 2e-3}

OUTPUT_TOLERANCES = {
    "G_whole": _FLOAT32_PCA,
    "G_foreground": _FLOAT32_PCA,
    "G_dual": _FLOAT32_PCA,
    "L_whole": _FLOAT32_PCA,
    "L_foreground": _FLOAT32_PCA,
    "L_dual_vs_frozen_composition": _FLOAT32_PCA,
    "HFG_hires": _HIST_EXACT,
    "HFG_hires_vs_core": _HIST_EXACT,
    "HSOFT": _HSOFT,
    "HSOFT_vs_core": _HSOFT,
    "dense_prototypes_g16": _F16_PROTO,
}


def tolerance_for(output: str) -> dict[str, float]:
    """Return the fixed, semantics-justified tolerance band for ``output``."""
    return dict(OUTPUT_TOLERANCES.get(output, DEFAULT_VECTOR_TOLERANCE))

FROZEN_VECTOR_TARGETS = {
    "G_whole": ("discovery/views/G.npy", 256),
    "G_foreground": ("discovery/views/G_foreground.npy", 256),
    "G_dual": ("generated/reference/core.npz#G_dual", 512),
    "L_whole": ("discovery/views/L.npy", 512),
    "L_foreground": ("discovery/views/L_foreground.npy", 512),
    "HSOFT": ("discovery/views/HSOFT.npy", 512),
    "HFG_hires": ("discovery/attributes/hist512_hires_fg.npy", 512),
}

# Derived-from-frozen composition targets (no standalone frozen array exists).
FROZEN_COMPOSITION_TARGETS = {"L_dual": ("L_whole", "L_foreground", 0.5, 0.5)}

FROZEN_PATCH_PROTOTYPE_TARGET = "discovery/models/reference_patch_prototypes_g16.npy"


def vector_metrics(computed, target) -> dict[str, float]:
    """Cosine / L2 / max-abs / mean-abs agreement for two equal-length vectors."""
    a = np.asarray(computed, np.float64).ravel()
    b = np.asarray(target, np.float64).ravel()
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: computed {a.shape} vs target {b.shape}")
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    cos = float(np.dot(a, b) / max(na * nb, 1e-12))
    diff = a - b
    l2 = float(np.linalg.norm(diff))
    return {
        "cosine": cos,
        "l2": l2,
        "rel_l2": float(l2 / max(nb, 1e-12)),
        "max_abs": float(np.max(np.abs(diff))) if diff.size else 0.0,
        "mean_abs": float(np.mean(np.abs(diff))) if diff.size else 0.0,
    }


def scalar_metrics(computed, target) -> dict[str, float]:
    return {"abs_diff": float(abs(float(computed) - float(target)))}


def vector_passes(metrics: dict[str, float], tolerance: dict[str, float] | None = None) -> bool:
    """Apply a tolerance band; a criterion set to ``None`` is informational only."""
    tol = tolerance or DEFAULT_VECTOR_TOLERANCE
    cos_min = tol.get("cosine_min")
    rel_max = tol.get("rel_l2_max")
    mx_max = tol.get("max_abs_max")
    if cos_min is not None and metrics["cosine"] < cos_min:
        return False
    if rel_max is not None and metrics["rel_l2"] > rel_max:
        return False
    if mx_max is not None and metrics["max_abs"] > mx_max:
        return False
    return True


def compose_frozen_dual(a, b, wa: float = 0.5, wb: float = 0.5):
    """Notebook composition: normalize(concat(sqrt(wa)*normalize(a), sqrt(wb)*normalize(b)))."""
    return normalize_rows_l2(
        np.c_[
            np.sqrt(float(wa)) * normalize_rows_l2(a),
            np.sqrt(float(wb)) * normalize_rows_l2(b),
        ]
    )


def fps_prototypes(dense, k: int):
    """Exact copy of the discovery notebook's farthest-point prototype reducer.

    ``dense`` is the (256, 128) runtime grid descriptor; returns (min(k,N), 128).
    """
    X = normalize_rows_l2(np.asarray(dense, np.float32))
    k = min(int(k), len(X))
    if k <= 0:
        return X[:0]
    sel = [int(np.argmax(np.linalg.norm(X - X.mean(0), axis=1)))]
    mind = 1 - X @ X[sel[0]]
    for _ in range(1, k):
        j = int(np.argmax(mind))
        sel.append(j)
        mind = np.minimum(mind, 1 - X @ X[j])
    return X[sel]


def _add(selected: dict[int, list[str]], idx: int, reason: str) -> None:
    selected.setdefault(int(idx), [])
    if reason not in selected[int(idx)]:
        selected[int(idx)].append(reason)


def select_golden_sample(
    per,
    G_whole,
    G_foreground,
    *,
    n_target: int = 40,
    foreground_extra: int = 4,
    ica_extra: int = 4,
) -> list[dict[str, Any]]:
    """Deterministically choose a small representative golden cohort.

    Covers every parent with a patch-heavy row and a reliable/typical fine row,
    then adds globally foreground-distinctive and ICA-extreme rows. Selection is
    a pure function of the frozen row metadata and frozen G views: reruns pick
    exactly the same canonical indices.
    """
    per = per.sort_values("canonical_index").reset_index(drop=True)
    parents = per.raw_parent_id.to_numpy(int)
    patch = per.patch_q99.to_numpy(float)
    status = per.discovery_status.astype(str).to_numpy()
    Gw = normalize_rows_l2(np.asarray(G_whole, np.float32))
    Gf = normalize_rows_l2(np.asarray(G_foreground, np.float32))
    selected: dict[int, list[str]] = {}

    for pid in range(16):
        idxs = np.flatnonzero(parents == pid)
        if not len(idxs):
            continue
        patch_idx = int(idxs[int(np.argmax(patch[idxs]))])
        _add(selected, patch_idx, f"parent{pid}:max_patch_q99")
        med = float(np.median(patch[idxs]))
        reliable = idxs[status[idxs] == "reliable_parent_and_fine_group"]
        pool = reliable if len(reliable) else idxs
        fine_idx = int(pool[int(np.argmin(np.abs(patch[pool] - med)))])
        _add(selected, fine_idx, f"parent{pid}:typical_reliable")

    # Foreground-distinctive rows: lowest whole<->foreground cosine globally.
    cos_gf = np.sum(Gw * Gf, axis=1)
    order_fg = np.argsort(cos_gf, kind="stable")
    for idx in order_fg:
        if len(selected) >= 32 + foreground_extra and int(idx) not in selected:
            break
        if int(idx) not in selected:
            _add(selected, int(idx), "foreground_distinctive")
        if sum("foreground_distinctive" in v for v in selected.values()) >= foreground_extra:
            break

    # ICA-extreme rows: largest available family ICA magnitude, else global_ica_00.
    fam_cols = [c for c in per.columns if c.startswith("family_ica__")]
    ica = np.zeros(len(per), np.float32)
    if fam_cols:
        fam = np.nan_to_num(per[fam_cols].to_numpy(float), nan=0.0)
        ica = np.max(np.abs(fam), axis=1).astype(np.float32)
    elif "global_ica_00" in per.columns:
        ica = np.abs(per.global_ica_00.to_numpy(float)).astype(np.float32)
    for idx in np.argsort(-ica, kind="stable"):
        if sum("ica_extreme" in v for v in selected.values()) >= ica_extra:
            break
        if int(idx) not in selected:
            _add(selected, int(idx), "ica_extreme")

    # Never exceed the target while always keeping every parent covered first.
    ordered = sorted(selected.keys())
    if len(ordered) > n_target:
        ordered = ordered[:n_target]

    entries = []
    for idx in ordered:
        r = per.iloc[idx]
        entries.append(
            {
                "canonical_index": int(idx),
                "canonical_id": str(r.canonical_id),
                "parent_id": int(parents[idx]),
                "validated_fine_group_id": int(r.validated_fine_group_id),
                "raw_visual_leaf_id": int(r.raw_visual_leaf_id),
                "discovery_status": str(r.discovery_status),
                "patch_q99": float(patch[idx]),
                "reasons": selected[idx],
            }
        )
    return entries


def _quantiles(values, qs):
    arr = np.asarray(list(values), np.float64)
    if not arr.size:
        return {f"p{int(q * 100):02d}": None for q in qs}
    return {f"p{int(q * 100):02d}": float(np.quantile(arr, q)) for q in qs}


def build_row_plan(
    per,
    core_ids,
    *,
    mode: str = "sample",
    golden_entries: list[dict] | None = None,
    preflight_n: int = 256,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Deterministic, release-ordered plan of canonical rows to evaluate.

    ``core_ids`` is the frozen row order (``core.npz['canonical_id']``), which is
    the same index space the frozen per-row target arrays use. ``full`` returns
    every canonical row; ``preflight`` returns a deterministic parent-stratified
    subset (round-robin so all parents appear first); ``sample`` returns the
    persisted golden entries verbatim.
    """
    if mode not in {"sample", "preflight", "full"}:
        raise ValueError(f"unknown mode: {mode}")

    per = per.sort_values("canonical_index").reset_index(drop=True)
    parent_of: dict[str, int] = {
        str(r.canonical_id): int(r.raw_parent_id) for r in per.itertuples(index=False)
    }

    if mode == "sample":
        entries = [dict(e) for e in (golden_entries or [])]
    elif mode == "full":
        entries = [
            {
                "canonical_index": i,
                "canonical_id": cid,
                "parent_id": parent_of.get(cid, -1),
            }
            for i, cid in enumerate(core_ids)
        ]
    else:  # preflight
        by_parent: dict[int, list[tuple[int, str]]] = {p: [] for p in range(16)}
        unassigned: list[tuple[int, str]] = []
        for i, cid in enumerate(core_ids):
            p = parent_of.get(cid, -1)
            if p in by_parent:
                by_parent[p].append((i, cid))
            else:
                unassigned.append((i, cid))
        ordered: list[tuple[int, str]] = []
        rnd = 0
        while len(ordered) < preflight_n:
            added = False
            for p in range(16):
                if rnd < len(by_parent[p]):
                    ordered.append(by_parent[p][rnd])
                    added = True
                    if len(ordered) >= preflight_n:
                        break
            if not added:
                break
            rnd += 1
        for item in unassigned:
            if len(ordered) >= preflight_n:
                break
            ordered.append(item)
        entries = [
            {"canonical_index": i, "canonical_id": cid, "parent_id": parent_of.get(cid, -1)}
            for i, cid in ordered
        ]

    if limit and limit > 0:
        entries = entries[:limit]
    return entries


def plan_fingerprint(release: str, mode: str, entries: list[dict], outputs) -> str:
    """Stable hash binding a checkpoint to release, mode, order and tolerances."""
    payload = {
        "release": str(release),
        "mode": mode,
        "canonical_ids": [str(e["canonical_id"]) for e in entries],
        "outputs": list(outputs),
        "tolerances": {n: tolerance_for(n) for n in outputs},
    }
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def aggregate_rows(rows, outputs, failed_outputs=()) -> dict:
    """Worst-case + quantile agreement per representation over successful rows.

    Only rows with ``status == "ok"`` contribute. ``rows_passing`` counts rows
    whose metrics satisfy that output's own fixed tolerance.
    """
    agg = {}
    for name in list(outputs) + list(failed_outputs):
        metrics = [
            r["comparisons"][name]
            for r in rows
            if r.get("status") == "ok" and name in r.get("comparisons", {})
        ]
        if not metrics:
            continue
        cos = [m["cosine"] for m in metrics]
        rl2 = [m["rel_l2"] for m in metrics]
        mx = [m["max_abs"] for m in metrics]
        ma = [m["mean_abs"] for m in metrics]
        tol = tolerance_for(name)
        passed = 0
        for m in metrics:
            if vector_passes(m, tol):
                passed += 1
        entry = {
            "rows": len(metrics),
            "cosine_min": float(min(cos)),
            "cosine_mean": float(np.mean(cos)),
            "rel_l2_max": float(max(rl2)),
            "max_abs_max": float(max(mx)),
            "mean_abs_mean": float(np.mean(ma)),
            "rows_passing": int(passed),
            "pass_all": bool(passed == len(metrics)),
            "tolerance": tol,
        }
        entry.update({"max_abs_" + k: v for k, v in _quantiles(mx, (0.5, 0.95, 0.99)).items()})
        entry.update({"cosine_" + k: v for k, v in _quantiles(cos, (0.01, 0.05)).items()})
        agg[name] = entry
    return agg


# Source files whose content can change a V1 raw-pixel reconstruction or its
# parity comparison. A checkpoint binds to the hash of these files so that
# metrics produced by different implementation code can never be silently
# reused (see ``checkpoint_compatible``). Volatile artifacts (reports, logs,
# timestamps, STATUS/docs, checkpoints) are deliberately excluded.
IMPLEMENTATION_SOURCE_FILES = (
    "src/circl_e_ai/features/preprocess.py",
    "src/circl_e_ai/features/foreground.py",
    "src/circl_e_ai/features/dino.py",
    "src/circl_e_ai/features/cradio.py",
    "src/circl_e_ai/features/vlad.py",
    "src/circl_e_ai/features/concepts.py",
    "src/circl_e_ai/features/dense_patch.py",
    "src/circl_e_ai/features/math.py",
    "src/circl_e_ai/features/views.py",
    "src/circl_e_ai/features/bundle.py",
    "src/circl_e_ai/validation/pixel_parity.py",
    "offline/replay_pixel_parity.py",
)


def default_project_root() -> Path:
    """Repository root inferred from this module's location."""
    return Path(__file__).resolve().parents[3]


def implementation_fingerprint(root=None, files=IMPLEMENTATION_SOURCE_FILES) -> str:
    """Deterministic hash of the sources that can change V1 parity results.

    Reads only the listed source files (using their repo-relative path and
    bytes); a missing file is recorded as such so the result stays
    deterministic. Never touches reports, checkpoints, logs or timestamps.
    """
    base = Path(root) if root is not None else default_project_root()
    digest = hashlib.sha256()
    for rel in sorted(str(f) for f in files):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        path = base / rel
        digest.update(path.read_bytes() if path.is_file() else b"<missing>")
        digest.update(b"\0")
    return digest.hexdigest()


def checkpoint_compatible(
    obj,
    plan_fingerprint: str,
    implementation_fingerprint: str,
    canonical_id=None,
    canonical_index=None,
) -> bool:
    """Exact compatibility gate for scientific checkpoint reuse.

    A stored row may be reused only when *all* of these match exactly: the plan
    fingerprint (release/target/tolerance/sample inputs), the implementation
    fingerprint (reconstruction/parity source content), the row identity, and
    the completed-ok status. A record lacking ``implementation_fingerprint``
    predates this contract and is treated as incompatible, never trusted.
    """
    if not obj or obj.get("status") != "ok":
        return False
    if obj.get("fingerprint") != plan_fingerprint:
        return False
    if not implementation_fingerprint or obj.get("implementation_fingerprint") != implementation_fingerprint:
        return False
    if canonical_id is not None and str(obj.get("canonical_id")) != str(canonical_id):
        return False
    if canonical_index is not None and int(obj.get("canonical_index", -1)) != int(canonical_index):
        return False
    return True


def run_is_complete(plan_n: int, ok_n: int, errored_n: int, missing_n: int, bboxes_finite: bool = True) -> bool:
    """Full-cohort completeness: every planned row accounted for and valid."""
    return (
        ok_n == plan_n
        and errored_n == 0
        and missing_n == 0
        and bool(bboxes_finite)
    )


def summarize_failures(rows, outputs, top_k: int = 10) -> dict:
    """Worst rows per representation, for a concise failure table."""
    table = {}
    for name in outputs:
        tol = tolerance_for(name)
        scored = [
            (r["comparisons"][name]["max_abs"], r["comparisons"][name]["cosine"], r)
            for r in rows
            if r.get("status") == "ok" and name in r.get("comparisons", {})
            and not vector_passes(r["comparisons"][name], tol)
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        table[name] = [
            {
                "canonical_id": r["canonical_id"],
                "canonical_index": r.get("canonical_index"),
                "parent_id": r.get("parent_id"),
                "max_abs": float(mx),
                "cosine": float(cs),
            }
            for mx, cs, r in scored[:top_k]
        ]
    return table


def output_specs():
    """The exact comparison surface evaluated by the parity harness."""
    return {
        "vector_targets": dict(FROZEN_VECTOR_TARGETS),
        "composition_targets": dict(FROZEN_COMPOSITION_TARGETS),
        "patch_prototype_target": FROZEN_PATCH_PROTOTYPE_TARGET,
        "scalar_outputs": ["foreground_bbox_finite"],
    }
