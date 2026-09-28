#!/usr/bin/env python3
"""Release smoke test: run real frozen inference on real images.

This is an **execution/state** smoke test, not accuracy evidence. It proves the
bundled application layer can load the frozen release, run the production
``infer_image`` path, build a presentation view, and never leak a result from a
different input.

Usage::

    python scripts/smoke_test.py --image a.jpg --image b.jpg [--json out.json]

Exits non-zero on the first failure so it can gate a deployment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DASHBOARD = ROOT / "dashboard"
for extra in (SRC, DASHBOARD):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from circl_e_app import InferenceService, input_source, result_is_stale, result_key  # noqa: E402


def _summarize(view: dict[str, Any]) -> dict[str, Any]:
    identity = view.get("device_identity") or {}
    best = identity.get("best_available") or {}
    post = view.get("post_mapping") or {}
    routing = view.get("routing") or {}
    return {
        "identity_headline": best.get("headline"),
        "identity_kind": best.get("kind"),
        "reference_state": (view.get("reference_conformity") or {}).get("state"),
        "ce": {dim: (post.get(dim) or {}).get("display") for dim in ("RRP", "WRO", "CSO", "TPC", "IRP")},
        "highest_route": routing.get("highest_display"),
        "byte_sha256": (view.get("input") or {}).get("byte_sha256"),
    }


def run(image_paths: list[Path], *, device: str | None, report_path: Path | None) -> int:
    release_dir = ROOT / "runtime" / "release"
    service = InferenceService(release_dir, device=device, require_verified=False, use_cache=True)

    errors: list[str] = []
    entries: list[dict[str, Any]] = []
    keys: dict[str, str] = {}
    t0 = time.time()
    for path in image_paths:
        if not path.is_file():
            errors.append(f"image not found: {path}")
            continue
        data = path.read_bytes()
        raw_sha = hashlib.sha256(data).hexdigest()
        try:
            result, view = service.infer_and_present(data, path.name)
        except Exception as exc:  # noqa: BLE001 - reported as a smoke failure
            errors.append(f"{path.name}: inference raised {type(exc).__name__}: {exc}")
            continue
        observed_sha = (view.get("input") or {}).get("byte_sha256")
        if observed_sha != raw_sha:
            errors.append(f"{path.name}: provenance hash mismatch ({observed_sha} != {raw_sha})")
        entry = _summarize(view)
        entry["image"] = str(path)
        entry["result_type"] = type(result).__name__
        entries.append(entry)
        key = result_key(raw_sha, "smoke")
        keys[path.name] = key
        print(f"  {path.name}: {entry['identity_headline']} | {entry['reference_state']} | "
              f"CE {entry['ce']} | route {entry['highest_route']}")

    # Two distinct images must not share a staleness key (no stale-result leak).
    if len(keys) > 1:
        distinct = set(keys.values())
        if len(distinct) != len(keys):
            errors.append("two distinct images produced the same result key")
    # A stored result must be stale for a different image's key.
    names = list(keys)
    if len(names) >= 2 and not result_is_stale(keys[names[0]], keys[names[1]]):
        errors.append("result from image A was not invalidated for image B")

    # input_source precedence is a pure invariant worth asserting in the bundle.
    if input_source(True, True) != "upload":
        errors.append("input precedence invariant broken")

    report = {
        "ok": not errors,
        "software_version": "1.0.0",
        "release_dir": str(release_dir),
        "duration_seconds": round(time.time() - t0, 2),
        "images": entries,
        "errors": errors,
        "note": "Execution/state smoke only; not accuracy or OOD evidence.",
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"ok": report["ok"], "errors": errors, "duration_seconds": report["duration_seconds"]}, indent=2))
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CIRCL-E release smoke test.")
    parser.add_argument("--image", action="append", required=True, help="image path (repeatable)")
    parser.add_argument("--device", default=None, choices=[None, "cpu", "cuda"], help="compute device override")
    parser.add_argument("--json", dest="report", default=None, help="write a JSON report to this path")
    args = parser.parse_args(argv)
    images = [Path(p).expanduser() for p in args.image]
    print(f"CIRCL-E smoke test on {len(images)} image(s)")
    return run(images, device=args.device, report_path=Path(args.report) if args.report else None)


if __name__ == "__main__":
    raise SystemExit(main())
