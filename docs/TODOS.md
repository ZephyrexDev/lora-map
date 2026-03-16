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
- [x] Store enabled matrix members in SQLite settings table (or JSON column): `{"hardware": ["v3", "v4"], "antennas": ["bingfu_whip", "slinkdsco_omni"], "terrain": ["bare_earth", "lulc_clutter"]}`
- [x] Add admin UI panel to toggle individual members on each axis (checkboxes per hardware, antenna, terrain model)
- [x] Changing the enabled set triggers delta computation: queue only the new combinations, don't re-run existing ones
- [x] Disabling a member hides it from the visitor selector but retains cached results (can be re-enabled without re-simulating)

### Simulation & storage
- [x] Matrix varies receiver gain, sensitivity, SWR mismatch loss, and terrain model — tower TX params stay fixed
- [x] Add backend endpoint or CLI command to batch-run matrix simulations for a given tower
- [x] Store each matrix result as a separate GeoTIFF in SQLite, keyed by tower_id + client_hardware + client_antenna + terrain_model
- [x] On tower creation, auto-queue the enabled matrix combinations as background tasks
- [x] Show matrix completion progress in admin UI (e.g., "4/8" badge, polls every 5s while pending)

### Visitor UI
- [x] Add selectors for visitors to pick their client hardware + antenna + terrain model — only enabled options shown
- [x] Instantly display the matching cached coverage layer (no simulation round-trip for visitors)

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
- [x] Add `color` field to towers table (hex string, e.g., "#ff0000") and Site/SplatParams types
- [x] Add color picker to tower creation form (admin), cycling through a 24-color palette: all permutations of `{0, 128, 255}` on R, G, B excluding greyscale `(0,0,0)`, `(128,128,128)`, `(255,255,255)`
- [x] Replace matplotlib colormap rendering with single-color + alpha: use `pixelValuesToColorFn` on GeoRasterLayer to map dBm → alpha on the tower's color
- [x] Alpha mapping: 10% transparency (alpha ≈ 230) at `signal_threshold` (minimum receivable), linearly scaling to 80% transparency (alpha ≈ 51) at max dBm (perfect reception). Pixels below threshold get alpha 0 (fully transparent / no coverage).
- [x] Backend: generate "raw dBm" GeoTIFFs (reverse-map PPM colors to dBm via DCF LUT)
- [x] Store raw dBm GeoTIFFs — colormap is now a frontend concern, not baked into the raster

### Phase 2 — Overlap detection & hatched rendering
- [x] Create a custom Leaflet canvas layer (`OverlapHatchLayer`) that composites all visible tower rasters
- [x] For each pixel, determine which towers have coverage (signal above threshold)
- [x] Single-tower pixel → solid color + alpha based on signal strength (same 10%–80% transparency scale)
- [x] Multi-tower pixel → draw diagonal stripes per tower, each in that tower's color
- [x] Line thickness scales with signal strength relative to other towers at that pixel (stronger = thicker lines)
- [x] Each tower gets a unique stripe angle (e.g., tower A = 45°, tower B = 135°) for natural cross-hatching
- [x] Toggle between "hatched overlap" and "simple alpha blend" modes in display settings

## 12. Deadzone remediation suggestion layer

Toggleable overlay that analyzes gaps in the combined coverage of all towers and highlights deadzones. Rendered as a **white dotted pattern** with transparency proportional to deadzone severity: areas with zero coverage from any tower are **80% opaque** (strong white dots), areas with weak partial coverage fade toward fully transparent. Requires at least 2 existing towers with completed simulations.

### Analysis
- [x] Compute a "coverage gap" raster from all active tower simulations: for each pixel, record the best signal from any tower (or no-coverage if below threshold everywhere)
- [x] Identify contiguous deadzone regions (connected components of no-coverage pixels within the simulation extent)
- [x] Score each deadzone by area and proximity to existing coverage edges — large gaps adjacent to near-threshold signal are highest priority (a new tower there extends the network most efficiently)
- [x] Filter out deadzones that are too small (noise) or too far from any existing coverage (unreachable by a single new tower)

### Rendering
- [x] Render deadzones as white dotted/stippled pattern on a canvas overlay layer
- [x] Transparency scales with deadzone severity: complete deadzone (no signal from any tower) = 80% opaque white dots (alpha ≈ 204), near-threshold weak signal = nearly transparent, above-threshold coverage = fully transparent (no dots)
- [x] Dot density or size can optionally scale with severity for additional visual weight in the worst gaps

### Suggestion markers
- [x] For candidate points within or adjacent to deadzones, estimate how much deadzone area a new tower at that point would cover (based on terrain LOS from that point, using a simplified or cached SPLAT! model)
- [x] Show top-N suggested sites as numbered markers with estimated coverage gain (e.g., "~12 km² new coverage")

### UI
- [x] Add toggle in display settings: "Show deadzone remediation" (disabled until ≥2 towers exist)
- [x] Clicking a suggestion marker opens a popup with: estimated new coverage area, terrain summary, option to pre-fill the transmitter form with that location's coordinates
- [x] Recompute suggestions when towers are added, removed, or simulations complete

## 13. Multi-source terrain data pipeline

Support three terrain elevation sources that feed into SPLAT! via the existing tile preprocessing step (`_convert_hgt_to_sdf`). SPLAT! itself doesn't change — it always reads `.sdf` tiles. The difference is what elevation values those tiles contain.

### Bare-earth SRTM (existing)
- [x] Download 1-arcsecond SRTM `.hgt.gz` tiles from AWS `elevation-tiles-prod`
- [x] Downsample to 3-arcsecond for standard resolution mode
- [x] Convert to SPLAT! `.sdf` via `srtm2sdf`

### DSM (Digital Surface Model)
- [x] Add DSM tile source support: Copernicus GLO-30 DSM (global 30m, free via AWS/OpenData)
- [x] DSM tiles include buildings and tree canopy as elevation — SPLAT! treats them as terrain that blocks signals
- [x] Implement DSM tile downloader with same cache pattern as SRTM (`diskcache` keyed by `dsm:{tile_name}`)
- [x] Fall back to bare-earth SRTM for tiles where DSM data is unavailable
- [x] Convert DSM `.hgt` to `.sdf` using same `srtm2sdf` pipeline

### LULC-burned clutter
- [x] Download ESA WorldCover tiles (10m GeoTIFF, global, free) — classify each pixel as tree cover, shrubland, grassland, cropland, built-up, bare/sparse, water, wetland, etc.
- [x] Define clutter height lookup table per land cover class (e.g., tree cover=12m, built-up=20m, shrubland=3m, cropland=0m, water=0m)
- [x] In tile preprocessing: load SRTM bare-earth tile + co-located WorldCover tile, resample WorldCover to match SRTM grid, add per-pixel clutter height to elevation values
- [x] Cache the burned tiles separately (`lulc:{tile_name}`) so bare-earth originals remain available
- [x] Convert burned `.hgt` to `.sdf` using same `srtm2sdf` pipeline

### Weighted Aggregate mode
A fourth virtual terrain model that blends the three real models into a single composite prediction. No additional SPLAT! run — it's a weighted pixel-level blend of the three existing simulation results.

- [x] For each pixel, compute: `signal_dBm = 0.20 × bare_earth + 0.40 × DSM + 0.40 × LULC_clutter`
- [x] Requires all three base terrain simulations to be completed for the tower+client combination; skip pixels where any source has no data
- [x] Generate the aggregate as a derived GeoTIFF (or compute on-the-fly in the frontend `pixelValuesToColorFn` if all three rasters are loaded)
- [x] Rationale: bare-earth is optimistic (no obstructions), DSM and LULC each capture different real-world blockage — weighting them equally at 40% each gives a practical "expected real-world" estimate while the 20% bare-earth component prevents over-pessimism in areas where DSM/LULC data is noisy
- [x] Add `"weighted_aggregate"` as a terrain model option in the visitor UI selector (only available when all three base models are cached)

### Terrain model selection
- [x] Add `terrain_model` field to `CoveragePredictionRequest`: `"bare_earth"` (default), `"dsm"`, `"lulc_clutter"`
- [x] Route tile download/preprocessing through the selected model in `coverage_prediction()`
- [x] Store terrain model used alongside each simulation result in SQLite (simulations table has terrain_model column)
- [x] `"weighted_aggregate"` is computed from cached results, not a separate SPLAT! run

## 14. Meshcore tower path simulation

- [x] Add SPLAT! point-to-point analysis function in `app/services/splat.py`
- [x] Add `POST /tower-paths` endpoint that runs pairwise P2P between selected towers
- [x] Store path results (path loss, LOS status) in SQLite `tower_paths` table
- [x] Add `GET /tower-paths` endpoint returning all computed paths
- [x] Render paths as Leaflet polylines between tower markers (color-coded by path quality)
- [x] Add toggle to show/hide mesh path overlay independently from coverage layers
- [x] Recalculate affected paths when a tower is added or removed

## 15. Backend audit — API conventions, DRY, dead code

### API convention violations
- [x] `POST /predict` returns 200 — should return 201 Created (resource creation)
- [x] `POST /tower-paths` returns 200 — should return 202 Accepted (queues background work)
- [x] `PUT /matrix/config` accepts `dict[str, Any]` — should use a Pydantic model like all other mutation endpoints
- [x] `/simulations/{tower_id}/aggregate` collides with `/simulations/{sim_id}/result` — move aggregate to `/towers/{tower_id}/aggregate`

### DRY violations
- [x] `get_result` and `get_simulation_result` duplicate GeoTIFF-or-status streaming logic — extract shared helper
- [x] `delete_tower` and `delete_tower_path` duplicate delete-check-rowcount-404 pattern — extract helper
- [x] Background task error handling in `run_splat` and `run_matrix_simulations` duplicates try/update-db/except/update-error pattern — extract helper

### Dead code
- [x] `Splat.bucket_name` and `Splat.bucket_prefix` stored on instance but unused after terrain provider extraction — remove

### Pydantic response models & type safety (round 2)
- [x] `_run_simulation_task` uses lowercase `callable` — use `Callable` from `collections.abc`
- [x] `_get_tower_location` returns untyped `dict[str, Any]` — replace with `TowerLocation` Pydantic model
- [x] API responses built as inline dicts — add `PredictResponse`, `TowerResponse`, `TowerListResponse`, `SimulationResponse`, `SimulationListResponse`, `TowerPathResponse`, `TowerPathListResponse`, `DeleteResponse`, `TaskStatusResponse`, `AuthTokenResponse`, `AuthCheckResponse`
- [x] `get_matrix_config` / `set_matrix_config` use `dict[str, list[str]]` — use `MatrixConfigRequest` model
- [x] `_KNOWN_HARDWARE` / `_KNOWN_ANTENNAS` duplicate keys from `HARDWARE_RX_PARAMS` / `ANTENNA_RX_PARAMS` — derive from source data

### Cleanup (round 3)
- [x] Remove unused `ErrorResponse` from `responses.py`
- [x] `list_tower_paths` parses `json.loads()` 4× per row — parse once per params blob
- [x] Remove redundant `SrtmProvider.__init__` that only calls `super().__init__()`

### CLAUDE.md norm violations (round 4)
- [x] `db_connection()` missing return type annotation — add `Generator[sqlite3.Connection, None, None]`
- [x] `_deadzone_cache: dict[str, Any]` is untyped module-level mutable state — replace with typed `_DeadzoneCache` dataclass

### Consistent error handling (round 5)
- [x] Replace all `JSONResponse({"error": ...}, status_code=4xx/5xx)` with `HTTPException` — FastAPI's standard error mechanism
- [x] Remove now-unused `JSONResponse` import from `main.py`
- [x] Rename `TaskStatusResponse.task_id` → `.id` so it works for both tasks and simulations in shared helper

## 16. Mobile / responsive design

### Critical
- [x] Add responsive breakpoints to all form columns (`col-12 col-sm-6` instead of fixed `col-6`) across Transmitter, Receiver, Environment, Simulation, Display, ClientSelector components
- [x] Remove hardcoded `width: 38px; height: 31px` from color picker in Transmitter.vue — let Bootstrap handle sizing
- [x] Make colorbar image responsive in Display.vue (`max-width: 100%; height: auto` instead of fixed `width="256" height="30"`)

### Medium
- [x] Add responsive stacking to TowerList items — tower name + buttons wrap on narrow screens via `flex-wrap` + `gap-1`
- [x] Add mobile-specific row spacing via `@media (max-width: 575.98px)` rule in style.css
- [x] Increase antenna mismatch loss badge font size on mobile (`max(0.75rem, 12px)` floor)

### Minor
- [x] Prevent navbar brand text + buttons from overflowing on very narrow viewports — `text-truncate` on brand, `flex-shrink-0` on buttons, max-width constraint
- [x] Add mobile-specific CSS rules in style.css for offcanvas sidebar max-height and overflow on small screens

### Round 2 — Critical
- [x] Fix dropdown menus clipped inside offcanvas on mobile — `position: static` + no transform on mobile
- [x] Fix map hidden under fixed navbar — `margin-top: 56px` and `height: calc(100vh - 56px)`
- [x] Fix offcanvas covering entire map on phones — 60vh max-height with scroll

### Round 2 — Medium
- [x] Increase touch targets on TowerList eye/trash buttons — `py-1 px-2` with `min-width/min-height: 36px`
- [x] Fix MatrixConfig inline checkboxes overflow on mobile — `form-check-inline` becomes `display: block` on <576px
- [x] Improve deadzone stats text wrapping in Display.vue — `<br class="d-sm-none">` line breaks on mobile only

### Round 2 — Minor
- [x] Fix "Set with Map" popover placement on mobile — changed to `data-bs-placement="auto"`
- [x] Increase tower color circle size in TowerList — 10px → 12px
- [x] Fix suggestion marker popup width on small screens — `min-width: 200px` → `max-width: min(200px, 80vw)`
- [x] Add landscape-specific media query to reduce offcanvas height on landscape phones

### Round 3 — Medium
- [x] Remove hardcoded `<br />` in Environment.vue "Clutter Height" label — use natural text flow
- [x] Stack "Set with Map" / "Center map on transmitter" buttons vertically on mobile — `flex-column flex-sm-row`
- [x] Make "Run Simulation" button sticky at bottom of offcanvas — `sticky-bottom bg-dark`
- [x] Add `flex-shrink-0` to antenna mismatch loss badge to prevent compression on narrow widths

### Round 3 — Minor
- [x] Increase offcanvas close button touch target for mobile — added `p-3` padding

## 17. Backend–frontend integration gaps

### Critical bugs
- [x] ClientSelector uses wrong field names — fixed to use `client_hardware`, `client_antenna`, `terrain_model`, `id`
- [x] Tower deletion (`removeSite`) now calls `DELETE /towers/{tower_id}` before local removal
- [x] `GET /towers` called on page load via `loadTowers()` in `initMap` — persisted towers load for all users

### Feature gaps
- [x] MatrixConfig lists all 3 real terrain models (`bare_earth`, `dsm`, `lulc_clutter`)
- [x] ClientSelector has terrain model selector — visitors can switch between terrain modes
- [x] Failed simulation error message surfaced in UI alert below Run Simulation button
- [x] `GET /towers/{tower_id}/aggregate` called when visitor selects `weighted_aggregate` terrain

### Round 4 — Minor
- [x] Add `text-break` to simulation error alert to prevent horizontal overflow on narrow screens
- [x] Add `form-control-sm` to LoginForm password input for consistency and prevent iOS auto-zoom
- [x] Add `mb-2` to ClientSelector terrain row for consistent spacing with pending message visibility

## 18. CLAUDE.md norm violations — frontend

### `readonly` on immutable interfaces
- [x] Add `readonly` to all fields on server-response interfaces: AnalysisBounds, SiteSuggestion, DeadzoneRegion, DeadzoneAnalysis, SimProgress, TowerInfo, OverlapHatchLayerOptions. Site.params/taskId/color also readonly (raster/visible are mutable). TowerPath and GeoRaster already had readonly.

### DRY — duplicated label maps
- [x] Extract hardware/antenna/terrain label maps to shared `src/presets/labels.ts` with `labelsToOptions()` helper. Both ClientSelector.vue and MatrixConfig.vue now import from there.

### Single source of truth — inline types
- [x] Move inline `Simulation` interface to `SimulationRecord` in src/types.ts. Used by both ClientSelector.vue and store.ts loadTowers.

### Dead code
- [x] Remove commented-out `// center:` in store.ts initMap
- [x] Remove commented-out CSS block in App.vue `<style>`

### Type safety
- [x] Fix `setTxCoords` — wrap `.toFixed(6)` in `parseFloat()` so numbers reach the store

---

# Pre-Ship Issues (formerly TODO.SHIP.md)

## Critical

- [x] **Memory leak: orphaned Bootstrap Popover** — lazy-init popover, `dispose()` on unmount.
- [x] **Uncaptured timeout in simulation flow** — captured timer IDs, cleanup on unmount.
- [x] **No simulation poll timeout** — 5-minute max (300 polls), sets error state on timeout.

## High

- [x] **Unsafe double cast** — runtime shape validation before cast.
- [x] **Non-null assertions on `map` and `currentMarker`** — optional chaining and guard checks.
- [x] **`noImplicitAny: false`** — set to `true`, all code passes type-check.
- [x] **N+1 sequential fetches in ClientSelector** — `Promise.all()` for parallel execution.

## Medium

- [x] **Silent error swallowing** — errors surface to UI via `pendingMessage` and `simulationError`.
- [x] **Inline `onclick` in Leaflet popups** — replaced with `addEventListener` on `popupopen`.
- [x] **Custom window events for cross-component comm** — replaced with Pinia `_prefillCoords` state + `watch()`.
- [x] **Bootstrap form validation wired but inert** — `was-validated` applied on `@input` via form ref.

## Low

- [x] **Accessibility:** added `aria-label` to emoji-only buttons in TowerList.
- [x] **Hardcoded timeouts** — extracted to named constants (`POLL_INTERVAL_MS`, `PATH_RELOAD_DELAY_MS`, etc.).
- [x] **Hardcoded default coordinates** — changed from Calgary to Edmonton (53.5461, -113.4937).
- [x] **Array index as preset identifier** — presets now keyed by `name`/`code`/`label` strings.
- [x] **`chirpyMarker` unused export** — removed from `layers.ts` and associated tests.

---

# Pre-Ship Issues — Security & Reliability (formerly TODOS.SHIP.md)

## Critical

- [x] 1. Auth token comparison is not constant-time (`app/auth.py:65,92`) — use `hmac.compare_digest()`
- [x] 2. Auth token is the raw password echoed back (`app/auth.py:95`) — return opaque session token
- [x] 3. `ADMIN_PASSWORD` read once at import time (`app/auth.py:17`) — document or fix
- [x] 4. Rate limiter `_login_attempts` dict grows unbounded (`app/auth.py:20`) — add periodic cleanup
- [x] 5. Background tasks have no concurrency control (`app/main.py:316-327`) — add semaphore
- [x] 6. `_delete_row` interpolates table/column names into SQL (`app/main.py:105-108`) — validate against allowlist

## High

- [x] 7. No database migrations (`app/db/schema.py`) — add version tracking
- [x] 8. Deadzone cache invalidation is racy (`app/main.py:664`) — use content hash
- [ ] 9. GeoTIFF blobs in SQLite degrade perf at scale — move to filesystem (deferred: requires data migration)
- [x] 10. `splat_service` global singleton at import time (`app/main.py:66`) — lazy init in lifespan
- [x] 11. No timeout on SPLAT! subprocesses (`app/services/splat.py:211`) — add `timeout=`
- [x] 12. Exception messages leak internals to API callers (`app/main.py:495,675`) — generic messages

## Medium

- [x] 13. `request.high_resolution = False` mutates caller's model (`app/services/splat.py:122`) — copy first
- [x] 14. `_get_tower_location` silently defaults to 0,0 (`app/main.py:138-141`) — raise on missing
- [x] 15. No validation of `tower_ids` in `POST /tower-paths` (`app/main.py:554`) — verify existence
- [x] 16. `executescript` disables implicit transactions (`app/db/schema.py:94`) — use `execute()`
- [x] 17. `_login_attempts` dict not thread-safe (`app/auth.py:20`) — add lock
- [x] 18. Terrain provider warning has hardcoded direction (`app/services/terrain.py:242`) — fix format

## Low

- [ ] 19. `splat.py` is 1028 lines — extract GeoTIFF/color modules (deferred: refactor only)
- [x] 20. f-strings in `logger.debug(f"...")` evaluate eagerly — use lazy `%s` formatting
- [x] 21. Dead `null_value` parameter on `_create_splat_geotiff` (`app/services/splat.py:586`) — remove
- [x] 22. `compose.yml` 12GB memory limit undocumented — documented with rationale

---

## Round 2 — Pre-Ship Review (2026-03-15)

### Critical

- [x] 23. Auth silently disabled if `ADMIN_PASSWORD` unset (`app/main.py` lifespan) — add startup warning
- [x] 24. Race condition in `_DeadzoneCache` (`app/main.py`) — concurrent reads/writes with no lock
- [x] 25. Missing indexes on FK columns (`app/db/schema.py`) — full table scans on tower lookups

### High

- [x] 26. Rate limiter only prunes at 10K IPs (`app/auth.py`) — add TTL-based cleanup on every call
- [x] 27. Failed tower paths silently deleted (`app/main.py:298`) — mark failed instead of deleting
- [x] 28. KML parsing assumes `LatLonBox` exists (`app/services/splat.py:623`) — null check before access
- [x] 29. HGT tile reshape has no size validation (`app/services/terrain.py:212-214`) — validate before reshape

### Medium

- [x] 30. `Literal[tuple(AVAILABLE_COLORMAPS)]` evaluated at import time (`CoveragePredictionRequest.py`) — defer
- [x] 31. Deadzone scoring weights are magic numbers (`app/services/deadzone.py:284`) — extract to named constants
- [x] 32. Raw SQL throughout codebase — migrated to SQLAlchemy ORM
- [x] 33. No retry mechanism for failed simulations — added 2-attempt retry with 5s delay
- [x] 34. PPM image fully loaded into memory for large radius simulations — downsample >4000px

## Round 3 — Frontend Pre-Ship Review (2026-03-15)

### High

- [x] 35. Deadzone popup listener accumulates on every `popupopen` (`store.ts:315-320`) — use `{ once: true }`
- [x] 36. Simulation polling `setTimeout` not tracked or cancelable (`store.ts:675`) — store timer ID
- [x] 37. `saveTimeout` not cleared on unmount (`MatrixConfig.vue:100-129`) — add `onUnmounted` cleanup
- [x] 38. Map click listener orphaned if component unmounts before click (`Transmitter.vue:313`) — remove on unmount

### Medium

- [x] 39. Backend `suggestion.reason` interpolated unsanitized into Leaflet popup HTML (`store.ts:306`) — use safe DOM
- [x] 40. Popover init crashes on null element (`Transmitter.vue:348`) — add null guard

### Low

- [x] 41. Unnecessary `as L.Layer` type assertion (`store.ts:327`) — remove redundant cast

---

## E2E Integration Testing (Playwright)

- [ ] 42. Install Playwright, create `playwright.config.ts` with dual `webServer` (Vite + Uvicorn)
- [ ] 43. Create E2E test fixtures — DB seeding, auth helpers, shared utilities
- [ ] 44. Visitor flow test — app loads, `GET /towers` returns data, map renders
- [ ] 45. Admin auth flow test — login form → token → protected endpoints accessible, bad creds rejected
- [ ] 46. API integration tests — tower CRUD, tower-paths list, matrix config round-trip
- [ ] 47. Add `test:e2e` script to `package.json` and `test-e2e` CI job gated behind unit tests

---

## Round 4 — Frontend Deep Review (2026-03-15)

### Critical

- [x] 48. Map init coupled to `Transmitter.vue` — visitors never get a map since it's inside `v-if="store.isAdmin"` (`Transmitter.vue:368`)
- [x] 49. `v-model` on numeric inputs produces strings — no `.number` modifier, causes NaN in calculations (all form components)

### High

- [x] 50. HTML injection in tower path popups — backend values interpolated into HTML string (`store.ts:220`)
- [x] 51. HTML injection in deadzone suggestion icon — `priority_rank` interpolated into `L.divIcon({ html })` (`store.ts:281-294`)
- [x] 52. `overlay_transparency` slider is non-functional — value collected but never applied to rendering (`store.ts:89,491,531`)
- [x] 53. Tower color picker ignored — `runSimulation` always uses palette color, discards `tx_color` (`store.ts:674-680`)

### Medium

- [x] 54. `simulationState` is untyped string — no union type, typos compile silently (`store.ts:37`)
- [x] 55. `await randanimalSync()` — `await` on sync function is misleading (`store.ts:682`)
- [x] 56. `updateOverlapLayer` ↔ `redrawSites` redundant redraws — mutual calls cause double work (`store.ts:499-538`)
- [x] 57. `_prefillCoords` reactive store state used as one-shot event — fragile signaling pattern (`store.ts:53`)

### Low

- [x] 58. No error feedback to visitors on `loadTowers` failure — silent `console.warn` only (`store.ts:96-161`)
- [ ] 59. Reactive destructuring of store nested objects is fragile (deferred: safe in practice since splatParams is never replaced)
