## 2026-10-10 - Guard string formatting in logging statements
**Learning:** Python evaluates expressions in logging calls synchronously even if the target log level is disabled. Complex serialization routines like `json.dumps()` / `_dump_json()` passed to `_LOGGER.debug()` should be explicitly guarded with `if _LOGGER.isEnabledFor(logging.DEBUG):`.
**Action:** Always check for expensive argument formatting or serialization in hot-path `_LOGGER.debug()` calls and wrap them in `isEnabledFor` guards.
# Bolt's Performance Journal


## 2026-05-18 - Avoid datetime object creation in hot data loops
**Learning:** In Home Assistant integrations processing timeseries data (such as Buienalarm's 5-minute precipitation forecast bins), converting epoch timestamps to `datetime` objects inside loops for time comparison operations (like checking if `timestamp < current_time < timestamp + 300`) incurs significant CPU overhead (up to ~6.5x slower). Comparing numeric epoch floats/ints directly bypasses Python datetime object construction, timezone resolution, and timedelta arithmetic.
**Action:** Always compare numeric epoch timestamps (`ts <= now_ts < ts + 300`) in data processing loops, and only convert to `datetime` objects when formatting strings or returning actual `datetime` instances.


Critical learnings on performance optimizations for this repository.
## 2026-05-05 - Avoid Duplicate Formatting in Home Assistant State Evaluation
**Learning:** Computing Home Assistant sensor states using methods that format rich attribute objects (e.g. `get_precipitation_periods_as_dict()`) causes duplicate timestamp parsing and ISO string serialization overhead when evaluating condition checks or counts.
**Action:** When evaluating numerical properties or counts for sensors, query raw internal lists or counts directly (e.g. `len(self._get_precipitation_periods())`) rather than invoking attribute formatting helpers that build complex dictionaries.
