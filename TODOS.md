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
- [ ] Update Containerfile to not install/configure Redis
- [ ] Add `/data` volume mount for SQLite + terrain cache
- [x] Replace all `docker` references in code/comments with `podman` (N/A — no docker refs outside renamed files)
- [ ] Test `podman build` and `podman run` workflow end-to-end

## 3. Replace Redis with SQLite

- [x] Add SQLite schema: `towers` table (id, name, params JSON, geotiff BLOB, created_at, updated_at)
- [x] Add SQLite schema: `tasks` table (id, tower_id, status, error, created_at)
- [x] Create `app/db/` module with schema init and access functions
- [ ] Rewrite `run_splat` to persist results to SQLite instead of Redis
- [ ] Rewrite `/predict` to create task row in SQLite
- [ ] Rewrite `/status/{task_id}` to read from SQLite
- [ ] Rewrite `/result/{task_id}` to stream GeoTIFF from SQLite
- [ ] Add `GET /towers` endpoint to list all towers with metadata (no blobs)
- [ ] Add `DELETE /towers/{id}` endpoint (admin-only)
- [x] Remove `redis` from `requirements.txt`
- [x] Remove Redis client initialization from `main.py`

## 4. Drop CORS and HTTPS

- [x] Remove `CORSMiddleware` from `main.py`
- [x] Remove CORS-related imports and comments
- [ ] Ensure static files still served via `StaticFiles` mount on `/`
- [ ] Verify API and UI work on same origin behind reverse proxy

## 5. Persistent towers & toggleable layers

- [ ] Add frontend tower list panel showing all persisted towers
- [ ] Add per-tower visibility toggle (checkbox or eye icon)
- [ ] Implement toggle via `setOpacity(0)` / `setOpacity(original)` — no layer remove/re-add
- [ ] On page load, fetch `GET /towers` and render all cached GeoTIFF layers
- [ ] Store per-tower visibility state in Pinia (not in the DOM)
- [ ] Add tower delete button (admin-only, calls `DELETE /towers/{id}`)

## 6. Admin/visitor auth

- [ ] Define admin credential source (environment variable: `ADMIN_PASSWORD` or similar)
- [ ] Add FastAPI auth dependency (e.g., HTTP Basic or token-based)
- [ ] Protect `POST /predict`, `DELETE /towers/{id}`, and any future mutation endpoints
- [ ] Leave `GET /towers`, `GET /status`, `GET /result` public
- [ ] Add login UI for admin (minimal — just unlocks edit controls)
- [ ] Visitor mode: hide simulation form, show only map + tower list with toggles

## 7. Hardware & environment presets

- [x] Create `src/presets/hardware.ts` with Heltec V3 (max 22 dBm / 158 mW, SX1262), Heltec V4 (max 22 dBm / 158 mW, SX1262), custom (all fields unlocked)
- [x] Create `src/presets/frequencies.ts` keyed by country code (Canada 907 MHz, US 915 MHz, EU 868 MHz, etc.)
- [x] Create `src/presets/antennas.ts` with curated antenna list (name, gain dBi, SWR): Ribbed Spring Helical (0 dBi, 3.0), Duck Stubby (1 dBi, 3.5), Bingfu Whip (2.5 dBi, 1.8), Slinkdsco Omni (4 dBi, 1.1)
- [ ] Calculate SWR mismatch loss: `loss_dB = -10 * log10(1 - ((SWR-1)/(SWR+1))²)` and subtract from TX power before sending to SPLAT!
- [ ] Add SWR mismatch loss calculation to backend `app/services/splat.py` (apply to effective TX power)
- [ ] Display computed mismatch loss in UI next to antenna selector (informational)
- [x] Create `src/presets/heights.ts` mapping labels to meters (ground: 1m, first floor window: 3m, second floor window: 6m, gutter line: 8m, rooftop: 10m, ground tower: 30m, roof tower: 15m)
- [ ] Add hardware selector dropdown to transmitter form
- [ ] Add country/region selector that auto-fills frequency
- [ ] Add antenna selector dropdown
- [ ] Add height preset dropdown (with manual override)
- [ ] Lock auto-filled fields in preset mode, unlock all in custom mode

## 8. Pre-cached client simulation matrix

Towers have fixed hardware/antenna/height configs set by admin. The matrix varies the **client (receiver)** side — showing "what coverage does a visitor with client hardware X and antenna Y see from this tower?"

- [ ] Define client simulation matrix: client hardware (V3, V4) × client antenna (4 options) = 8 receiver configurations per tower
- [ ] Matrix varies receiver gain, sensitivity, and SWR mismatch loss — tower TX params stay fixed
- [ ] Add backend endpoint or CLI command to batch-run matrix simulations for a given tower
- [ ] Store each matrix result as a separate GeoTIFF in SQLite, keyed by tower_id + client_hardware + client_antenna
- [ ] Add UI selector for visitors to pick their client hardware + antenna and instantly see the matching cached coverage layer
- [ ] On tower creation, auto-queue the full client matrix as background tasks
- [ ] Show matrix completion progress in admin UI

## 9. Meshcore tower path simulation

- [ ] Add SPLAT! point-to-point analysis function in `app/services/splat.py`
- [ ] Add `POST /tower-paths` endpoint that runs pairwise P2P between selected towers
- [ ] Store path results (path loss, LOS status) in SQLite `tower_paths` table
- [ ] Add `GET /tower-paths` endpoint returning all computed paths
- [ ] Render paths as Leaflet polylines between tower markers (color-coded by path quality)
- [ ] Add toggle to show/hide mesh path overlay independently from coverage layers
- [ ] Recalculate affected paths when a tower is added or removed
