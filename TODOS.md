# TODOS

## 1. Rebrand to generic LoRa

- [x] Rename repo/package from `meshtastic-site-planner` to `lora-planner` (package.json `name` field)
- [ ] Replace "Meshtastic" with "LoRa" in all UI text, page titles, and meta tags
- [ ] Replace Meshtastic logos/favicons in `public/` with generic branding
- [x] Update `index.html` title and meta
- [x] Remove `site.meshtastic.org` references from CORS config, comments, and deployment docs
- [ ] Rename `randanimal` site names if they reference Meshtastic concepts
- [ ] Update README.md

## 2. Podman + single-container migration

- [ ] Rename `Dockerfile` → `Containerfile`
- [ ] Remove nginx-proxy and acme-companion services from compose
- [ ] Remove Redis service from compose
- [ ] Rename `docker-compose.yml` → `compose.yml` with single `app` service + persistent volume
- [ ] Update Containerfile to not install/configure Redis
- [ ] Add `/data` volume mount for SQLite + terrain cache
- [ ] Replace all `docker` references in code/comments with `podman`
- [ ] Test `podman build` and `podman run` workflow end-to-end

## 3. Replace Redis with SQLite

- [ ] Add SQLite schema: `towers` table (id, name, params JSON, geotiff BLOB, created_at, updated_at)
- [ ] Add SQLite schema: `tasks` table (id, tower_id, status, error, created_at)
- [ ] Create `app/db/` module with schema init and access functions
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

- [ ] Create `src/presets/hardware.ts` with Heltec V3, Heltec V4, custom specs (power, gain)
- [ ] Create `src/presets/frequencies.ts` keyed by country code (Canada 907 MHz, US 915 MHz, EU 868 MHz, etc.)
- [ ] Create `src/presets/antennas.ts` with curated antenna gain list
- [ ] Create `src/presets/heights.ts` mapping labels to meters (ground: 1m, first floor window: 3m, second floor window: 6m, gutter line: 8m, rooftop: 10m, ground tower: 30m, roof tower: 15m)
- [ ] Add hardware selector dropdown to transmitter form
- [ ] Add country/region selector that auto-fills frequency
- [ ] Add antenna selector dropdown
- [ ] Add height preset dropdown (with manual override)
- [ ] Lock auto-filled fields in preset mode, unlock all in custom mode

## 8. Meshcore tower path simulation

- [ ] Add SPLAT! point-to-point analysis function in `app/services/splat.py`
- [ ] Add `POST /tower-paths` endpoint that runs pairwise P2P between selected towers
- [ ] Store path results (path loss, LOS status) in SQLite `tower_paths` table
- [ ] Add `GET /tower-paths` endpoint returning all computed paths
- [ ] Render paths as Leaflet polylines between tower markers (color-coded by path quality)
- [ ] Add toggle to show/hide mesh path overlay independently from coverage layers
- [ ] Recalculate affected paths when a tower is added or removed
