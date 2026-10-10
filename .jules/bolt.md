## 2026-10-10 - Guard string formatting in logging statements
**Learning:** Python evaluates expressions in logging calls synchronously even if the target log level is disabled. Complex serialization routines like `json.dumps()` / `_dump_json()` passed to `_LOGGER.debug()` should be explicitly guarded with `if _LOGGER.isEnabledFor(logging.DEBUG):`.
**Action:** Always check for expensive argument formatting or serialization in hot-path `_LOGGER.debug()` calls and wrap them in `isEnabledFor` guards.
