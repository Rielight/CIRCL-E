#!/usr/bin/env python3
"""Startup verification for the CIRCL-E Dashboard release bundle.

Runs *before* Streamlit loads multi-GB backbones, so misconfiguration fails with
a clear message instead of a Deep Learning traceback. It never loads a model, so
it is fast and safe.

Checks:
  1. bundle layout (app, app layer, frozen core, release, packaging metadata);
  2. frozen release tree integrity (hash manifest + required artifacts);
  3. backbone directories (env override or manifest binding) and expected files;
  4. optional checkpoint SHA-256 against RELEASE_MANIFEST.json;
  5. Python/package compatibility against requirements.lock;
  6. CUDA availability (informational; CPU fallback is allowed).

Exit codes: 0 = ready, 1 = fatal problem, 2 = usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

REQUIRED_LAYOUT = (
    "dashboard/app.py",
    "dashboard/components.py",
    "dashboard/state.py",
    "dashboard/styles.py",
    "src/circl_e_app/__init__.py",
    "src/circl_e_app/inference_service.py",
    "src/circl_e_ai/__init__.py",
    "src/circl_e_ai/release/loader.py",
    "runtime/release/manifest.json",
    "requirements.lock",
    "RELEASE_MANIFEST.json",
)

#: Files that must exist in a backbone directory for local_files_only loading.
BACKBONE_REQUIRED = ("config.json", "preprocessor_config.json")
BACKBONE_WEIGHT_SUFFIXES = (".safetensors", ".bin", ".pth.tar", ".pth", ".ckpt")


def sha256_file(path: Path, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 - reported as a check failure
        return {}


def _parse_lock(lock_path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    if not lock_path.is_file():
        return pins
    for raw in lock_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, _, version = line.partition("==")
        pins[name.strip()] = version.strip()
    return pins


def check_layout() -> list[str]:
    return [f"missing bundle file: {rel}" for rel in REQUIRED_LAYOUT if not (ROOT / rel).is_file()]


def check_release(full_hash: bool) -> tuple[list[str], dict[str, Any]]:
    release_dir = Path(
        os.environ.get("CIRCL_RELEASE_DIR") or (ROOT / "runtime" / "release")
    ).expanduser()
    manifest_path = release_dir / "manifest.json"
    if not manifest_path.is_file():
        return [f"release manifest not found: {manifest_path}"], {}
    manifest = _read_json(manifest_path)
    if not full_hash:
        return [], manifest
    from circl_e_ai.release.verifier import verify_release_tree

    errors = [f"release integrity: {e}" for e in verify_release_tree(release_dir)]
    return errors, manifest


def resolved_backbone_paths(manifest: dict[str, Any]) -> dict[str, str | None]:
    bound = dict(manifest.get("backbones") or {})
    dino = (os.environ.get("CIRCL_DINO_DIR") or "").strip() or bound.get("dino_path")
    cradio = (os.environ.get("CIRCL_CRADIO_DIR") or "").strip() or bound.get("cradio_path")
    return {"dino_path": dino, "cradio_path": cradio}


def check_backbones(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for label, path in resolved_backbone_paths(manifest).items():
        if not path:
            errors.append(f"{label} is not set (set the env var or bind it in the release manifest)")
            continue
        folder = Path(path)
        if not folder.is_dir():
            errors.append(f"{label} directory does not exist: {folder}")
            continue
        readable = True
        for name in BACKBONE_REQUIRED:
            target = folder / name
            if not target.is_file():
                errors.append(f"{label} missing {name} in {folder}")
                readable = False
            elif not _readable(target):
                errors.append(f"{label} {name} is not readable: {target}")
                readable = False
        weights = [p for p in folder.iterdir() if p.suffix in BACKBONE_WEIGHT_SUFFIXES or p.name.endswith(".pth.tar")]
        if not weights:
            errors.append(f"{label} has no recognised weight file in {folder}")
        elif not any(_readable(p) for p in weights):
            errors.append(f"{label} weight files are not readable in {folder}")
        if not readable:
            continue
    return errors


def _readable(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            handle.read(16)
        return True
    except OSError:
        return False


def check_model_hashes(manifest: dict[str, Any], release_manifest: dict[str, Any]) -> list[str]:
    """Verify recorded checkpoint hashes (opt-in; hashing multi-GB files is slow)."""
    expected = release_manifest.get("expected_model_files") or {}
    if not expected:
        return []
    paths = resolved_backbone_paths(manifest)
    errors: list[str] = []
    for label, key in (("dino", "dino_path"), ("cradio", "cradio_path")):
        folder = paths.get(key)
        if not folder:
            continue
        for name, digest in (expected.get(label) or {}).items():
            target = Path(folder) / name
            if not target.is_file():
                errors.append(f"{label} expected file missing: {name}")
            elif sha256_file(target) != digest:
                errors.append(f"{label} hash mismatch: {name}")
    return errors


def check_environment() -> tuple[list[str], dict[str, str], str]:
    import importlib.metadata as importlib_metadata

    pins = _parse_lock(ROOT / "requirements.lock")
    installed: dict[str, str] = {}
    warnings: list[str] = []
    for name, wanted in sorted(pins.items()):
        try:
            got = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            warnings.append(f"{name}: not installed (expected {wanted})")
            continue
        installed[name] = got
        # torch may report a local build tag (e.g. 2.13.0+cu130)
        if got.split("+")[0] != wanted.split("+")[0]:
            warnings.append(f"{name}: installed {got}, lock pins {wanted}")
    python_version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info < (3, 11):
        warnings.append(f"Python {python_version} is below the supported 3.11 minimum")
    return warnings, installed, python_version


def check_cuda() -> tuple[bool, str]:
    try:
        import torch

        if torch.cuda.is_available():
            return True, torch.cuda.get_device_name(0)
        return False, "CUDA not available (CPU fallback will be slow)"
    except Exception as exc:  # noqa: BLE001 - torch may be missing from the env
        return False, f"torch unavailable: {exc}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the CIRCL-E runtime bundle.")
    parser.add_argument("--fast", action="store_true", help="skip the full release hash sweep")
    parser.add_argument("--check-model-hashes", action="store_true", help="hash multi-GB backbone checkpoints")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    args = parser.parse_args(argv)

    errors = check_layout()
    release_errors, release_manifest = check_release(full_hash=not args.fast)
    errors.extend(release_errors)
    if not release_errors:
        errors.extend(check_backbones(release_manifest))
    env_warnings, installed, python_version = check_environment()
    cuda_ok, cuda_detail = check_cuda()

    bundle_manifest = _read_json(ROOT / "RELEASE_MANIFEST.json")
    if args.check_model_hashes and release_manifest:
        errors.extend(check_model_hashes(release_manifest, bundle_manifest))

    report = {
        "ok": not errors,
        "errors": errors,
        "warnings": env_warnings,
        "python_version": python_version,
        "installed_packages": installed,
        "cuda_available": cuda_ok,
        "cuda_detail": cuda_detail,
        "release_id": release_manifest.get("release_id"),
        "release_verified": release_manifest.get("verified"),
        "backbones": resolved_backbone_paths(release_manifest) if release_manifest else {},
        "software_version": bundle_manifest.get("software_version"),
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"CIRCL-E Dashboard runtime check (Python {python_version})")
        print(f"  release_id       : {report['release_id']}")
        print(f"  release_verified : {report['release_verified']}")
        print(f"  dino_path        : {report['backbones'].get('dino_path')}")
        print(f"  cradio_path      : {report['backbones'].get('cradio_path')}")
        print(f"  CUDA             : {'yes — ' + cuda_detail if cuda_ok else cuda_detail}")
        for warning in env_warnings:
            print(f"  warning: {warning}")
        for error in errors:
            print(f"  ERROR: {error}")
        print("PASS: runtime is ready." if not errors else "FAIL: runtime is not ready.")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
