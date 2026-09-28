"""Thin inference service over the frozen :mod:`circl_e_ai` runtime.

The dashboard talks to this module only. It must never know how DINO, C-RADIO,
discovery, ICA or post-mapping work internally.

Design constraints (scientific invariants):

* the frozen release is loaded once and reused; multi-GB backbones are never
  reloaded per request when a cache key matches;
* inference always goes through ``circl_e_ai.pipeline.infer.infer_image``;
* uploaded bytes are decoded and validated defensively, without changing the
  frozen preprocessing path (no ad-hoc resizing that would alter features);
* results are never cached across different image bytes.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from circl_e_ai.input.image import image_sha256
from circl_e_ai.pipeline.infer import infer_image
from circl_e_ai.release.loader import FrozenRelease, load_release

from .errors import ImageValidationError, InferenceError, ReleaseLoadError
from .ui_helpers import backbone_env_overrides, manifest_fingerprint

#: Image containers the release UI supports. Pillow can decode more than this,
#: but only these are advertised/tested; the release UI never claims a format it
#: has not exercised.
SUPPORTED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

#: Hard ceiling on one uploaded file. Far above any realistic device photo and
#: small enough that a local deployment never buffers an unbounded upload.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

#: Defensive ceiling to avoid decompression-bomb OOM in a local UI.
DEFAULT_MAX_PIXELS = 64_000_000


@dataclass(frozen=True)
class InputInfo:
    """Presentation metadata for one uploaded image.

    This is *display* metadata only; it is never fed into CIRCL-E features.
    """

    filename: str
    format: str | None
    mode: str | None
    width: int | None
    height: int | None
    byte_size: int
    sha256: str
    converted_from_mode: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "format": self.format,
            "mode": self.mode,
            "width": self.width,
            "height": self.height,
            "byte_size": self.byte_size,
            "sha256": self.sha256,
            "converted_from_mode": self.converted_from_mode,
        }


@dataclass(frozen=True)
class ReleaseInfo:
    """Display-safe summary of the loaded frozen release."""

    release_id: str
    verified: bool
    discovery_version: str | None
    semantic_version: str | None
    postmapping_version: str | None
    dino_path: str | None
    cradio_path: str | None
    root: str
    development: bool = True

    @property
    def status_label(self) -> str:
        """Neutral user-facing model-release status (the ``verified`` flag is unchanged)."""
        return "Research / decision-support release" if not self.verified else "Verified canonical release"

    def as_dict(self) -> dict[str, Any]:
        return {
            "release_id": self.release_id,
            "verified": self.verified,
            "development": self.development,
            "status_label": self.status_label,
            "discovery_version": self.discovery_version,
            "semantic_version": self.semantic_version,
            "postmapping_version": self.postmapping_version,
            "dino_path": self.dino_path,
            "cradio_path": self.cradio_path,
            "root": self.root,
        }


# Process-wide release cache keyed by
# (resolved path, require_verified, device, strict_environment, manifest fingerprint).
# The manifest fingerprint means an in-place release rebuild cannot silently
# reuse a previously loaded release. The Streamlit layer additionally wraps this
# in @st.cache_resource so a single process never reloads multi-GB backbones per
# click. Results are NOT cached.
_RELEASE_CACHE: dict[tuple[str, bool, str | None, bool, str], FrozenRelease] = {}


def load_release_cached(
    release_dir: str | Path,
    *,
    require_verified: bool = True,
    device: str | None = None,
    strict_environment: bool = False,
    use_cache: bool = True,
    release_fingerprint: str | None = None,
) -> FrozenRelease:
    """Load a frozen release, optionally reusing a cached instance.

    The cache key includes the manifest fingerprint (auto-derived when not
    supplied) so a release rebuilt in place does not keep serving the previous
    assets. Raises :class:`ReleaseLoadError` with a clean message on any failure.
    """
    path = Path(release_dir).expanduser().resolve()
    fingerprint = release_fingerprint or manifest_fingerprint(path) or "unknown"
    key = (str(path), bool(require_verified), device, bool(strict_environment), fingerprint)
    if use_cache and key in _RELEASE_CACHE:
        return _RELEASE_CACHE[key]
    if not (path / "manifest.json").is_file():
        raise ReleaseLoadError(
            "Release manifest not found.",
            detail=f"Expected manifest at {path / 'manifest.json'}. Build the development release first.",
        )
    try:
        release = load_release(
            path,
            require_verified=require_verified,
            load_backbones=True,
            device=device,
            strict_environment=strict_environment,
            backbone_paths=backbone_env_overrides() or None,
        )
    except Exception as exc:  # noqa: BLE001 - normalize runtime errors for the UI
        raise ReleaseLoadError("Could not load the frozen release.", detail=str(exc)) from exc
    if use_cache:
        _RELEASE_CACHE[key] = release
    return release


def clear_release_cache() -> None:
    """Drop cached releases (used by tests; not part of normal runtime)."""
    _RELEASE_CACHE.clear()


class InferenceService:
    """Stable service facade used by the dashboard.

    Example::

        service = InferenceService("runtime/release-dev")
        result = service.infer(uploaded_bytes, filename="photo.jpg")
        view = prepare_display_result(result, input_info=service.last_input_info)
    """

    def __init__(
        self,
        release_dir: str | Path,
        *,
        require_verified: bool = False,
        device: str | None = None,
        strict_environment: bool = False,
        max_pixels: int = DEFAULT_MAX_PIXELS,
        max_bytes: int = MAX_UPLOAD_BYTES,
        use_cache: bool = True,
        release_fingerprint: str | None = None,
    ):
        self.release_dir = Path(release_dir).expanduser()
        self.require_verified = bool(require_verified)
        self.device = device
        self.strict_environment = bool(strict_environment)
        self.max_pixels = int(max_pixels)
        self.max_bytes = int(max_bytes)
        self.use_cache = bool(use_cache)
        self.release_fingerprint = release_fingerprint
        self._release: FrozenRelease | None = None
        self.last_input_info: InputInfo | None = None

    # ------------------------------------------------------------------ #
    # Release
    # ------------------------------------------------------------------ #
    def load(self) -> FrozenRelease:
        """Load (or reuse) the frozen release. Never fits or mutates assets."""
        if self._release is None:
            self._release = load_release_cached(
                self.release_dir,
                require_verified=self.require_verified,
                device=self.device,
                strict_environment=self.strict_environment,
                use_cache=self.use_cache,
                release_fingerprint=self.release_fingerprint,
            )
        return self._release

    def release_info(self) -> ReleaseInfo:
        release = self.load()
        manifest = release.manifest
        backbones = getattr(manifest, "backbones", None) or {}
        return ReleaseInfo(
            release_id=manifest.release_id,
            verified=bool(manifest.verified),
            discovery_version=getattr(manifest, "discovery_version", None),
            semantic_version=getattr(manifest, "semantic_version", None),
            postmapping_version=getattr(manifest, "postmapping_version", None),
            dino_path=backbones.get("dino_path"),
            cradio_path=backbones.get("cradio_path"),
            root=str(release.root),
            development=not bool(manifest.verified),
        )

    def display_labels(self) -> dict[str, Any]:
        """Authoritative, display-only labels read from frozen release metadata.

        This intentionally avoids :meth:`load` so the landing page never
        triggers a multi-GB backbone load just to render wording. The helper
        fails soft (empty mapping) when the release files are absent.
        """
        from .labels import load_display_labels

        return load_display_labels(self.release_dir)

    # ------------------------------------------------------------------ #
    # Image validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extension_ok(filename: str | None) -> bool:
        if not filename:
            return True  # bytes without a name are still worth attempting
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in SUPPORTED_EXTENSIONS

    def validate_image(
        self,
        data: bytes | bytearray | memoryview,
        filename: str | None = None,
    ) -> tuple[Any, InputInfo]:
        """Decode and validate uploaded bytes.

        Returns a detached RGB ``PIL.Image`` plus display metadata. The returned
        image is handed to the frozen pipeline unchanged (no ad-hoc resizing).
        """
        if not data:
            raise ImageValidationError("The uploaded file is empty.")
        if not self._extension_ok(filename):
            ext = filename.rsplit(".", 1)[-1] if filename and "." in filename else ""
            raise ImageValidationError(
                f"Unsupported file extension: .{ext}",
                detail=f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )

        raw = bytes(data)
        if len(raw) > self.max_bytes:
            raise ImageValidationError(
                "The uploaded file is too large.",
                detail=f"{len(raw):,} bytes exceeds the {self.max_bytes:,}-byte upload limit.",
            )
        from PIL import Image, ImageOps
        from PIL import UnidentifiedImageError

        try:
            with Image.open(_BytesReader(raw)) as opened:
                opened.load()
                source_format = opened.format
                source_mode = opened.mode
                width, height = opened.size
                if width * height > self.max_pixels:
                    raise ImageValidationError(
                        "Image is too large to process safely.",
                        detail=f"{width}x{height} exceeds the {self.max_pixels:,}-pixel limit.",
                    )
                image = ImageOps.exif_transpose(opened).convert("RGB").copy()
        except ImageValidationError:
            raise
        except UnidentifiedImageError as exc:
            raise ImageValidationError("The file is not a readable image.", detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - corrupt/truncated/unsupported
            raise ImageValidationError("Could not decode the uploaded image.", detail=str(exc)) from exc

        info = InputInfo(
            filename=filename or "uploaded",
            format=source_format,
            mode=source_mode,
            width=width,
            height=height,
            byte_size=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            converted_from_mode=source_mode if source_mode != "RGB" else None,
        )
        return image, info

    # ------------------------------------------------------------------ #
    # Inference
    # ------------------------------------------------------------------ #
    def infer(
        self,
        data: bytes | bytearray | memoryview,
        filename: str | None = None,
    ) -> Any:
        """Validate bytes and run the frozen production inference path.

        Returns the existing ``circl_e_ai`` ``InferenceResult``; it is never
        mutated or cached.
        """
        image, info = self.validate_image(data, filename)
        release = self.load()
        try:
            result = infer_image(image, release)
        except Exception as exc:  # noqa: BLE001 - normalize for the UI
            raise InferenceError("Inference failed for this image.", detail=str(exc)) from exc
        self.last_input_info = info
        # Pixel-content hash from the frozen pipeline should agree with the raw
        # byte hash only when the upload is already canonical; both are shown.
        return result

    def infer_and_present(
        self,
        data: bytes | bytearray | memoryview,
        filename: str | None = None,
        *,
        labels: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        """Convenience: run inference and build the presentation model."""
        from .presentation import prepare_display_result

        result = self.infer(data, filename)
        view = prepare_display_result(
            result,
            input_info=self.last_input_info,
            release_info=self.release_info(),
            labels=labels,
        )
        return result, view


def image_pixel_sha256(image: Any) -> str:
    """Canonical pixel hash used by the frozen pipeline (display helper)."""
    return image_sha256(image)


class _BytesReader:
    """Minimal file-like wrapper so PIL never holds a UI-owned buffer open."""

    __slots__ = ("_data", "_pos")

    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = len(self._data) + offset
        self._pos = max(0, min(self._pos, len(self._data)))
        return self._pos

    def tell(self) -> int:
        return self._pos

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True
