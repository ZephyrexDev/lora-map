# Pre-Ship Issues

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
