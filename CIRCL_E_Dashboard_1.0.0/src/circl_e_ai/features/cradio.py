"""Frozen C-RADIO slot-1 feature extraction matching the discovery notebook."""
from __future__ import annotations
import numpy as np
from .math import normalize_rows_l2, apply_npz_transform
from .preprocess import choose_aspect_preserving_size, foreground_canvas


def _resolution_hw(value, target_hw=None):
    if value is None:
        raise TypeError("resolution is None")
    if hasattr(value, "height") and hasattr(value, "width"):
        return int(value.height), int(value.width)
    if isinstance(value, dict) and "height" in value and "width" in value:
        return int(value["height"]), int(value["width"])
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and np.isscalar(value[0]) and np.isscalar(value[1]):
            return int(value[0]), int(value[1])
        candidates = []
        for item in value:
            try:
                candidates.append(_resolution_hw(item, target_hw))
            except Exception:
                pass
        if candidates:
            if target_hw is None:
                return candidates[0]
            th, tw = map(int, target_hw)
            return min(candidates, key=lambda hw: (hw[0] - th) ** 2 + (hw[1] - tw) ** 2)
    raise TypeError(f"Unsupported C-RADIO resolution object: {type(value).__name__}: {value!r}")


def cradio_supported_hw(model, height: int, width: int) -> tuple[int, int]:
    return _resolution_hw(model.get_nearest_supported_resolution(int(height), int(width)), (height, width))


def extract_cradio_raw(image, release, *, fixed_preferred: bool = False):
    import torch
    model = release.assets.cradio_model
    proc = release.assets.cradio_processor
    if model is None or proc is None:
        raise RuntimeError("C-RADIO model/processor not loaded in FrozenRelease")
    cfg = getattr(release.assets, "runtime_config", None) or {}
    canvas = int(cfg.get("foreground_canvas", 512))
    short = int(cfg.get("cradio_short", 512))
    max_long = int(cfg.get("cradio_max_long", 1024))
    step = int(getattr(model, "min_resolution_step", 16) or 16)
    if fixed_preferred:
        th, tw = cradio_supported_hw(model, canvas, canvas)
    else:
        th0, tw0 = choose_aspect_preserving_size(image.height, image.width, short, step, max_long)
        th, tw = cradio_supported_hw(model, th0, tw0)
    x = proc(images=image, return_tensors="pt", do_resize=True,
             size={"height": int(th), "width": int(tw)}, do_center_crop=False).pixel_values
    try:
        device = next(model.parameters()).device
    except StopIteration:
        device = torch.device("cpu")
    x = x.to(device, dtype=torch.float32)
    amp_dtype = torch.bfloat16 if device.type == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
    if device.type == "cuda" and amp_dtype != torch.float32:
        ctx = torch.autocast("cuda", dtype=amp_dtype)
    else:
        from contextlib import nullcontext
        ctx = nullcontext()
    with torch.inference_mode(), ctx:
        summary, _ = model(x)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    sc = summary.float().cpu().numpy()
    if sc.ndim != 2 or sc.shape[1] % 2 != 0:
        raise RuntimeError(f"Unexpected C-RADIO summary shape {sc.shape}")
    return normalize_rows_l2(sc[:, sc.shape[1] // 2:])


def extract_G_whole(image, release):
    raw = extract_cradio_raw(image, release, fixed_preferred=False)
    return apply_npz_transform(raw, release.assets.transforms["cradio_slot1_pca256"])


def extract_G_foreground(image, bbox, release):
    cfg = getattr(release.assets, "runtime_config", None) or {}
    fg = foreground_canvas(
        image, bbox,
        margin=float(cfg.get("foreground_margin", 0.04)),
        size=int(cfg.get("foreground_canvas", 512)),
        fill=tuple(cfg.get("foreground_fill", (127, 127, 127))),
    )
    raw = extract_cradio_raw(fg, release, fixed_preferred=True)
    return apply_npz_transform(raw, release.assets.transforms["cradio_slot1_pca256"])
