# Home Assistant Integration Guidance — Buienalarm

## Purpose

These instructions are specific to the Buienalarm custom integration in this repository. Apply them together with the root `AGENTS.md`, the integration manifest, current Home Assistant developer documentation, and existing tests.

Deliver the single best, minimal, production-quality change. Preserve established behavior unless a verified defect requires a correction. Do not make unrelated refactors or claim that live weather data has been validated when only static code or mocked tests were inspected.

## Project context

- Integration domain: `buienalarm`.
- Integration package: `custom_components/buienalarm/`.
- Platforms: `sensor` and `binary_sensor`.
- Configuration: config flow using latitude and longitude, with location metadata and options such as refresh interval and notification threshold.
- Data source: Buienalarm/Infoplaza nowcast time-series endpoint, currently configured in `const.py`.
- Architecture: asynchronous API client, `DataUpdateCoordinator`, config-entry setup/unload, coordinator-backed entities.
- Current repository metadata declares Home Assistant `>=2026.1` and Python `>=3.14.2,<3.15` in `pyproject.toml`. Verify the current supported Home Assistant/Python versions and APIs before changing compatibility metadata.
- The coordinator payload currently wraps the endpoint response in a mapping containing `timeseries`, `retrieval_time`, and `cache_age`. Trace the actual payload through the client, coordinator, and entity accessors before changing field paths.

## Required inspection before editing

1. Read `AGENTS.md` and these Buienalarm-specific instructions.
2. Inspect `custom_components/buienalarm/manifest.json`, `const.py`, `config_flow.py`, `__init__.py`, `api.py`, `coordinator.py`, `entity.py`, `sensor.py`, `sensor_types.py`, `binary_sensor.py`, translations, tests, and relevant CI workflows as applicable.
3. Trace each affected entity's source field from the API response through parsing and transformation to its Home Assistant state.
4. Inspect current Home Assistant documentation and source for any API whose signature, behavior, deprecation, or lifecycle requirements matter to the change.
5. Check existing entity IDs and unique IDs before changing descriptions or naming. Avoid registry churn and duplicate entities.

Do not assume that a declared description is actually instantiated, that a sensor key exists in the API payload, or that an API field has the meaning suggested by its name. Confirm these details in the active code path and representative fixtures.

## API client and coordinator

- Keep all network I/O asynchronous. Reuse Home Assistant's shared `aiohttp` client session through `async_get_clientsession(hass)`; do not introduce `requests`, synchronous HTTP calls, or a separately owned session without a demonstrated requirement.
- Apply bounded request timeouts and handle HTTP errors, connection failures, timeouts, invalid JSON, and malformed response structures.
- Convert external failures into the appropriate Home Assistant coordinator/config-entry exceptions. Preserve cancellation semantics; do not swallow `asyncio.CancelledError` or broadly catch exceptions without a specific reason.
- Validate the response shape before exposing data to entities. A successful HTTP status alone does not prove that the response contains valid or current forecast data.
- Keep timestamps timezone-aware. Interpret epoch timestamps according to the API contract and use the correct timezone when displaying or comparing local forecast times. Handle daylight-saving transitions and interval boundaries.
- Avoid logging credentials, unnecessary full payloads, or sensitive user information. Full-response debug logging should not create excessive log volume or expose data without a clear diagnostic need.
- Keep the configured update interval consistent with the options flow and defaults. Verify that changing options takes effect through the supported config-entry lifecycle.

## Sensor correctness

Audit each entity against the actual API schema and domain semantics. The integration currently describes entities for:

- Nowcast and personalized messages.
- Current precipitation description and precipitation type.
- Time until the next precipitation period.
- Precipitation duration.
- Current precipitation rate.
- Precipitation rate over the next hour.
- Forecast precipitation rate.
- Precipitation time-series/period data.

For every affected sensor, verify:

- The entity reads the correct field from the current coordinator payload.
- Missing, null, malformed, non-finite, or stale data is not silently converted to a plausible but incorrect value, zero, or empty string.
- Numeric values are validated and converted without accepting booleans as measurements.
- The unit, device class, state class, and value semantics are compatible with current Home Assistant requirements.
- Duration and rate calculations use the correct interval, unit, boundary rules, and timestamp basis.
- Attributes containing forecast periods have a stable, documented structure and use timezone-aware timestamps where required.
- Availability reflects the validity and freshness of the underlying data, not merely the fact that a non-empty dictionary exists.
- Entity values remain within the source field's valid domain without arbitrary clamping that hides bad data.

Precipitation intensity is a rate, typically expressed in `mm/h`; do not treat it as accumulated precipitation in millimetres. Do not assign a cumulative/total state class to a rate sensor. Verify the API's meaning before naming or calculating any hourly or total forecast value.

## Binary sensor correctness

The integration defines binary sensors for:

- Precipitation expected.
- Currently raining.
- Currently snowing.

Verify the source period list, precipitation-rate field, precipitation-type vocabulary, and period timestamps against real API examples or reliable fixtures. Confirm that:

- “Precipitation expected” follows the intended forecast horizon.
- “Currently raining” and “currently snowing” only describe the current interval, not any future interval.
- The period duration and interval inclusivity match the API's actual time-series granularity.
- Mixed precipitation types have explicitly tested semantics.
- Missing or invalid period data makes the entity unavailable when the state cannot be determined; it must not be represented as a confirmed “off” state.
- Rain/snow classifications are not inferred from undocumented assumptions about API strings.

## Config flow and entity lifecycle

- Validate latitude and longitude as finite numeric values within their legal ranges. Reject NaN and infinity.
- Keep config-entry unique IDs stable and ensure duplicate detection compares normalized coordinates rather than formatting differences such as trailing zeros, where appropriate.
- Preserve and correctly migrate existing config entries and entity registry identities.
- Use supported config-entry setup, unload, reload, and options-update patterns for the target Home Assistant version.
- Ensure platform setup fails clearly if the coordinator is missing; do not silently create entities with fabricated defaults.
- Ensure entities use the correct device association and do not create duplicate instances from legacy or experimental entity definitions.
- Avoid changing established entity names, keys, or unique IDs unless the migration and user impact are explicitly addressed.

## Testing and validation

Add or update deterministic tests for each behavioral change. Prefer mocked HTTP responses and representative JSON fixtures over live network calls.

At minimum, cover relevant cases among:

- Valid and representative API responses.
- Missing fields, nulls, wrong types, empty time series, and malformed period records.
- Zero, positive, negative, very large, non-finite, and boolean numeric-like values where applicable.
- Exact expected sensor values, units, state/device classes, and attributes.
- Period start/end boundaries, stale periods, future periods, timezone conversion, and daylight-saving changes.
- Rain, snow, mixed precipitation, and unknown precipitation types.
- API timeout, HTTP failure, connection error, invalid JSON, coordinator failure, unavailable state, and successful recovery.
- Config-flow coordinate validation, duplicate entries, migration, and options changes.
- Entity setup/unload and stable unique IDs.

Run the repository's configured tests, linting, type checks, and Home Assistant validation that are available. Report the commands actually run and their results. Do not claim that tests pass if they were not executed.

## Review standard

Report only actionable, evidence-based defects. For each finding, state the affected entity or code path, file and line, concrete failure scenario, expected behavior, actual behavior, severity, and the regression test needed.

Distinguish confirmed defects from unverified risks. If API semantics or live runtime behavior cannot be verified from code, fixtures, documentation, or available credentials, mark them as **NOT VERIFIED** rather than guessing.

Do not treat a sensor as correct solely because it is created, has a non-null state, or passes a test that only asserts entity existence. Sensor correctness requires checking source mapping, transformations, units, timestamps, availability, and representative expected values.
