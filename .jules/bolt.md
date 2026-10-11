## 2026-10-10 - Guard string formatting in logging statements
**Learning:** Python evaluates expressions in logging calls synchronously even if the target log level is disabled. Complex serialization routines like `json.dumps()` / `_dump_json()` passed to `_LOGGER.debug()` should be explicitly guarded with `if _LOGGER.isEnabledFor(logging.DEBUG):`.
**Action:** Always check for expensive argument formatting or serialization in hot-path `_LOGGER.debug()` calls and wrap them in `isEnabledFor` guards.
# Bolt's Performance Journal

Critical learnings on performance optimizations for this repository.
## 2026-05-05 - Avoid Duplicate Formatting in Home Assistant State Evaluation
**Learning:** Computing Home Assistant sensor states using methods that format rich attribute objects (e.g. `get_precipitation_periods_as_dict()`) causes duplicate timestamp parsing and ISO string serialization overhead when evaluating condition checks or counts.
**Action:** When evaluating numerical properties or counts for sensors, query raw internal lists or counts directly (e.g. `len(self._get_precipitation_periods())`) rather than invoking attribute formatting helpers that build complex dictionaries.
