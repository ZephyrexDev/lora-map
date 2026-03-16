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

## Who This Is For

Meshcore and LoRa communities with fixed tower infrastructure who want to **plan new sites with real propagation physics** and **share current coverage maps with their community**. Admins run simulations; visitors see the results on an interactive map — no RF expertise required.

## Why LoRa Map?

The [upstream planner](https://github.com/meshtastic/meshtastic-site-planner) runs single-tower, single-terrain simulations. LoRa Map builds on that foundation with multi-tower network planning, real-world terrain modeling, and a visitor-facing coverage portal.

- **Multi-source terrain** — Go beyond flat bare-earth SRTM. Simulate against Copernicus DSM (buildings + tree canopy), ESA WorldCover LULC clutter, or a weighted aggregate that blends all three for a realistic "expected coverage" estimate.
- **Batch simulation matrix** — Pre-compute coverage for every combination of client hardware, antenna, and terrain model. Visitors instantly switch scenarios — no simulation wait, no admin involvement.
- **Deadzone remediation** — Automatically find coverage gaps across your network, rank them by priority, and suggest where to place new towers with estimated coverage gain.
- **Mesh path analysis** — Pairwise SPLAT! point-to-point between all towers. See line-of-sight status, path loss, and link quality as color-coded polylines — understand your mesh backbone at a glance.
- **Overlap visualization** — Per-tower color-coded layers with signal-strength transparency. Multi-coverage areas render as cross-hatched patterns so you can distinguish each tower's contribution.
- **Hardware-aware presets** — Heltec V3/V4 profiles, region-locked frequencies (CA/US/EU/AU/AS), curated antennas with automatic SWR mismatch loss calculated and deducted.
- **Visitor portal** — Community members pick their client device and antenna from dropdowns and see personalized coverage maps. No login, no configuration, instant results.
- **One container** — Single Podman image, one port, one volume mount. Deploys behind your existing reverse proxy in minutes.

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
| **Multi-Source Terrain** | Bare-earth SRTM, Copernicus DSM (buildings + canopy), ESA WorldCover LULC clutter, and weighted aggregate blend mode |
| **Batch Simulation Matrix** | Admin-configurable client hardware × antenna × terrain combinations, pre-computed so visitors get instant layer switching |
| **Deadzone Remediation** | Gap analysis across all towers, priority-scored deadzone regions, suggested new tower placements with estimated coverage gain |
| **Mesh Path Analysis** | Pairwise SPLAT! point-to-point between towers, path loss and LOS status, color-coded polyline overlay |
| **Overlap Visualization** | Cross-hatched canvas layer distinguishes per-tower signal contributions in multi-coverage areas |
| **Hardware Presets** | Heltec V3/V4 profiles, region-locked frequencies (CA/US/EU/AU/AS), curated antennas with SWR mismatch loss |
| **Admin/Visitor Roles** | Rate-limited admin auth gates mutations; visitors see cached results instantly with client hardware/antenna/terrain selectors |
| **Mobile Responsive** | Full responsive layout with touch-friendly controls, sticky simulation button, and adaptive offcanvas sidebar |
| **Single Container** | One Podman container, HTTP on port 8080, SQLite on a mounted volume, sits behind your existing reverse proxy |

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
| Backend | pytest | 341 |
| Frontend | Vitest | 232 |
| **Total** | | **573** |

All tests run against real code with zero mocks — SPLAT! binaries are built from source during test setup.

---

## Model & Assumptions

This tool runs a physics simulation with the following key assumptions:

1. **Terrain resolution:** SRTM elevation data is accurate to ~90 m (3-arcsecond) or ~30 m (1-arcsecond HD mode).
2. **Surface clutter is optional:** By default, bare-earth SRTM terrain has no buildings or vegetation. Enable DSM (Copernicus GLO-30) or LULC clutter (ESA WorldCover) terrain modes for simulations that include surface obstructions. The weighted aggregate mode blends all three sources.
3. **Isotropic antennas:** Horizontal radiation patterns are assumed omnidirectional. Directional antenna patterns are not modeled.
4. **No skywave propagation:** Upper-atmosphere reflections are assumed negligible, which is less accurate below ~50 MHz.

A detailed description of all model parameters and their recommended values is available in [docs/parameters.md](docs/parameters.md).

---

## Acknowledgements

- **SPLAT!** by John A. Magliacane, KD2BD — [qsl.net/kd2bd/splat.html](https://www.qsl.net/kd2bd/splat.html)
- **ITM/Longley-Rice** propagation model — NTIA/ITS
- **SRTM terrain data** — NASA/USGS via [AWS Open Data](https://registry.opendata.aws/terrain-tiles/)
- Originally forked from [meshtastic/meshtastic-site-planner](https://github.com/meshtastic/meshtastic-site-planner)

---

## License

This project is licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE) for details.
