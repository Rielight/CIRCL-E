# CIRCL-E Dashboard

Local inference dashboard for electronic-device images. It reports:

- **device / component identity** (family, subtype, component);
- **reference conformity** (does the image sit inside the frozen reference domain?);
- **circular-economy profile** — RRP · WRO · CSO · TPC · IRP;
- **route affinity** (ordinal compatibility, not a recommendation).

Inference is fully local and frozen: no internet access, no runtime training,
and no model download. Runtime stack:

```text
Streamlit -> circl_e_app -> frozen circl_e_ai -> frozen DINO + C-RADIO
```

> **Research / decision-support release.** Outputs are evidence, not a certified
> verdict or a hazard assessment. The bundled model release carries its own
> scientific verification status; it is not claimed to be production-certified.

## Requirements

- Linux with an NVIDIA GPU and a working CUDA driver (CPU fallback exists but is slow).
- The Frozen backbone model directories (external, read-only):
  - DINOv3 model directory;
  - C-RADIOv4 model directory.
- Python 3.11+ (validated on 3.13) for the local option.

## Option A — Docker (recommended)

1. Copy the environment template and set your host model paths:
   ```bash
   cp .env.example .env
   # edit .env:
   #   CIRCL_DINO_HOST_DIR=/absolute/path/to/dinov3
   #   CIRCL_CRADIO_HOST_DIR=/absolute/path/to/cradio
   ```
2. Build and start:
   ```bash
   docker compose up --build
   ```
3. Open <http://localhost:8501>.

The model directories are mounted read-only. Multi-GB checkpoints are **not**
baked into the image. The NVIDIA Container Toolkit is required.

Health endpoint: `http://localhost:8501/_stcore/health` (returns `ok`).

## Option B — local Python

1. Create a virtual environment and install the pinned runtime:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.lock
   ```
2. Point the process at the frozen backbones:
   ```bash
   export CIRCL_DINO_DIR=/absolute/path/to/dinov3
   export CIRCL_CRADIO_DIR=/absolute/path/to/cradio
   ```
3. Launch:
   ```bash
   ./scripts/run_local.sh
   ```
   or explicitly:
   ```bash
   PYTHONPATH=src streamlit run dashboard/app.py
   ```

## Model directories

The release ships its fitted/static artifacts under `runtime/release/`. Only the
large backbone checkpoints are external:

| Variable | Meaning |
| --- | --- |
| `CIRCL_DINO_DIR` | DINOv3 model directory (local runs) |
| `CIRCL_CRADIO_DIR` | C-RADIOv4 model directory (local runs) |
| `CIRCL_DINO_HOST_DIR` / `CIRCL_CRADIO_HOST_DIR` | host paths mounted by Docker Compose |
| `CIRCL_RELEASE_DIR` | release directory (default `runtime/release`) |
| `CIRCLE_PORT` | dashboard port (default `8501`) |

The container maps the host variables to `/models/dino` and `/models/cradio`.

## Supported images

`JPG`, `JPEG`, `PNG`, `WEBP`; maximum 25 MB per file. Grayscale and RGBA images
are converted to RGB. EXIF orientation is applied. Corrupted files fail cleanly.

## Verify the runtime

```bash
python scripts/verify_runtime.py
```

Checks the bundle layout, the frozen release, the backbone directories/files,
version compatibility and CUDA availability, and fails before Streamlit loads
multi-GB weights if something is wrong.

## Troubleshooting

- **"The released model directories are missing"** — set `CIRCL_DINO_DIR` /
  `CIRCL_CRADIO_DIR` (local) or `CIRCL_DINO_HOST_DIR` / `CIRCL_CRADIO_HOST_DIR`
  (Docker) and re-run `verify_runtime.py`.
- **No GPU / falls back to CPU** — install a working NVIDIA driver; without CUDA
  the app still runs but inference is much slower.
- **CUDA out of memory** — close other GPU processes, or run with a smaller
  concurrent load; the app processes one image at a time.
- **Port already in use** — set `CIRCLE_PORT` to a free port.

## Contents

```text
dashboard/            Streamlit app (app.py, components.py, state.py, styles.py)
src/                  frozen runtime (circl_e_ai) + thin app layer (circl_e_app)
runtime/release/      frozen release assets (fitted/static artifacts)
scripts/              run_local.sh, verify_runtime.py, smoke_test.py
requirements.lock     pinned runtime dependencies
RELEASE_MANIFEST.json build provenance, model bindings, hashes
SHA256SUMS            checksums of every bundled file
```
