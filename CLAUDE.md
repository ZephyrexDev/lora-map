# CLAUDE.md

## Project Overview

LoRa Coverage Planner — a full-stack radio coverage prediction tool using SPLAT! (ITM/Longley-Rice model). Admins configure tower sites with hardware presets, run coverage simulations, and build multi-tower mesh path visualizations. Visitors see cached results with toggleable coverage layers on an interactive Leaflet map.

## Active Goals

1. **Meshcore tower path simulation:** Visualize inter-tower mesh paths (line-of-sight links, path loss) to form a tower web overlay. Requires pairwise SPLAT! point-to-point analysis between tower sites. **In progress.**
2. **Deadzone remediation:** Identify and visualize gaps in coverage to guide new tower placement. **In progress.**

## Architecture

```
src/                  → Vue 3 + TypeScript frontend (Pinia store, Leaflet map, Bootstrap UI)
  components/         → Vue components (Transmitter, Receiver, TowerList, LoginForm, etc.)
  presets/            → Hardware/antenna/frequency/height preset data (presets.json + typed wrappers)
  layers/             → Custom Leaflet layers (OverlapHatchLayer)
app/                  → FastAPI backend
  main.py             → API endpoints + static file serving
  auth.py             → Bearer-token admin auth with rate limiting
  colors.py           → 24-color tower palette assignment
  matrix.py           → Client simulation matrix config and combinations
  services/           → SPLAT! wrapper + terrain data providers
  models/             → Pydantic request/response models
  db/                 → SQLite schema, connection factory
  ui/                 → Build output (frontend assets, gitignored)
splat/                → Git submodule — SPLAT! C source
public/               → Static assets (colormaps)
tests/                → pytest backend tests
Containerfile         → Single-container podman build
compose.yml           → Optional podman-compose for dev convenience
```

**Data flow:** Vue form → Pinia store → POST /predict (admin-authed) → background task runs SPLAT! → tower config + GeoTIFF result persisted in SQLite → frontend polls /status, fetches /result GeoTIFF → parsed with georaster → rendered as independent GeoRasterLayer on Leaflet. Visitors hit GET /towers → load all persisted layers directly from SQLite — no simulation round-trip.

## Tech Stack

- **Frontend:** Vue 3.5, TypeScript 5.9, Pinia, Leaflet 1.9, Bootstrap 5, Vite 7
- **Backend:** Python 3.11, FastAPI, Pydantic 2, Uvicorn
- **Storage:** SQLite (tower data, simulation results, GeoTIFF blobs)
- **Data/Geo:** Rasterio, GDAL, NumPy, Matplotlib, Haversine, Boto3 (AWS S3 terrain tiles)
- **Infra:** Podman (single container), sits behind an external HTTPS-terminating reverse proxy
- **Testing:** Vitest (frontend), pytest (backend), GitHub Actions CI
- **Linting/Formatting:** Black + Ruff (Python), ESLint + Prettier (TypeScript/Vue)
- **Package manager:** pnpm (frontend), uv (backend)

## Commands

```bash
# Frontend
pnpm install              # Install JS dependencies
pnpm run dev              # Vite dev server
pnpm run build            # Type-check + build + copy to app/ui

# Backend
uv sync                   # Install Python dependencies from pyproject.toml
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080

# Testing
pnpm run test             # Frontend tests (Vitest)
uv run pytest             # Fast unit tests only (default)
uv run pytest --run-slow  # All tests including SPLAT! integration

# Linting & Formatting
uv run black app/ tests/  # Format Python (line length 120)
uv run ruff check app/ tests/  # Lint Python
pnpm run lint             # ESLint + Prettier (TypeScript/Vue)
pnpm run format           # Prettier format only

# Container
podman build -f Containerfile -t lora-planner .
podman run -p 8080:8080 -v lora-data:/data lora-planner
podman-compose up         # Dev convenience (optional)
```

## Code Standards

### Python

- Target Python 3.11. Use modern syntax: `match`, `|` union types, f-strings.
- Use type hints on all function signatures. Use Pydantic models for API boundaries.
- Follow PEP 8 strictly. All code must be formatted with **Black** (line length 120). Lint with **Ruff** (`ruff check`).
- Use snake_case for functions, variables, and modules. Use PascalCase for classes.
- **Favor object-oriented design.** Group related state and behavior into classes. Use inheritance and composition to share logic — prefer composition when the relationship is "has-a", inheritance when "is-a". Avoid loose collections of module-level functions when a class would reduce parameter passing and improve cohesion.
- **Minimize code volume.** Consolidate duplicate logic into shared base classes, mixins, or utility methods. If two pieces of code do similar things, refactor them behind a common abstraction. Shorter is better when clarity is preserved.
- Avoid mutable default arguments. Prefer `None` with internal initialization.
- Use `logging` (module-level `logger = logging.getLogger(__name__)`) — never `print()` in backend code. Use lazy `%s` formatting (`logger.info("msg %s", val)`) — never f-strings in logger calls (they evaluate eagerly even when the level is disabled).
- Handle exceptions at the appropriate level. Don't catch broad `Exception` unless re-raising or storing the error (as in the task runner pattern). Never leak internal exception messages to API callers — return generic messages and log the details server-side.
- Prefer `pathlib.Path` over `os.path` for file operations.
- Never interpolate table or column names into SQL. Use parameterized queries for values; validate identifiers against an allowlist if dynamic SQL is unavoidable.
- Use `hmac.compare_digest` for any security-sensitive string comparison (tokens, passwords). Never use `==` or `!=` for secrets.
- Avoid module-level side effects that depend on environment variables or external state. Prefer lazy initialization (e.g., in FastAPI lifespan) so the app can start and report useful errors.
- Always pass `timeout=` to `subprocess.run` calls. No subprocess should be able to hang indefinitely.

### TypeScript / Vue

- Use TypeScript strict mode. All exports must be typed — no `any` except where third-party types are missing (e.g., georaster).
- Lint with **ESLint** (`eslint .`) using `@typescript-eslint` and `eslint-plugin-vue`. Format with **Prettier**. ESLint runs with type-aware rules via `parserOptions.project`.
- Follow modern TypeScript idioms: discriminated unions over type assertions, `satisfies` for safe narrowing, `readonly` where mutation isn't needed, `as const` for literal types.
- Define shared interfaces in `src/types.ts`. Keep the single source of truth for data shapes.
- **Favor object-oriented design and class-based abstractions.** Use classes for stateful services, models, and anything with lifecycle. Use interfaces and generics to define contracts. Prefer composition via injected dependencies over standalone functions with implicit coupling.
- **Minimize code volume.** Extract shared logic into base classes, generic utilities, or composables. Consolidate repeated patterns — two near-identical blocks should become one parameterized abstraction.
- Use Vue 3 Composition API for new components. Existing Options API code does not need to be rewritten unless being significantly modified.
- Use Pinia for shared state. Components should not hold state that other components need. Use Pinia actions or reactive state for cross-component communication — never `window.dispatchEvent` / `CustomEvent`.
- Prefer `const` over `let`. Never use `var`.
- Use template literals over string concatenation.
- Never use `console.log` in committed code. Use `console.warn` or `console.error` for diagnostics.
- **No inline HTML event handlers.** Never use `onclick`, `onload`, or similar attributes in dynamically constructed HTML (e.g., Leaflet popups, template literals). Use `addEventListener` after DOM insertion instead.
- **No magic numbers.** Extract timeouts, poll intervals, zoom levels, and other numeric constants to named `const` declarations at the top of the file.
- **Preset dropdowns keyed by stable identifiers.** Use `name`, `code`, or `label` as `<option>` values — never array indices, which break when order changes.
- **Clean up lifecycle resources.** Capture all timer IDs from `setTimeout`/`setInterval` and clear them in `onUnmounted`. Dispose Bootstrap instances (Popover, Tooltip, Modal) in `onUnmounted`. Never leave dangling event listeners or orphaned timers.
- **Handle every promise.** Every `async` call must be `await`ed, `.catch()`-ed, or explicitly marked `void`. Unhandled rejections silently swallow errors.

### General

- **DRY aggressively.** Extract repeated logic into shared abstractions as soon as a pattern appears twice. Prefer a single parameterized implementation over two similar blocks. Actively look for opportunities to reduce total lines of code through consolidation.
- **No dead code.** Remove commented-out imports, unused variables, and stale comments. Don't leave `// TODO` markers without a linked issue.
- **Naming:** Names should describe *what* something is or does, not *how*. Prefer `terrain_tile_cache` over `dc` or `cache1`.
- **No secrets in code.** AWS credentials, API keys, and admin credentials must come from environment variables — never hardcoded. Auth tokens returned to clients must be opaque (random); never echo raw passwords or secrets back.
- **Commits:** Write concise commit messages focused on *why*, not *what*. One logical change per commit.
- **Schema changes require migrations.** Never rely on `CREATE TABLE IF NOT EXISTS` alone. Add a new versioned entry in `app/db/schema.py:MIGRATIONS` so existing databases get updated. The `schema_version` table tracks what's been applied.
- **Don't suppress linter warnings** (`# noqa`, `// eslint-disable`) without first trying to fix the root cause. Suppression is a last resort, not a shortcut.
- **No HTTPS in app.** The app serves HTTP only on port 8080. TLS termination is handled by the external reverse proxy. Do not add SSL config, certificate handling, or HTTPS redirects.
- **No CORS.** The reverse proxy serves both the API and static frontend on the same origin. Do not add CORS middleware.

### Layer Management

- Each tower site owns its own GeoRasterLayer instance. Toggling visibility uses `layer.setOpacity(0)` / `layer.setOpacity(original)` or Leaflet layer control — never remove/re-add, which triggers re-renders.
- Tower data and simulation results are stored in SQLite on a persistent volume (`/data`).
- The Pinia store tracks per-tower visibility state independently from raster data.

### Hardware Presets

- Define hardware specs (power, gain, supported frequencies) as static data — not inline in components. A single source file (e.g., `src/presets/hardware.ts` and/or `app/presets/`) shared between validation and UI.
- Frequency options are keyed by country/region code. Height presets map human-readable labels to meter values.
- "Custom" mode unlocks all fields for manual entry. Preset mode locks auto-filled fields in the UI but still sends raw values to the API — the backend is preset-agnostic.

## File Conventions

- Python model files use PascalCase filenames matching the class name (e.g., `CoveragePredictionRequest.py`).
- Vue components use PascalCase filenames (e.g., `Transmitter.vue`).
- TypeScript utility files use camelCase (e.g., `utils.ts`, `layers.ts`).
- Built frontend assets go in `app/ui/` — this directory is gitignored and regenerated by `pnpm run build`.
- Container files: `Containerfile` (not Dockerfile), `compose.yml` (not docker-compose.yml).
- SQLite database and terrain tile cache live under `/data` inside the container (bind-mounted persistent volume).

## Deployment

- Single container exposes HTTP on port 8080. An external reverse proxy handles HTTPS termination and routing.
- `podman run -p 8080:8080 -v lora-data:/data lora-planner` is the canonical production invocation.
- SPLAT! binary is compiled from source during container build with `-march=native`.
- Terrain tiles are streamed from AWS S3 (`elevation-tiles-prod`) and cached locally via diskcache under `/data`.
- SQLite database at `/data/lora-planner.db` stores tower configs, simulation metadata, and GeoTIFF blobs.
- Admin auth is enforced at the API layer (FastAPI dependency), not just hidden in the UI.
