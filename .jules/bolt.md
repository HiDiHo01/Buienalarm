# Bolt's Performance Journal
Critical learnings on performance optimizations for this repository.

## Optimization guidelines: performance without behavior regressions

- **Measure before and after.** Benchmark the same implementation path with the same representative forecast inputs (dry, upcoming rain, active rain and mixed/invalid bins). Record the Python version, platform, number of iterations, warm-up strategy, elapsed time and variability. Isolate CPU processing from API/network and Home Assistant startup overhead. Report historical speedups as measurements from their original context, not guaranteed improvements on every system.
- **Optimize proven hot paths.** Prefer numeric epoch comparisons for five-minute interval filtering, single-pass scans, and avoiding repeated formatting, serialization or `datetime` construction. Do not introduce complexity for an unmeasured or cold path. Guard expensive DEBUG argument preparation when logging is disabled.
- **Keep generic input support.** Fast-path exact built-in `dict`, `int` and `float` values only when the API contract permits it; retain validated fallbacks for supported `Mapping` implementations and string values. Reject boolean and non-finite timestamps; handle overflow and platform-dependent `datetime.fromtimestamp()` failures without modifying previously valid rain boundaries.
- **Preserve precipitation semantics.** A five-minute bin is active for `ts <= now_ts < ts + 300`. Leading dry bins need no UTC `datetime` object; the first dry bin *after* rain starts still determines the event endpoint. Retain the same timezone-aware UTC endpoints, whole-minute rounding, duration limit, availability and invalid-data behavior as before optimization. Do not turn indeterminate source data into a plausible zero or confirmed `off`.
- **Prove parity with regressions.** Test all-dry, dry-to-wet-to-dry, active bins, rain extending to the forecast end, `dict` and `UserDict` inputs, comma-decimal rates, malformed/boolean/non-finite/out-of-range timestamps and conversion failures. Assert exact sensor values and availability. Where skipping work is the optimization itself, also assert that leading dry bins do not call `datetime.fromtimestamp()`.
- **Verify before reporting.** Run the focused tests and relevant repository CI checks (including Ruff and Home Assistant compatibility); inspect the complete diff for accidental API or entity changes. Distinguish independently reproduced benchmarks, historical reported measurements and passing correctness tests.

**Evidence from [PR #214](https://github.com/HiDiHo01/Buienalarm/pull/214):** Its description reported approximately 1.17 s → 0.44 s for 25,000 dry-forecast scans and 0.60 s → 0.42 s for 25,000 wet-forecast scans on 25-bin payloads. These are **historical benchmark claims**, not measurements reproduced during this documentation update. The rebased PR's CI completed with **679 passed, 1 skipped**; that validates tested behavior, not the claimed speedup.

## 2026-10-10 - Guard string formatting in logging statements
**Learning:** Python evaluates expressions in logging calls synchronously even if the target log level is disabled. Complex serialization routines like `json.dumps()` / `_dump_json()` passed to `_LOGGER.debug()` should be explicitly guarded with `if _LOGGER.isEnabledFor(logging.DEBUG):`.
**Action:** Always check for expensive argument formatting or serialization in hot-path `_LOGGER.debug()` calls and wrap them in `isEnabledFor` guards.

## 2026-05-18 - Avoid datetime object creation in hot data loops
**Learning:** In Home Assistant integrations processing timeseries data (such as Buienalarm's 5-minute precipitation forecast bins), converting epoch timestamps to `datetime` objects inside loops for time comparison operations (like checking if `timestamp < current_time < timestamp + 300`) incurs significant CPU overhead (up to ~6.5x slower). Comparing numeric epoch floats/ints directly bypasses Python datetime object construction, timezone resolution, and timedelta arithmetic.
**Action:** Always compare numeric epoch timestamps (`ts <= now_ts < ts + 300`) in data processing loops, and only convert to `datetime` objects when formatting strings or returning actual `datetime` instances.

## 2026-05-05 - Avoid Duplicate Formatting in Home Assistant State Evaluation
**Learning:** Computing Home Assistant sensor states using methods that format rich attribute objects (e.g. `get_precipitation_periods_as_dict()`) causes duplicate timestamp parsing and ISO string serialization overhead when evaluating condition checks or counts.
**Action:** When evaluating numerical properties or counts for sensors, query raw internal lists or counts directly (e.g. `len(self._get_precipitation_periods())`) rather than invoking attribute formatting helpers that build complex dictionaries.

## 2026-10-19 - Avoid bound method allocation in generic mapping getter helpers
**Learning:** Generic dictionary getter functions like `_safe_get()` that use `getattr(item, "get")` to extract keys dynamically instantiate bound method objects (`PyMethod_New`) on every call. In hot loops processing timeseries data points, checking `isinstance(item, dict)` first and invoking `item.get(key, default)` directly avoids method object allocations and speeds up key lookups by 4x (~75% reduction in lookup latency), reducing overall entity state attribute evaluation time by ~31%.
**Action:** Always provide an explicit `if isinstance(item, dict): return item.get(key, default)` fast path in dynamic dictionary lookup helpers before falling back to `getattr`.

## 2026-10-21 - Aggregate timeseries data in a single pass
**Learning:** Filtering timeseries forecast points into an intermediate list before iterating over that list to aggregate values causes unnecessary object allocations and double array traversals. Combining time-window filtering and rate summation into a single pass direct loop yields a ~1.81x speedup (~45% reduction in calculation latency).
**Action:** Perform filtering and aggregation in a single loop pass when processing timeseries forecast arrays.

## 2026-10-22 - Fast-path exact type checks in numeric conversion helpers
**Learning:** `isinstance(val, (int, float))` requires traversing Python's MRO inheritance tree (and checking if `val` is `bool`, since `bool` subclasses `int` in Python). Checking `type(val) is float` and `type(val) is int` directly in helper functions like `_as_float()` bypasses MRO checks, speeding up float/int parsing by ~1.48x and reducing binary sensor state update latency by ~30% when combined with single-pass validation.
**Action:** Use exact `type(v) is float` / `type(v) is int` fast-paths in type casting helper functions when processing large timeseries forecast arrays.

## 2026-10-23 - Validate forecast points and compute timestamp bounds in a single pass
**Learning:** Redundantly converting numeric epoch timestamps float -> datetime -> float inside sensor icon checks (`datetime.fromtimestamp(...).timestamp()`) and using double list traversals (`all(...)` followed by `for point in forecast`) creates unnecessary `datetime` object instantiations and list allocations. Validating points and updating min/max timestamp floats directly in a single pass reduces execution latency by ~63% (~2.71x speedup).
**Action:** Always validate timeseries entries and compute minimum/maximum timestamp bounds in a single pass using direct float comparisons (`0 <= ts <= 253402300799`).

## 2026-10-24 - Validate datetime conversion before updating rain boundaries
**Learning:** Numeric epoch bounds do not guarantee that `datetime.fromtimestamp(...)` succeeds on every platform. Deferring conversion until after rain boundaries have been updated lets unsupported points erase a valid rain start or inflate the duration. Numeric float subtraction can also change whole-minute rounding compared with subtraction of converted datetimes.
**Action:** Keep numeric filtering and parsing fast paths, but convert each accepted timestamp before changing any rain boundary. Skip conversion failures, reuse the validated UTC datetime, and calculate duration from datetime endpoints to preserve rounding.

## 2026-10-25 - Fast-path exact dict type checks in active forecast point resolution
**Learning:** In `BuienalarmEntity._get_current_data_point()`, candidate timeseries points were routed through `isinstance(data_point, Mapping)` and `_safe_get()`. Because active readings are queried repeatedly across multiple sensor entities (`precipitationrate_now`, `precipitationrate_now_desc`, `precipitationtype_now`), checking `type(data_point) is dict` directly and extracting `data_point.get()` bypasses ABC virtual subclass inheritance resolution and nested getter dispatch overhead, resulting in a ~1.75x speedup (~43% reduction in resolution latency) when finding active forecast points.
**Action:** Provide an exact `type(item) is dict` fast path in forecast-point scanning methods before falling back to generic `Mapping` abstractions.

## 2026-11-05 - Single-pass binary sensor state and availability evaluation
**Learning:** In `BuienalarmBinarySensor._update_state()`, evaluating availability and state for each binary sensor (`precipitation_expected`, `currently_raining`, `currently_snowing`) previously ran up to 3 separate `any(...)` generator expressions over the forecast timeseries. Each generator pass repeatedly performed timestamp extraction, floating-point conversion, and precipitation-type validation. Consolidating the unexpired/active interval checks, classification validation, and state detection into a single-pass loop reduces generator dispatch and redundant dictionary lookups, achieving a ~4.3x speedup (~77% reduction in update latency) for active bin evaluation.
**Action:** Evaluate availability, classification validity, and binary sensor state in a single pass over timeseries forecast periods.

## 2026-11-10 - Fast-path exact dict lookups in precipitation duration calculation
**Learning:** In `BuienalarmEntity.get_precipitation_duration()`, iterating through forecast entries using `isinstance(entry, Mapping)` and dynamic `_safe_get()` repeatedly incurred ABC inheritance checks and method object allocations. Providing an exact `type(entry) is dict` fast path along with direct float/int type checks yields a ~1.44x speedup (~30.4% reduction in execution latency) for dry forecast scans and ~1.41x speedup (~28.9% reduction) during active event calculations.
**Action:** Fast-path exact `type(entry) is dict` and exact float/int conversions in timeseries scanning loops before falling back to generic `Mapping` getters.

## 2026-11-13 - Defer datetime creation for leading dry forecast bins
**Learning:** When dry forecast bins precede rain, their timestamps need validation but do not need conversion into UTC datetime objects. After precipitation starts, the first dry bin still establishes the event end time.
**Action:** Validate input timestamps and precipitation rates before creating datetime objects, and cover both dictionary and mapping-like inputs with deterministic duration regressions.

