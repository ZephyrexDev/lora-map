# Pre-Ship Issues

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
- [ ] 22. `compose.yml` 12GB memory limit undocumented — add to deployment docs (deferred: docs only)

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
- [ ] 33. No retry mechanism for failed simulations — user must re-POST (deferred: acceptable for MVP)
- [ ] 34. PPM image fully loaded into memory for large radius simulations (deferred: rare edge case)

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
