"""Frozen DINO middle/final patch extraction matching the discovery notebook."""
from __future__ import annotations
import numpy as np
from .math import normalize_rows_l2
from .preprocess import choose_aspect_preserving_size, resize_rgb_exact


def _runtime_config(release) -> dict:
    return getattr(release.assets, "runtime_config", None) or {
        "dino_short": 512,
        "dino_max_long": 1024,
        "dino_mid_fraction": 0.75,
        "attr_short": 768,
        "attr_max_long": 1024,
    }


def dino_forward(image, release, *, short: int | None = None, max_long: int | None = None) -> dict:
    import torch
    model = release.assets.dino_model
    proc = release.assets.dino_processor
    if model is None or proc is None:
        raise RuntimeError("DINO model/processor not loaded in FrozenRelease")
    cfg = _runtime_config(release)
    patch = int(getattr(model.config, "patch_size", 16))
    reg = int(getattr(model.config, "num_register_tokens", 0) or 0)
    depth = int(model.config.num_hidden_layers)
    mid_fraction = float(cfg.get("dino_mid_fraction", 0.75))
    mid_layer = max(1, min(depth, int(round(mid_fraction * depth))))
    short = int(short if short is not None else cfg.get("dino_short", 512))
    max_long = int(max_long if max_long is not None else cfg.get("dino_max_long", 1024))
    th, tw = choose_aspect_preserving_size(image.height, image.width, short, patch, max_long)
    rr = resize_rgb_exact(image, th, tw)
    inp = proc(images=rr, return_tensors="pt", do_resize=False, do_center_crop=False)
    try:
        device = next(model.parameters()).device
        dtype = next(model.parameters()).dtype
    except StopIteration:
        device, dtype = torch.device("cpu"), torch.float32
    x = inp.pixel_values.to(device, dtype=dtype)
    with torch.inference_mode():
        o = model(pixel_values=x, output_hidden_states=True)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    npre = 1 + reg
    gh, gw = th // patch, tw // patch
    hf = o.last_hidden_state
    hs = o.hidden_states
    if len(hs) == depth + 1:
        hm = hs[mid_layer]
    elif len(hs) == depth:
        hm = hs[mid_layer - 1]
    else:
        raise RuntimeError(f"Unexpected DINO hidden-state count {len(hs)} for depth {depth}")
    hm = model.norm(hm)
    late = hf[:, npre:][0].float().cpu().numpy().copy()
    mid = hm[:, npre:][0].float().cpu().numpy().copy()
    cls = normalize_rows_l2(hf[:, 0].float().cpu().numpy())[0].copy()
    if len(late) != gh * gw:
        raise RuntimeError(f"DINO patch/grid mismatch: patches={len(late)} grid={gh}x{gw}")
    return {"cls": cls, "late": late, "mid": mid, "grid": (gh, gw), "size": (th, tw)}
