"""Image input handling. Metadata is never fed into CIRCL-E representations."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import hashlib
from PIL import Image, ImageOps


def load_rgb_image(source) -> Image.Image:
    """Return a detached EXIF-oriented RGB PIL image.

    Accepted inputs: PIL.Image, filesystem path, or bytes. This mirrors the source
    notebook's path behavior while making the standalone runtime usable in tests.
    """
    if isinstance(source, Image.Image):
        return ImageOps.exif_transpose(source).convert("RGB").copy()
    if isinstance(source, (bytes, bytearray, memoryview)):
        with Image.open(BytesIO(bytes(source))) as im:
            return ImageOps.exif_transpose(im).convert("RGB").copy()
    with Image.open(Path(source)) as im:
        return ImageOps.exif_transpose(im).convert("RGB").copy()


def image_sha256(image: Image.Image) -> str:
    """Stable hash of canonical RGB pixels plus dimensions, not filename/metadata."""
    im = image.convert("RGB")
    h = hashlib.sha256()
    h.update(int(im.width).to_bytes(8, "little"))
    h.update(int(im.height).to_bytes(8, "little"))
    h.update(im.tobytes())
    return h.hexdigest()
