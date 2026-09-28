"""Exact deterministic image geometry helpers from the 2026-09-23 discovery notebook."""
from __future__ import annotations
import numpy as np
from PIL import Image, ImageOps


def choose_aspect_preserving_size(h: int, w: int, short: int, patch: int = 16, max_long: int = 1024) -> tuple[int, int]:
    """Choose the notebook-compatible aspect-preserving, patch-aligned resolution."""
    scale = float(short) / min(h, w)
    if max(h, w) * scale > max_long:
        scale = float(max_long) / max(h, w)
    th = max(int(patch), int(round(h * scale / patch)) * int(patch))
    tw = max(int(patch), int(round(w * scale / patch)) * int(patch))
    return th, tw


def resize_rgb_exact(image: Image.Image, h: int, w: int) -> Image.Image:
    # Source function is named Lanczos in prose but actually uses BICUBIC.
    return image.convert("RGB").resize((int(w), int(h)), Image.Resampling.BICUBIC)


def bbox_crop(image: Image.Image, bbox, margin: float = 0.0) -> Image.Image:
    w, h = image.size
    x0, y0, x1, y1 = map(float, np.asarray(bbox)[:4])
    if margin > 0:
        bw = max(x1 - x0, 1e-6)
        bh = max(y1 - y0, 1e-6)
        x0 -= margin * bw
        x1 += margin * bw
        y0 -= margin * bh
        y1 += margin * bh
    box = (
        int(np.clip(x0, 0, 1) * w),
        int(np.clip(y0, 0, 1) * h),
        int(np.clip(x1, 0, 1) * w),
        int(np.clip(y1, 0, 1) * h),
    )
    if box[2] - box[0] < 16 or box[3] - box[1] < 16:
        return image.copy()
    return image.crop(box)


def letterbox_square(image: Image.Image, size: int = 512, fill=(127, 127, 127)) -> Image.Image:
    x = ImageOps.contain(image.convert("RGB"), (int(size), int(size)), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (int(size), int(size)), tuple(fill))
    canvas.paste(x, ((int(size) - x.width) // 2, (int(size) - x.height) // 2))
    return canvas


def foreground_canvas(image: Image.Image, bbox, margin: float = 0.04, size: int = 512, fill=(127, 127, 127)) -> Image.Image:
    """C-RADIO foreground path: bbox + 4% margin -> deterministic gray 512 square."""
    return letterbox_square(bbox_crop(image, bbox, margin), size=size, fill=fill)
