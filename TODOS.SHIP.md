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
