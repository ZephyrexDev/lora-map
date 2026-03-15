<p align="center">
  <img src="public/logo.svg" alt="LoRa Map" width="80" />
</p>

<h1 align="center">LoRa Map</h1>

<p align="center">
  <strong>Full-stack radio coverage prediction tool using SPLAT! and the ITM/Longley-Rice propagation model.</strong>
</p>

<p align="center">
  <a href="https://github.com/ZephyrexDev/lora-map/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/ZephyrexDev/lora-map/ci.yml?branch=main&label=CI&logo=github" alt="CI"></a>
  <a href="https://github.com/ZephyrexDev/lora-map/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue?logo=gnu" alt="License: GPL-3.0"></a>
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white" alt="TypeScript 5.9">
  <img src="https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue 3.5">
  <img src="https://img.shields.io/badge/code%20style-black-000000?logo=python" alt="Code style: Black">
  <img src="https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black" alt="Lint: Ruff">
  <img src="https://img.shields.io/badge/format-prettier-F7B93E?logo=prettier&logoColor=black" alt="Format: Prettier">
</p>

---

## Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Development](#-development)
- [Testing](#-testing)
- [Model & Assumptions](#-model--assumptions)
- [Acknowledgements](#-acknowledgements)
- [License](#-license)

---

## Overview

LoRa Map is a web-based radio coverage planner that generates RF propagation predictions using [SPLAT!](https://www.qsl.net/kd2bd/splat.html) (Signal Propagation, Loss, And Terrain) by John A. Magliacane, KD2BD. Admins configure tower sites with hardware presets, run coverage simulations, and build multi-tower mesh path visualizations. Visitors see cached results with independently toggleable coverage layers on an interactive Leaflet map.

Terrain elevation data is streamed from [AWS Open Data](https://registry.opendata.aws/terrain-tiles/) based on the NASA SRTM (Shuttle Radar Topography) dataset.

> Forked from [meshtastic/meshtastic-site-planner](https://github.com/meshtastic/meshtastic-site-planner). See commit history for changes.

---

## Features

| Category | Details |
|---|---|
| **Coverage Prediction** | ITM/Longley-Rice propagation model via SPLAT!, configurable frequency/power/gain/height, per-tower color-coded layers with signal-strength alpha mapping |
| **Hardware Presets** | Pre-configured profiles for Heltec V3/V4, region-locked frequencies (CA/US/EU/AU/AS), curated antenna list with SWR mismatch loss calculation |
| **Multi-Tower Support** | Independent per-tower layers, visibility toggling without re-rendering, automatic color assignment from a 24-color palette |
| **Admin/Visitor Roles** | Admin credentials gate simulation triggers and tower management; visitors see cached results instantly with no edit capability |
| **Persistent Storage** | Tower configs, simulation results, and GeoTIFF blobs persisted in SQLite on a mounted volume |
| **Single Container** | One Podman container, HTTP on port 8080, sits behind your existing HTTPS reverse proxy |

---

## Architecture

```
src/                  Vue 3 + TypeScript frontend (Pinia, Leaflet, Bootstrap)
app/                  FastAPI backend
  main.py               API endpoints + static file serving
  services/splat.py     SPLAT! subprocess wrapper, terrain tile pipeline
  models/               Pydantic request/response models
  db/                   SQLite schema, migrations, connection factory
  auth.py               Bearer-token admin auth with rate limiting
  colors.py             24-color palette assignment
splat/                Git submodule — SPLAT! C source
Containerfile         Single-container Podman build
compose.yml           Optional dev convenience
```

**Data flow:** Vue form &#8594; Pinia store &#8594; `POST /predict` (admin-authed) &#8594; background task runs SPLAT! &#8594; GeoTIFF persisted in SQLite &#8594; frontend polls `/status`, fetches `/result` &#8594; rendered as independent `GeoRasterLayer` with per-tower color + alpha. Visitors hit `GET /towers` to load all cached layers directly.

---

## Quick Start

**Requirements:** Podman (or Docker), Git

```bash
git clone --recurse-submodules https://github.com/ZephyrexDev/lora-map.git
cd lora-map

podman build -f Containerfile -t lora-map .
podman run -p 8080:8080 -v lora-data:/data lora-map
```

Open [http://localhost:8080](http://localhost:8080).

To enable admin authentication, set the `ADMIN_PASSWORD` environment variable:

```bash
podman run -p 8080:8080 -v lora-data:/data -e ADMIN_PASSWORD=yourpassword lora-map
```

---

## Usage

1. Open the tool in a web browser and log in as admin (if `ADMIN_PASSWORD` is set).
2. In **Site / Transmitter**, enter coordinates and antenna height. Select a hardware preset or manually configure power, frequency, and gain.
3. In **Receiver**, configure sensitivity, height, and gain for the target client device.
4. In **Simulation**, set the maximum range in km. Ranges above 50 km increase computation time.
5. Press **Run Simulation**. The coverage layer renders when computation completes.

Repeat for additional tower sites. Each tower gets its own color and independently toggleable layer.

---

## Development

**Requirements:** Node.js 22+, pnpm, Python 3.11+, [uv](https://docs.astral.sh/uv/), g++, libbz2-dev

```bash
# Clone and build SPLAT! binaries
git clone --recurse-submodules https://github.com/ZephyrexDev/lora-map.git
cd lora-map
cd splat && bash build all && cd utils && bash build all && cd ../..

# Frontend
pnpm install
pnpm run dev              # Vite dev server

# Backend
uv sync
SPLAT_PATH=splat/bin uv run uvicorn app.main:app --host 0.0.0.0 --port 8080

# Build for production
pnpm run build            # Type-check + build + copy to app/ui
```

---

## Testing

```bash
# Backend (pytest)
uv run pytest -v

# Frontend (vitest)
pnpm run test
```

| Suite | Framework | Tests |
|---|---|---|
| Backend | pytest | 196 |
| Frontend | Vitest | 50 |
| **Total** | | **246** |

All tests run against real code with zero mocks — SPLAT! binaries are built from source during test setup.

---

## Model & Assumptions

This tool runs a physics simulation with the following key assumptions:

1. **Terrain resolution:** SRTM elevation data is accurate to ~90 m (3-arcsecond) or ~30 m (1-arcsecond HD mode).
2. **No surface clutter by default:** Buildings, trees, and other obstructions beyond terrain are not modeled. The uniform `clutter_height` parameter can approximate ground-level obstructions. Future support for DSM tiles and LULC-burned clutter is planned.
3. **Isotropic antennas:** Horizontal radiation patterns are assumed omnidirectional. Directional antenna patterns are not modeled.
4. **No skywave propagation:** Upper-atmosphere reflections are assumed negligible, which is less accurate below ~50 MHz.

A detailed description of all model parameters and their recommended values is available in [parameters.md](parameters.md).

---

## Acknowledgements

- **SPLAT!** by John A. Magliacane, KD2BD — [qsl.net/kd2bd/splat.html](https://www.qsl.net/kd2bd/splat.html)
- **ITM/Longley-Rice** propagation model — NTIA/ITS
- **SRTM terrain data** — NASA/USGS via [AWS Open Data](https://registry.opendata.aws/terrain-tiles/)
- Originally forked from [meshtastic/meshtastic-site-planner](https://github.com/meshtastic/meshtastic-site-planner)

---

## License

This project is licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE) for details.
