# TODOS

## 1. Rebrand to generic LoRa

- [x] Rename repo/package from `meshtastic-site-planner` to `lora-planner` (package.json `name` field)
- [x] Replace "Meshtastic" with "LoRa" in all UI text, page titles, and meta tags
- [ ] Replace Meshtastic logos/favicons in `public/` with generic branding
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

- [ ] Add frontend tower list panel showing all persisted towers
- [ ] Add per-tower visibility toggle (checkbox or eye icon)
- [ ] Implement toggle via `setOpacity(0)` / `setOpacity(original)` — no layer remove/re-add
- [ ] On page load, fetch `GET /towers` and render all cached GeoTIFF layers
- [ ] Store per-tower visibility state in Pinia (not in the DOM)
- [ ] Add tower delete button (admin-only, calls `DELETE /towers/{id}`)

## 6. Admin/visitor auth

- [x] Define admin credential source (environment variable: `ADMIN_PASSWORD`, rate-limited login)
- [x] Add FastAPI auth dependency (Bearer token = static password)
- [x] Protect `POST /predict`, `DELETE /towers/{id}`, and any future mutation endpoints
- [x] Leave `GET /towers`, `GET /status`, `GET /result` public
- [ ] Add login UI for admin (minimal — just unlocks edit controls)
- [ ] Visitor mode: hide simulation form, show only map + tower list with toggles

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

Towers have fixed hardware/antenna/height configs set by admin. The matrix varies the **client (receiver)** side — showing "what coverage does a visitor with client hardware X and antenna Y see from this tower?"

- [ ] Define client simulation matrix: client hardware (V3, V4) × client antenna (4 options) = 8 receiver configurations per tower
- [ ] Matrix varies receiver gain, sensitivity, and SWR mismatch loss — tower TX params stay fixed
- [ ] Add backend endpoint or CLI command to batch-run matrix simulations for a given tower
- [ ] Store each matrix result as a separate GeoTIFF in SQLite, keyed by tower_id + client_hardware + client_antenna
- [ ] Add UI selector for visitors to pick their client hardware + antenna and instantly see the matching cached coverage layer
- [ ] On tower creation, auto-queue the full client matrix as background tasks
- [ ] Show matrix completion progress in admin UI

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

## 12. Meshcore tower path simulation

- [ ] Add SPLAT! point-to-point analysis function in `app/services/splat.py`
- [ ] Add `POST /tower-paths` endpoint that runs pairwise P2P between selected towers
- [ ] Store path results (path loss, LOS status) in SQLite `tower_paths` table
- [ ] Add `GET /tower-paths` endpoint returning all computed paths
- [ ] Render paths as Leaflet polylines between tower markers (color-coded by path quality)
- [ ] Add toggle to show/hide mesh path overlay independently from coverage layers
- [ ] Recalculate affected paths when a tower is added or removed
