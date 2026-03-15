# TODOS

## 1. Rebrand to generic LoRa

- [x] Rename repo/package from `meshtastic-site-planner` to `lora-planner` (package.json `name` field)
- [x] Replace "Meshtastic" with "LoRa" in all UI text, page titles, and meta tags
- [x] Replace Meshtastic logos/favicons in `public/` with transparent placeholders
- [x] Update `index.html` title and meta
- [x] Remove `site.meshtastic.org` references from CORS config, comments, and deployment docs
- [x] Rename `randanimal` site names if they reference Meshtastic concepts (N/A — randanimal is generic)
- [x] Update README.md

## 2. Podman + single-container migration

- [x] Rename `Dockerfile` → `Containerfile`
- [x] Remove nginx-proxy and acme-companion services from compose
- [x] Remove Redis service from compose
- [x] Rename `docker-compose.yml` → `compose.yml` with single `app` service + persistent volume
- [x] Update Containerfile to not install/configure Redis (N/A — Redis was never in Containerfile)
- [x] Add `/data` volume mount for SQLite + terrain cache (already in compose.yml)
- [x] Replace all `docker` references in code/comments with `podman` (N/A — no docker refs outside renamed files)
- [ ] Test `podman build` and `podman run` workflow end-to-end

## 3. Replace Redis with SQLite

- [x] Add SQLite schema: `towers` table (id, name, params JSON, geotiff BLOB, created_at, updated_at)
- [x] Add SQLite schema: `tasks` table (id, tower_id, status, error, created_at)
- [x] Create `app/db/` module with schema init and access functions
- [x] Rewrite `run_splat` to persist results to SQLite instead of Redis
- [x] Rewrite `/predict` to create task row in SQLite
- [x] Rewrite `/status/{task_id}` to read from SQLite
- [x] Rewrite `/result/{task_id}` to stream GeoTIFF from SQLite
- [x] Add `GET /towers` endpoint to list all towers with metadata (no blobs)
- [x] Add `DELETE /towers/{id}` endpoint (admin-only)
- [x] Remove `redis` from `requirements.txt`
- [x] Remove Redis client initialization from `main.py`

## 4. Drop CORS and HTTPS

- [x] Remove `CORSMiddleware` from `main.py`
- [x] Remove CORS-related imports and comments
- [x] Ensure static files still served via `StaticFiles` mount on `/`
- [ ] Verify API and UI work on same origin behind reverse proxy

## 5. Persistent towers & toggleable layers

- [x] Add frontend tower list panel showing all persisted towers
- [x] Add per-tower visibility toggle (eye/no-entry icon)
- [x] Implement toggle via `setOpacity(0)` / `setOpacity(original)` — no layer remove/re-add
- [x] On page load, fetch `GET /towers` and load tower metadata
- [x] Store per-tower visibility state in Pinia (not in the DOM)
- [x] Add tower delete button (admin-only, gated by `store.isAdmin`)

## 6. Admin/visitor auth

- [x] Define admin credential source (environment variable: `ADMIN_PASSWORD`, rate-limited login)
- [x] Add FastAPI auth dependency (Bearer token = static password)
- [x] Protect `POST /predict`, `DELETE /towers/{id}`, and any future mutation endpoints
- [x] Leave `GET /towers`, `GET /status`, `GET /result` public
- [x] Add login UI for admin (modal with password field, lock icon in navbar, localStorage persistence)
- [x] Visitor mode: hide simulation form, show only map + tower list with toggles

## 7. Hardware & environment presets

- [x] Create `src/presets/hardware.ts` with Heltec V3 (max 22 dBm / 158 mW, SX1262), Heltec V4 (max 22 dBm / 158 mW, SX1262), custom (all fields unlocked)
- [x] Create `src/presets/frequencies.ts` keyed by country code (Canada 907 MHz, US 915 MHz, EU 868 MHz, etc.)
- [x] Create `src/presets/antennas.ts` with curated antenna list (name, gain dBi, SWR): Ribbed Spring Helical (0 dBi, 3.0), Duck Stubby (1 dBi, 3.5), Bingfu Whip (2.5 dBi, 1.8), Slinkdsco Omni (4 dBi, 1.1)
- [x] Calculate SWR mismatch loss: `loss_dB = -10 * log10(1 - ((SWR-1)/(SWR+1))²)` and subtract from TX power before sending to SPLAT!
- [x] Add SWR mismatch loss calculation to backend `app/services/splat.py` (apply to effective TX power)
- [x] Display computed mismatch loss in UI next to antenna selector (informational)
- [x] Create `src/presets/heights.ts` mapping labels to meters (ground: 1m, first floor window: 3m, second floor window: 6m, gutter line: 8m, rooftop: 10m, ground tower: 30m, roof tower: 15m)
- [x] Add hardware selector dropdown to transmitter form
- [x] Add country/region selector that auto-fills frequency
- [x] Add antenna selector dropdown (with mismatch loss badge)
- [x] Add height preset dropdown (with manual override)
- [x] Lock auto-filled fields in preset mode, unlock all in custom mode

## 8. Pre-cached client simulation matrix

Towers have fixed hardware/antenna/height configs set by admin. The matrix varies the **client (receiver)** side — showing "what coverage does a visitor with client hardware X and antenna Y see from this tower?" Each axis of the matrix is admin-configurable: the admin enables/disables individual members per axis, and only the enabled combinations are simulated. This keeps compute time manageable while allowing full flexibility.

### Matrix axes (all toggled by admin)
- **Client hardware** — e.g., Heltec V3, Heltec V4, Custom. Admin enables which hardware options visitors can select.
- **Client antenna** — e.g., Ribbed Spring Helical, Duck Stubby, Bingfu Whip, Slinkdsco Omni. Admin enables which antennas to simulate.
- **Terrain model** — Bare-earth SRTM, DSM, LULC-burned clutter. Admin enables which terrain modes are available.
- Total simulations per tower = enabled hardware × enabled antennas × enabled terrain models (e.g., 2 × 3 × 2 = 12 instead of full 2 × 4 × 3 = 24)

### Terrain model modes
- **Bare-earth SRTM** — existing behavior, standard 1/3-arcsecond SRTM DTM tiles from AWS Open Data
- **DSM (Digital Surface Model)** — includes buildings and tree canopy as elevation; sources: USGS 3DEP (US), provincial LiDAR (Canada), Copernicus GLO-30 DSM. SPLAT! treats surface features as terrain that naturally blocks signals — no code changes to the propagation model
- **LULC-burned clutter** — SRTM bare-earth tiles with per-pixel clutter heights added from ESA WorldCover (10m, global, free). Land cover classes map to clutter heights (e.g., forest=12m, suburban=8m, urban=20m, cropland=0m, water=0m). Synthetic but global coverage with no DSM gaps

### Admin matrix configuration
- [ ] Store enabled matrix members in SQLite settings table (or JSON column): `{"hardware": ["v3", "v4"], "antennas": ["bingfu_whip", "slinkdsco_omni"], "terrain": ["bare_earth", "lulc_clutter"]}`
- [ ] Add admin UI panel to toggle individual members on each axis (checkboxes per hardware, antenna, terrain model)
- [ ] Changing the enabled set triggers delta computation: queue only the new combinations, don't re-run existing ones
- [ ] Disabling a member hides it from the visitor selector but retains cached results (can be re-enabled without re-simulating)

### Simulation & storage
- [ ] Matrix varies receiver gain, sensitivity, SWR mismatch loss, and terrain model — tower TX params stay fixed
- [ ] Add backend endpoint or CLI command to batch-run matrix simulations for a given tower
- [ ] Store each matrix result as a separate GeoTIFF in SQLite, keyed by tower_id + client_hardware + client_antenna + terrain_model
- [ ] On tower creation, auto-queue the enabled matrix combinations as background tasks
- [ ] Show matrix completion progress in admin UI (e.g., "8/12 simulations complete")

### Visitor UI
- [ ] Add selectors for visitors to pick their client hardware + antenna + terrain model — only enabled options shown
- [ ] Instantly display the matching cached coverage layer (no simulation round-trip for visitors)

## 9. Frontend performance refactors (`src/store.ts`)

- [x] Store a `GeoRasterLayer` ref on each `Site` object instead of recreating layers on every redraw
- [x] Replace `redrawSites()` remove/re-add with per-site `setOpacity()` toggling and `bringToFront()` on baselayerchange
- [x] Fix `removeSite()` double layer iteration — with per-site refs, just call `map.removeLayer(site.layer)`
- [x] Remove needless `{...site}.raster` shallow clone — pass `site.raster` directly
- [x] Wire `display.overlay_transparency` to GeoRasterLayer opacity (currently hardcoded 0.7)
- [x] Add retry cap, exponential backoff, and abort handling to `pollStatus()` loop

## 10. Backend DRY & code quality

- [x] `app/services/splat.py` — replace 4× repeated binary isfile+access validation with a loop over a dict
- [x] `app/services/splat.py` — extract shared colormap RGB helper (duplicated in `_create_splat_dcf`, `_create_splat_geotiff`, `create_splat_colorbar`)
- [x] `app/services/splat.py` — extract `_fetch_and_cache(s3_key, cache_key)` helper in `_download_terrain_tile` (V1 fallback duplicates fetch+cache block)
- [x] `app/services/splat.py` — add `from e` exception chaining to all re-raises (currently drops tracebacks)
- [x] `app/services/splat.py` — migrate `os.path` usage to `pathlib.Path` per CLAUDE.md code standards
- [x] `app/main.py` — make `get_db()` a context manager to eliminate 5× repeated `conn = get_db() / try / finally: conn.close()` boilerplate
- [x] `app/db/schema.py` — have `init_db()` use `get_db()` instead of opening its own raw connection (duplicates PRAGMA setup)
- [x] `pyproject.toml` — `haversine` is listed as a dependency but never imported (already removed)

## 11. Per-tower color rendering & overlap hatching

Each tower gets a user-assigned color. Coverage is rendered as that solid color with transparency proportional to signal strength. Transparency maps to reception quality: **10% transparency (nearly opaque) = minimum signal threshold** (barely receivable by the selected client device), **80% transparency (nearly invisible) = perfect reception**. This means strong-signal areas fade out while weak-signal edges are prominently visible — highlighting the coverage boundary, which is the most useful information for placement decisions.

Where multiple towers overlap, the area uses cross-hatched line shading — each tower's lines drawn in its color, with line thickness proportional to that tower's signal strength (stronger signal = thicker lines).

### Phase 1 — Per-tower solid color rendering
- [ ] Add `color` field to towers table (hex string, e.g., "#ff0000") and Site/SplatParams types
- [ ] Add color picker to tower creation form (admin), cycling through a 24-color palette: all permutations of `{0, 128, 255}` on R, G, B excluding greyscale `(0,0,0)`, `(128,128,128)`, `(255,255,255)`
- [ ] Replace matplotlib colormap rendering with single-color + alpha: use `pixelValuesToColorFn` on GeoRasterLayer to map dBm → alpha on the tower's color
- [ ] Alpha mapping: 10% transparency (alpha ≈ 230) at `signal_threshold` (minimum receivable), linearly scaling to 80% transparency (alpha ≈ 51) at max dBm (perfect reception). Pixels below threshold get alpha 0 (fully transparent / no coverage).
- [ ] Backend: generate "raw dBm" GeoTIFFs (no colormap baked in) so frontend controls visualization
- [ ] Store raw dBm GeoTIFFs — colormap is now a frontend concern, not baked into the raster

### Phase 2 — Overlap detection & hatched rendering
- [ ] Create a custom Leaflet canvas layer (`OverlapHatchLayer`) that composites all visible tower rasters
- [ ] For each pixel, determine which towers have coverage (signal above threshold)
- [ ] Single-tower pixel → solid color + alpha based on signal strength (same 10%–80% transparency scale)
- [ ] Multi-tower pixel → draw diagonal stripes per tower, each in that tower's color
- [ ] Line thickness scales with signal strength relative to other towers at that pixel (stronger = thicker lines)
- [ ] Each tower gets a unique stripe angle (e.g., tower A = 45°, tower B = 135°) for natural cross-hatching
- [ ] Toggle between "hatched overlap" and "simple alpha blend" modes in display settings

## 12. Deadzone remediation suggestion layer

Toggleable overlay that analyzes gaps in the combined coverage of all towers and highlights deadzones. Rendered as a **white dotted pattern** with transparency proportional to deadzone severity: areas with zero coverage from any tower are **80% opaque** (strong white dots), areas with weak partial coverage fade toward fully transparent. Requires at least 2 existing towers with completed simulations.

### Analysis
- [ ] Compute a "coverage gap" raster from all active tower simulations: for each pixel, record the best signal from any tower (or no-coverage if below threshold everywhere)
- [ ] Identify contiguous deadzone regions (connected components of no-coverage pixels within the simulation extent)
- [ ] Score each deadzone by area and proximity to existing coverage edges — large gaps adjacent to near-threshold signal are highest priority (a new tower there extends the network most efficiently)
- [ ] Filter out deadzones that are too small (noise) or too far from any existing coverage (unreachable by a single new tower)

### Rendering
- [ ] Render deadzones as white dotted/stippled pattern on a canvas overlay layer
- [ ] Transparency scales with deadzone severity: complete deadzone (no signal from any tower) = 80% opaque white dots (alpha ≈ 204), near-threshold weak signal = nearly transparent, above-threshold coverage = fully transparent (no dots)
- [ ] Dot density or size can optionally scale with severity for additional visual weight in the worst gaps

### Suggestion markers
- [ ] For candidate points within or adjacent to deadzones, estimate how much deadzone area a new tower at that point would cover (based on terrain LOS from that point, using a simplified or cached SPLAT! model)
- [ ] Show top-N suggested sites as numbered markers with estimated coverage gain (e.g., "~12 km² new coverage")

### UI
- [ ] Add toggle in display settings: "Show deadzone remediation" (disabled until ≥2 towers exist)
- [ ] Clicking a suggestion marker opens a popup with: estimated new coverage area, terrain summary, option to pre-fill the transmitter form with that location's coordinates
- [ ] Recompute suggestions when towers are added, removed, or simulations complete

## 13. Multi-source terrain data pipeline

Support three terrain elevation sources that feed into SPLAT! via the existing tile preprocessing step (`_convert_hgt_to_sdf`). SPLAT! itself doesn't change — it always reads `.sdf` tiles. The difference is what elevation values those tiles contain.

### Bare-earth SRTM (existing)
- [x] Download 1-arcsecond SRTM `.hgt.gz` tiles from AWS `elevation-tiles-prod`
- [x] Downsample to 3-arcsecond for standard resolution mode
- [x] Convert to SPLAT! `.sdf` via `srtm2sdf`

### DSM (Digital Surface Model)
- [ ] Add DSM tile source support: USGS 3DEP (US), Copernicus GLO-30 DSM (global 30m, free via AWS/OpenData), provincial LiDAR (Canada)
- [ ] DSM tiles include buildings and tree canopy as elevation — SPLAT! treats them as terrain that blocks signals
- [ ] Implement DSM tile downloader with same cache pattern as SRTM (`diskcache` keyed by `dsm:{tile_name}`)
- [ ] Fall back to bare-earth SRTM for tiles where DSM data is unavailable
- [ ] Convert DSM `.hgt` to `.sdf` using same `srtm2sdf` pipeline

### LULC-burned clutter
- [ ] Download ESA WorldCover tiles (10m GeoTIFF, global, free) — classify each pixel as tree cover, shrubland, grassland, cropland, built-up, bare/sparse, water, wetland, etc.
- [ ] Define clutter height lookup table per land cover class (e.g., tree cover=12m, built-up=20m, shrubland=3m, cropland=0m, water=0m)
- [ ] In tile preprocessing: load SRTM bare-earth tile + co-located WorldCover tile, resample WorldCover to match SRTM grid, add per-pixel clutter height to elevation values
- [ ] Cache the burned tiles separately (`lulc:{tile_name}`) so bare-earth originals remain available
- [ ] Convert burned `.hgt` to `.sdf` using same `srtm2sdf` pipeline

### Terrain model selection
- [ ] Add `terrain_model` field to `CoveragePredictionRequest`: `"bare_earth"` (default), `"dsm"`, `"lulc_clutter"`
- [ ] Route tile download/preprocessing through the selected model in `coverage_prediction()`
- [ ] Store terrain model used alongside each simulation result in SQLite

## 14. Meshcore tower path simulation

- [ ] Add SPLAT! point-to-point analysis function in `app/services/splat.py`
- [ ] Add `POST /tower-paths` endpoint that runs pairwise P2P between selected towers
- [ ] Store path results (path loss, LOS status) in SQLite `tower_paths` table
- [ ] Add `GET /tower-paths` endpoint returning all computed paths
- [ ] Render paths as Leaflet polylines between tower markers (color-coded by path quality)
- [ ] Add toggle to show/hide mesh path overlay independently from coverage layers
- [ ] Recalculate affected paths when a tower is added or removed
