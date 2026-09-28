"""Small, dependency-free UI/session helpers for the dashboard.

Pure functions only: no Streamlit import, no scientific math and no I/O beyond
the paths explicitly passed in. Keeping them here makes the dashboard's
session/cache behaviour unit-testable without a browser or model backbones.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

#: How many demonstration images the landing page offers at most.
DEFAULT_EXAMPLE_LIMIT = 6

#: Environment variables that redirect the frozen backbone directories at
#: deployment time (e.g. a read-only container mount). They never change the
#: loaded weights, only where they are read from.
DINO_ENV_VAR = "CIRCL_DINO_DIR"
CRADIO_ENV_VAR = "CIRCL_CRADIO_DIR"


def backbone_env_overrides(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return manifest-key overrides for backbone directories from the environment.

    Only non-empty values are returned, so an unset variable leaves the
    manifest-bound path untouched (the historical behavior).
    """
    source = os.environ if env is None else env
    overrides: dict[str, str] = {}
    dino = (source.get(DINO_ENV_VAR) or "").strip()
    cradio = (source.get(CRADIO_ENV_VAR) or "").strip()
    if dino:
        overrides["dino_path"] = dino
    if cradio:
        overrides["cradio_path"] = cradio
    return overrides


def effective_backbone_paths(
    backbones: Mapping[str, Any] | None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Merge manifest-bound backbone paths with deployment env overrides."""
    resolved = dict(backbones or {})
    resolved.update(backbone_env_overrides(env))
    return resolved


def sha256_bytes(data: bytes | bytearray | memoryview) -> str:
    """Deterministic SHA-256 of raw uploaded bytes."""
    return hashlib.sha256(bytes(data)).hexdigest()


def result_is_stale(stored_sha: str | None, current_sha: str | None) -> bool:
    """Return True when a stored result must not be shown for the current input.

    A result is stale whenever the bytes it was computed from are no longer the
    bytes currently selected. ``None``/``None`` (nothing stored, nothing
    selected) is not stale.
    """
    if stored_sha is None:
        return False
    return stored_sha != current_sha


def manifest_fingerprint(release_dir: str | Path) -> str | None:
    """Cheap content-change signature of a release manifest.

    ``st_mtime_ns`` plus size is enough to detect an in-place release rebuild
    (an atomic write changes both), so caches keyed on a release cannot
    silently reuse the previously loaded assets. Returns ``None`` when the
    manifest is absent or unreadable. It never reads or parses the manifest
    body, so calling it is safe on every rerun.
    """
    try:
        stat = (Path(release_dir) / "manifest.json").stat()
    except OSError:
        return None
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def inference_settings_key(
    release_dir: str | Path,
    require_verified: bool,
    device: str | None,
    release_fingerprint: str | None = None,
) -> str:
    """Deterministic signature of the inference-affecting developer settings.

    A stored result must never be shown beside release/device/verification
    settings that did not produce it, so these settings participate in the
    staleness key alongside the input byte SHA. ``release_fingerprint``
    (see :func:`manifest_fingerprint`) additionally invalidates a result when
    the release at the same path is rebuilt in place.
    """
    try:
        resolved = str(Path(release_dir).expanduser().resolve())
    except Exception:  # noqa: BLE001 - never break the UI on a malformed path
        resolved = str(release_dir)
    fingerprint = release_fingerprint or ""
    return f"{resolved}|verified={bool(require_verified)}|device={device or 'auto'}|release={fingerprint}"


def backbone_paths_missing(
    backbones: Mapping[str, Any] | None,
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Return the bound backbone directories that are absent on disk.

    Distinguishes "path not bound" (an incomplete manifest) from "path bound but
    missing" so the landing page can show an honest, actionable blocker instead
    of failing only at run time. Deployment env overrides are respected. It only
    stats the paths; it never loads the models and never fabricates a result.
    """
    missing: list[str] = []
    for key in ("dino_path", "cradio_path"):
        value = effective_backbone_paths(backbones, env).get(key)
        if value and not Path(value).exists():
            missing.append(str(value))
    return missing


def result_key(byte_sha: str | None, settings_key: str | None) -> str | None:
    """Composite staleness key binding a result to its bytes *and* settings.

    ``None`` when no input is selected. The value is opaque to callers and is
    only ever compared for equality via :func:`result_is_stale`.
    """
    if byte_sha is None:
        return None
    return f"{byte_sha}::{settings_key or ''}"


#: Session-state keys that constitute the displayed result. ``Clear result`` and
#: stale/error purges remove exactly these; the selected image and developer
#: settings are never part of this set.
RESULT_STATE_KEYS = ("result", "view", "view_sha", "view_key", "error")


def input_source(uploaded_present: bool, example_present: bool) -> str:
    """Deterministic input precedence: an upload always wins over an example.

    Returns ``"upload"``, ``"example"`` or ``"none"``. The dashboard disables
    the demonstration selector while an upload is present so this precedence is
    visible, not implicit.
    """
    if uploaded_present:
        return "upload"
    if example_present:
        return "example"
    return "none"


def read_example_bytes(path: str | Path) -> bytes:
    """Read a demonstration image, normalizing OS errors for the UI.

    Raises :class:`~circl_e_app.errors.ImageValidationError` (an ``AppError``) so
    the dashboard can show a clean message instead of an uncaught ``OSError``.
    """
    from .errors import ImageValidationError

    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise ImageValidationError(
            "Could not read the demonstration image.", detail=str(exc)
        ) from exc


def drop_empty_columns(
    rows: Iterable[Mapping[str, Any]],
    columns: Iterable[str],
) -> list[str]:
    """Return the columns that carry at least one non-empty value.

    Presentation-only: a column whose every value is ``None`` or ``""`` is
    dropped so Evidence tables stay readable. A column containing an explicit
    unresolved/N/A marker is never empty, so meaningful states are preserved.
    """
    ordered = list(columns)
    materialized = [row for row in rows]
    keep: list[str] = []
    for column in ordered:
        if any(
            row.get(column) is not None and str(row.get(column)).strip() != ""
            for row in materialized
        ):
            keep.append(column)
    return keep


def humanize_token(value: object) -> str:
    """Format a frozen identifier for display without renaming its meaning.

    This only replaces underscores with spaces; it never expands an acronym or
    invents a label.
    """
    if value is None:
        return ""
    text = str(value)
    return text.replace("_", " ").strip()


def select_example_images(paths: Iterable[Path], limit: int = DEFAULT_EXAMPLE_LIMIT) -> list[Path]:
    """Deterministically pick at most ``limit`` example images.

    Sorted, evenly-spaced selection so the demonstration list is stable across
    restarts and spread across the corpus instead of clustered by filename.
    """
    items = sorted(Path(p) for p in paths)
    if limit <= 0 or not items:
        return []
    if len(items) <= limit:
        return items
    step = len(items) / float(limit)
    picked: list[Path] = []
    for i in range(limit):
        candidate = items[min(int(i * step), len(items) - 1)]
        if candidate not in picked:
            picked.append(candidate)
    return picked
