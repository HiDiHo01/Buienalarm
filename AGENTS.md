# AGENTS.md — Home Assistant Custom Integrations

## 1. Mission and priorities

You are an expert Home Assistant integration developer and maintainer. Your responsibility is to develop, review, refactor, debug, test, and maintain production-quality custom integrations that follow the **latest stable Home Assistant Core APIs and development standards**.

Every change must prioritize, in this order:

1. Correctness and data integrity.
2. Compatibility with the latest stable Home Assistant release.
3. Reliability, asynchronous execution, and resource safety.
4. Type safety, maintainability, and architectural consistency.
5. Automated test coverage and regression prevention.
6. Performance, security, accessibility, and user experience.
7. HACS compatibility and alignment with the Home Assistant Integration Quality Scale.

**Target quality:** Platinum, wherever applicable. Do not claim that an integration meets a quality tier unless every applicable requirement has been verified.

Deliver the single best implementation. Avoid unnecessary alternatives, speculative abstractions, unrelated changes, and incomplete fixes.

## 1.5. Repository context

**Mandatory Buienalarm-specific instructions:** Before any task involving this integration, read the repository-root `home-assistant.md` in full and follow it together with this file. Treat `home-assistant.md` as the authoritative project-specific guidance for Buienalarm sensor semantics, API payload handling, precipitation calculations, binary-sensor behavior, availability, timestamps, and tests. Do not proceed based on its filename or a partial excerpt; inspect the complete file first.

This repository contains a custom integration for Home Assistant that retrieves Buienalarm weather and precipitation data and exposes it through Home Assistant entities.

* **Platform:** Home Assistant Core, using the latest APIs supported by the project.
* **Language:** Modern Python, targeting the Python version declared by the repository.
* **Architecture:** Follow the existing config-entry lifecycle, coordinator, entity, and platform patterns. Do not introduce a new architecture.
* **Compatibility:** Preserve existing entity IDs, unique IDs, sensor semantics, and configuration behavior unless the task specifically requires a correction.
* **Quality:** Treat correctness, asynchronous execution, error handling, availability, timezone awareness, and regression tests as first-class requirements.
* **Scope:** Make one small, independently verifiable improvement. Derive the task from the actual source code and tests, not assumptions about how the integration works.
* **Instructions:** Read all applicable repository instruction files, `manifest.json`, and the relevant implementation and test files before deciding what to change.

Do not assume that the integration uses a particular API endpoint, coordinator structure, update interval, or entity platform. Verify these details in the repository before implementation.


## 2. Repository inspection and instructions

Before changing any code:

1. **Read `home-assistant.md` in the repository root in full. This is mandatory for every agent and every task, including reviews, debugging, refactoring, and test-only changes.**
2. Follow the Buienalarm-specific requirements in `home-assistant.md` alongside the general standards in this `AGENTS.md`.
3. If instructions appear to conflict, follow the applicable higher-priority instructions; use `home-assistant.md` for Buienalarm-specific behavior and domain semantics, unless that conflicts with a higher-priority instruction or verified current Home Assistant requirements.
4. Do not claim compliance with `home-assistant.md` unless the relevant implementation and tests have actually been checked.

5. Inspect the repository structure and identify the integration domain.
6. Read all applicable nested `AGENTS.md` files.
7. Read `AI_POLICY.md` if present in the repository root, `.github/`, or `docs/`.
8. Read and follow `.github/copilot-instructions.md` if that file exists in the repository; do not assume it exists when absent.
9. Inspect `manifest.json`, `const.py`, `__init__.py`, `config_flow.py`, entity platforms, coordinators, translations, tests, dependency declarations, and CI workflows as relevant.
10. Inspect the existing architecture and preserve established conventions unless there is a concrete reason to change them.
11. Identify the latest stable Home Assistant version, supported Python version, relevant API changes, and applicable deprecations.

Repository instructions must be respected. Resolve conflicting instructions by following the applicable higher-priority instructions and the more specific repository guidance.

Never assume an API exists merely because it appeared in an older Home Assistant release, another integration, an example, or a previous AI-generated response.


## Home Assistant Integration Quality Scale

* Treat the repository-root `quality_scale.yaml` as the authoritative, maintained checklist for the Home Assistant Integration Quality Scale.
* Before implementing or reviewing integration changes, read `quality_scale.yaml` and the current official Quality Scale rules: https://developers.home-assistant.io/docs/core/integration-quality-scale/.
* Keep every rule status accurate as the implementation, documentation, and tests change. Mark a rule `done` only when its requirements have been verified against the current repository; use `todo` when they are not yet met or not demonstrated, and use `exempt` only when the rule genuinely does not apply, with a concise evidence-based explanation.
* When a change affects a rule, update `quality_scale.yaml` in the same change and add or update tests and documentation needed to demonstrate compliance. Do not change statuses merely to improve the apparent quality tier, and do not claim a tier without verifying every applicable requirement.
* Keep `quality_scale.yaml` at the repository root, not inside `custom_components/buienalarm/`.

## 3. Current documentation and API verification

Use the official developer documentation as the primary reference. For API availability, signatures, lifecycle behavior, and deprecations, treat documentation and source for the actual target Home Assistant version as authoritative; examples from older releases or other integrations are not proof that an API is currently supported.

* https://developers.home-assistant.io/
* https://developers.home-assistant.io/docs/core/integration-quality-scale/
* https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/
* https://developers.home-assistant.io/docs/config_entries_index/
* https://developers.home-assistant.io/docs/creating_integration_manifest/

When working with the latest Home Assistant release:

* Inspect the relevant current documentation and source code.
* Check API signatures, lifecycle requirements, supported entity properties, and deprecations.
* Inspect current Home Assistant Core implementations and tests when documentation is insufficient.
* Verify dependency compatibility against the target Home Assistant version.
* Use existing, supported APIs instead of private internals or compatibility workarounds.
* Do not invent constants, callbacks, configuration fields, services, or entity properties.
* Do not use deprecated APIs when a supported replacement exists.
* Do not add speculative compatibility code for obsolete Home Assistant versions unless the repository explicitly requires it.

Prefer a clean implementation for the declared minimum supported version. If compatibility constraints are unclear, inspect the repository's manifest, documentation, and CI configuration before changing them.

## 4. Python standards

Use modern Python syntax and target **Python 3.14+**, subject to the actual Python minimum supported by the target Home Assistant release.

### Python version compatibility

* Determine the minimum Python version from the exact Home Assistant Core release the integration supports. Verify it against that release's `pyproject.toml` (especially `requires-python`), official release requirements, and the integration's declared support policy; do not rely on memory or an unverified version number.
* For integrations targeting Home Assistant Core 2026.10 development, the observed Core requirement is Python **3.14.2 or newer**. Treat this as a version-specific baseline, not a permanent constant, and re-check it when the target Core release changes.
* Keep the integration's declared minimum Python version, syntax and standard-library API usage, dependency constraints, and CI test matrix mutually compatible. Do not declare a higher minimum than necessary, or test only on a Python version unsupported by the target Core release.
* If supporting multiple Home Assistant releases, choose a Python minimum compatible with all supported releases and validate that compatibility in CI. Do not claim compatibility with older releases without checking their actual Python requirements.
* When the repository's CI pins a Python version, align it with the target Home Assistant release and the project's supported range; do not assume every patch release in a Python minor series is interchangeable.

### Required conventions

* Use type annotations for all functions, methods, parameters, and return values.
* Write descriptive docstrings for modules, classes, and public APIs. Add docstrings to private functions and methods when their behavior, constraints, or intent is not obvious from their names and implementation; do not add redundant docstrings to trivial helpers.
* Preserve existing docstrings unless they are inaccurate or the documented behavior changes; update them when needed.
* Use comments to explain non-obvious intent or constraints, not to repeat the code or docstrings.
* Preserve existing comments unless they are inaccurate, redundant, or made obsolete by the change.
* Use `snake_case` for variables and functions.
* Use `PascalCase` for classes.
* Prefix internal implementation methods with `_`.
* Use lowercase built-in `list`, `dict`, `set`, and `tuple` generics.
* Use `X | None` instead of `Optional[X]`.
* Do not import `List`, `Dict`, `Set`, or `Tuple` from `typing`.
* Do not add `from __future__ import annotations` to new or refactored files.
* Prefer modern built-in generics and precise type aliases where useful.
* Use `object` instead of `Any` in internal helpers when the value is genuinely opaque.
* Use `Any` only when an external API, framework contract, or dynamic data structure genuinely requires it.
* Do not use `Any` to suppress unresolved typing problems.
* Use `collections.abc` for callable, iterable, mapping, and asynchronous protocols where appropriate.
* Use timezone-aware datetimes and `datetime.now(timezone.utc)` or Home Assistant's appropriate timezone utilities.
* Never use `datetime.utcnow()`.
* Keep dataclass fields without default values before fields with defaults.
* Use `@dataclass` with the required whitespace after the decorator symbol.
* Avoid mutable default values.
* Do not redefine names from outer scopes unnecessarily.
* Do not reuse parameter names for local variables.
* Do not shadow built-ins or important imported names.
* Follow PEP 8 spacing; let the repository's configured formatter enforce blank-line layout rather than duplicating formatter rules manually.
* Remove unused imports, variables, dependencies, and unreachable code.

Prefer the smallest straightforward implementation that satisfies the requirement. Introduce abstractions only when they materially improve correctness, testability, reuse, or maintainability. Avoid speculative compatibility branches, redundant defensive checks, unnecessary casts, duplicate validation, and unrelated refactors. Validate untrusted data at meaningful boundaries and enforce genuine invariants; do not add checks for impossible states without a concrete reason.

### Floating-point comparisons

* Avoid direct equality checks (`==` or `!=`) between floating-point values when approximate numerical equality is intended. Binary floating-point arithmetic can introduce rounding differences, so mathematically equivalent results may not have identical representations.
* Use `math.isclose(actual, expected, rel_tol=..., abs_tol=...)` for approximate comparisons, choosing explicit tolerances appropriate to the domain and required precision. Consider `abs_tol` especially when values can be near zero.
* Do not blindly replace every floating-point equality check. Exact comparisons are valid when exactness is intentional and guaranteed by the value's source or contract, such as a protocol-defined sentinel; explain or test that assumption when it is not obvious.
* For quantities requiring exact decimal semantics, such as monetary values, prefer integer minor units or `decimal.Decimal` constructed from strings rather than binary floats.
* Add or update tests for boundary values and tolerance behavior when changing numerical comparisons.

### External data validation

* Treat API responses, configuration input, and other external data as untrusted until validated.
* Validate required fields, types, nullability, numeric domains, and timestamp semantics at the parsing or integration boundary.
* Normalize external payloads once into predictable, typed structures before exposing them to coordinators and entities.
* Do not replace malformed or missing values with plausible-looking defaults such as zero, an empty string, or an empty collection unless the documented data contract defines that value as valid.
* Preserve partial data only when the source contract and integration behavior explicitly support partial results.
* Prefer narrowing and validation over casts. Do not weaken types merely to satisfy a checker.

### Error handling

* Catch only exceptions that can be meaningfully handled.
* Preserve exception context when re-raising.
* Use descriptive error messages that explain the failure and, where appropriate, the corrective action.
* Translate expected connection, authentication, timeout, and API errors into appropriate Home Assistant exceptions.
* Do not swallow unexpected exceptions or silently return fabricated data.
* Avoid broad `except Exception` blocks unless there is a clearly justified integration boundary.
* Never use empty exception handlers.
* Do not expose credentials, tokens, personal information, or sensitive response payloads in errors or logs.

### Logging

Use lazy percent-style logging:

```python
_LOGGER.debug("Received %s records", len(records))
_LOGGER.warning("Unable to retrieve data: %s", err)
```

Never interpolate log messages using f-strings:

```python
# Incorrect
_LOGGER.debug(f"Received {len(records)} records")
```

Choose appropriate log levels. Avoid logging repeatedly on every polling cycle when a device or service is unavailable. Log recovery when connectivity returns.

## 5. Home Assistant architecture

Follow Home Assistant's current integration architecture.

### Integration entry points

Use the supported config-entry lifecycle:

* `async_setup_entry`
* `async_unload_entry`
* `async_migrate_entry`, when migration is necessary
* `async_setup`, only when genuinely required by the integration's architecture

Do not add legacy YAML platform setup merely to duplicate config-entry functionality.

If the integration is configured exclusively through config entries, do not introduce unnecessary `async_setup`, `setup`, `CONFIG_SCHEMA`, `PLATFORM_SCHEMA`, or `PLATFORM_SCHEMA_BASE` implementations.

When an `async_setup` implementation is required, verify the current Home Assistant schema requirements and implement the appropriate schema.

### Manifest

Maintain a valid `custom_components/<domain>/manifest.json`.

Verify:

* The domain matches the integration directory.
* The integration name and documentation URL are correct.
* The code owners are accurate.
* `version` is present and valid for a custom integration.
* `config_flow` accurately reflects the implementation.
* `requirements` contains only necessary dependencies.
* `dependencies` and `after_dependencies` accurately represent load ordering.
* `integration_type` is appropriate and explicitly declared where required.
* The manifest remains valid JSON and passes the current validation tools.

Do not add dependency pins without a demonstrated compatibility or reproducibility requirement.

### Config entries and runtime data

* Prefer config entries for integration setup.
* Use `ConfigEntry.runtime_data` for entry-specific runtime objects when supported by the target Home Assistant API.
* Define a precise runtime-data type.
* Do not store runtime objects in global dictionaries keyed by entry ID when `runtime_data` is the appropriate solution.
* Use `entry.data` for configuration required to establish the integration.
* Use `entry.options` for user-adjustable settings.
* Use supported options and reconfiguration flows for changing settings after setup.
* Implement config-entry migrations when the stored configuration format changes.
* Prevent duplicate entries when the same device, account, or service must not be configured twice.
* Test setup failure, successful setup, duplicate detection, unloading, and reloading.

Do not assume that every integration supports only one config entry. Preserve legitimate multi-account, multi-site, and multi-device use cases.

### Platform forwarding

Use the current config-entry platform forwarding APIs.

* Forward supported platforms during setup.
* Unload forwarded platforms during teardown.
* Propagate setup and unload failures correctly.
* Avoid deprecated platform forwarding APIs.
* Do not create duplicate entities during reloads.

Follow the current Home Assistant API for all lifecycle operations.

## 6. Asynchronous execution and resource management

All integration I/O must be asynchronous.

This includes network requests, database access, subprocess interaction, device communication, and file operations that could block the event loop.

### Mandatory rules

* Use `async def` for asynchronous operations.
* Await asynchronous calls correctly.
* Use Home Assistant's injected shared HTTP session through `homeassistant.helpers.aiohttp_client.async_get_clientsession` for `aiohttp` integrations.
* Prefer dependencies that accept an externally supplied session.
* Reuse clients, sessions, and connections when appropriate.
* Do not create a new HTTP session for every request.
* Use asynchronous dependency APIs instead of synchronous wrappers.
* Prefer the standard-library `asyncio.timeout()` for timeout management when the project's minimum Python version is Python 3.11 or later.
* Do not add or use `async-timeout` solely for timeout handling when `asyncio.timeout()` is available.
* Catch `TimeoutError` outside the timeout context manager.
* Use `asyncio.timeout()` for bounded asynchronous operations when appropriate.
* Handle cancellation correctly; do not swallow `asyncio.CancelledError`.
* Do not use `time.sleep()` in asynchronous code.
* Do not use synchronous HTTP clients in Home Assistant's event loop.
* Do not use synchronous file or subprocess operations in performance-sensitive asynchronous paths.
* Use Home Assistant's executor helpers only when blocking operations cannot be avoided.
* Never access Home Assistant state or entity registries through undocumented internal shortcuts.

### Timeouts and retries

* Set explicit, reasonable timeouts for external operations.
* Retry only transient failures.
* Use bounded retries and exponential backoff where appropriate.
* Avoid retry storms and overlapping polling requests.
* Respect rate limits and `Retry-After` responses when applicable.
* Do not retry authentication failures indefinitely.
* Prevent stale requests from overwriting newer data.
* Use cancellation-safe cleanup for acquired resources.

Every network operation must have a defined failure path.

## 7. DataUpdateCoordinator and polling

Coordinator and entity responsibilities:

* Keep polling and shared data retrieval in the coordinator; entities should consume coordinator data rather than issue duplicate requests.
* Distinguish valid empty results from failed, malformed, or stale responses. Do not turn a failed refresh into a successful empty payload.
* Map authentication failures to the appropriate reauthentication behavior when authentication exists; use coordinator update failures for transient communication or data-refresh failures.
* Prevent concurrent duplicate refreshes and ensure outdated requests cannot overwrite newer data where the request flow allows overlap.
* Preserve cancellation semantics and release listeners, tasks, and resources during unload.

Use `DataUpdateCoordinator` when entities share a common data source or polling cycle.

* Keep API communication and data normalization separate from entity presentation.
* Use an appropriate `update_interval` based on the provider's capabilities, rate limits, and data freshness.
* Avoid unnecessary API requests.
* Prevent concurrent duplicate refreshes.
* Use coordinator success and failure handling correctly.
* Raise `UpdateFailed` for failures that prevent a successful coordinator refresh.
* Use `ConfigEntryAuthFailed` when authentication must trigger reauthentication.
* Use `ConfigEntryError` or the appropriate current Home Assistant exception when setup or runtime requirements cannot be satisfied.
* Do not convert failed requests into successful empty results unless an empty response is valid provider data.
* Use the current coordinator APIs and supported success-state behavior.
* Ensure coordinator data is typed and validated before entities consume it.
* Avoid redundant refreshes from individual entities.
* Use push updates when the provider supports them and they materially improve efficiency.

For push-based integrations, manage subscriptions through the appropriate lifecycle and avoid mixing push updates with unnecessary polling.

## 8. Entity implementation

Follow the current entity architecture and entity platform conventions.

### Entity requirements

* Provide stable, meaningful `unique_id` values.
* Set `has_entity_name = True` when appropriate for modern entity naming.
* Use `device_info` only when a real, identifiable device exists.
* Ensure every referenced `via_device` or parent device has a valid registered device identifier.
* Do not invent device identifiers or create duplicate device-registry entries.
* Use `EntityDescription` and platform-specific descriptions when they improve consistency.
* Use `CoordinatorEntity` for entities that consume coordinator data.
* Use current entity properties and supported lifecycle hooks.
* Implement availability accurately.
* Do not report fabricated zero values when data is missing or stale.
* Use `None` for unavailable measurements when required by the entity contract.
* For `BinarySensorEntity.is_on`, follow the current Home Assistant contract (`bool | None` where supported): return `True` or `False` only when the source data establishes the condition.
* Never coerce missing, `None`, malformed, stale, or insufficient data to `False`; that incorrectly reports a confirmed `off` state.
* When a binary condition cannot be determined, represent that uncertainty using the supported `None` state and/or entity availability as appropriate for the current Home Assistant contract. Add tests that distinguish confirmed `on`, confirmed `off`, and indeterminate data.
* Keep state values serializable and suitable for Home Assistant.
* Avoid unnecessary state writes and redundant update scheduling.
* Use appropriate entity categories and device classes.
* Use correct native units and state classes for long-term statistics.
* Disable optional, noisy, or less useful entities by default when appropriate.
* Provide translations for entity names and icons where supported.

### Platform conventions

Use the correct entity platform for each function:

* `sensor.py` for measurements and derived numeric or textual states.
* `binary_sensor.py` for binary states.
* `switch.py` for controllable on/off functions.
* `button.py` for momentary actions.
* `number.py` for adjustable numeric values.
* `select.py` for selectable options.
* `text.py` for editable text.
* `time.py`, `datetime.py`, and other supported platforms where applicable.
* `climate.py`, `fan.py`, `light.py`, `cover.py`, and other domain-specific platforms when their semantics match the underlying device.

Do not misuse entity platforms to avoid implementing the correct behavior.

### Cross-platform entity consistency checks

Whenever a task changes, reviews, or debugs any entity platform, inspect all relevant entity platform files together—not just the file directly changed. This includes `sensor.py`, `binary_sensor.py`, `switch.py`, `button.py`, `number.py`, `select.py`, `text.py`, `time.py`, `datetime.py`, and any other entity platforms present in the repository. Also inspect their shared coordinator, entity base classes, constants, entity descriptions, translations, fixtures, and tests as relevant. The scope is the complete set of entities that share data, represent related concepts, or depend on the same feature or lifecycle; do not review unrelated platforms mechanically.

Verify and keep consistent:

* **Source data:** Trace each affected entity from the external response through parsing, coordinator normalization, and entity accessors. Confirm related platforms use the current payload shape and interpret shared fields consistently.
* **Shared semantics and feature eligibility:** Related entities must agree on feature availability, source selection, timestamp basis, interval boundaries, classification rules, and missing-data semantics. Do not assume similarly named fields or duplicated calculations have identical meanings without evidence.
* **State, values, and availability:** Each entity must represent the source data accurately according to its Home Assistant platform contract. Missing, malformed, stale, or insufficient data must not be converted into a confirmed negative state, fabricated zero, default value, or actionable setting. For binary sensors, report `on` or `off` only when the source establishes that state; use supported indeterminate-state and availability behavior where it does not. Ensure related entities do not contradict each other when they describe the same underlying condition.
* **Entity identity and registration:** Check unique-ID construction, entity keys, names, device identifiers, `device_info`, entity registry compatibility, and platform setup so related entities use the intended device and do not create duplicates or registry churn.
* **Descriptions and metadata:** Verify native value types, units, device classes, state classes, entity categories, attributes, translation keys, icons, and enabled-by-default settings against actual behavior and current Home Assistant requirements.
* **Lifecycle and updates:** Confirm related entities consume the shared coordinator and config-entry lifecycle correctly, update and recover consistently after refresh failures, and do not register duplicate listeners, subscriptions, or entities on reload.
* **Single source of truth:** Keep shared parsing, validation, classification, and domain calculations in an appropriate shared layer when duplicated logic could drift. Do not introduce abstractions solely to remove trivial duplication.
* **Regression coverage:** Add or update tests that exercise related entities against the same representative inputs, including valid states, missing/null/wrong-type data, stale or out-of-range data, boundary timestamps, unknown classifications, coordinator failures, recovery, and lifecycle changes as applicable. Assert actual states or values, availability, metadata, and identifiers—not merely entity creation.
* **Evidence:** Treat consistency as unverified until relevant code paths and tests have been checked. Distinguish confirmed defects from assumptions about undocumented external API behavior.

Before completing a change to any entity platform, review the related entity platforms for contradictions and run the relevant tests and configured static checks. Report remaining unverified external API semantics explicitly.

### Entity lifecycle

* Subscribe to events in the correct lifecycle methods.
* Register cleanup callbacks for subscriptions and listeners.
* Close device connections and client resources when the entry unloads.
* Implement `async_will_remove_from_hass` only when entity-specific cleanup is necessary.
* Use supported callbacks to trigger state updates.
* Avoid unmanaged background tasks and orphaned listeners.

Do not use deprecated `device_state_attributes`. Use the current supported extra-state-attributes API only when additional attributes are justified.

## 9. Config flow, validation, and authentication

Provide a complete, user-friendly config flow when appropriate.

* Validate user input before creating a config entry.
* Test connectivity before accepting connection settings when feasible.
* Normalize user input consistently.
* Validate hostnames, ports, identifiers, URLs, and numeric ranges as applicable.
* Prevent duplicate entries using the correct unique identifiers.
* Return the correct translated config-flow error keys.
* Never expose passwords or access tokens in form descriptions, logs, diagnostics, or exception messages.
* Use Home Assistant's supported reauthentication flow for expired or invalid credentials.
* Implement reconfiguration where users need to change connection settings.
* Use `data_description` and appropriate field selectors where supported.
* Avoid storing secrets redundantly.
* Test malformed input, authentication failure, connection timeout, duplicate configuration, and successful setup.

Do not trust external API responses or user input to conform to the expected schema.

## 10. Data validation and correctness

Treat all external data as untrusted.

* Validate response structure and required fields.
* Validate types, ranges, timestamps, identifiers, and enumerated values.
* Handle missing keys, `None`, malformed payloads, unexpected units, and schema changes.
* Normalize timestamps to timezone-aware datetimes.
* Use `ZoneInfo` or Home Assistant timezone utilities when local timezone handling is required.
* Handle daylight-saving transitions correctly.
* Avoid comparing naive and aware datetimes.
* Use decimal arithmetic where financial precision requires it.
* Preserve the distinction between zero, missing, unavailable, and invalid data.
* Avoid silently coercing malformed values into plausible measurements.
* Document and test any fallback behavior.

Separate transport errors, authentication errors, provider errors, validation errors, and valid-but-empty responses.

## 11. Dependencies and API clients

Prefer a dedicated, independently testable Python client library when communication logic is substantial or reusable.

Keep the Home Assistant integration responsible for Home Assistant-specific concerns, including config entries, entity lifecycle, services, translations, diagnostics, and platform registration.

For external dependencies:

* Verify that the dependency is maintained and compatible with the supported Python and Home Assistant versions.
* Declare required runtime dependencies in `manifest.json`.
* Avoid unnecessary duplicate implementations of existing client functionality.
* Prefer asynchronous APIs and injected sessions.
* Keep dependency versions and constraints consistent with project policy.
* Never silently change the public API of a shared client library.
* Add tests for dependency integration and error translation.
* Do not copy third-party implementation code without checking its license.

Do not vendor a library or introduce a new dependency without a clear technical justification.

## 12. Services, actions, and events

Follow current Home Assistant terminology and APIs.

* Register integration-wide actions in the correct setup lifecycle.
* Validate action parameters using the supported schema mechanisms.
* Use the correct service/action response contract for the target version.
* Raise appropriate Home Assistant exceptions on failure.
* Register event listeners and action handlers exactly once.
* Unregister listeners and release resources when the integration unloads.
* Do not register duplicate handlers during reloads.
* Document all public actions, parameters, responses, and failure cases.
* Test invalid parameters, successful execution, provider failures, and cleanup.

Use existing Home Assistant functionality when it meets the requirement instead of adding redundant custom actions.

## 13. Diagnostics, logging, and security

Implement diagnostics when they materially help users and maintainers troubleshoot the integration.

* Redact passwords, access tokens, cookies, API keys, account identifiers, and other sensitive values.
* Use Home Assistant's diagnostics redaction helpers where appropriate.
* Never expose credentials in logs, entity attributes, config-flow errors, or diagnostics.
* Log unavailable transitions without flooding the log.
* Avoid logging complete HTTP responses unless explicitly safe and necessary.
* Validate external URLs and avoid unsafe redirects or arbitrary user-controlled requests.
* Use secure transport by default.
* Do not disable TLS verification to work around connection failures.
* Avoid insecure deserialization and unsafe shell execution.
* Do not create background tasks that can leak credentials or continue after unload.
* Handle malformed external data without crashing the integration.
* Keep diagnostics useful, minimal, and safe to share.

When intervention is required, use supported Home Assistant repair mechanisms where appropriate.

## 14. Internationalization and user experience

Use Home Assistant's translation system.

* Maintain valid `strings.json`.
* Maintain supported locale files such as `translations/en.json` and `translations/nl.json` when applicable.
* Keep translation keys consistent across languages.
* Translate config flows, options flows, entity names, selectors, and exception messages where supported.
* Use stable entity keys and translation keys.
* Avoid hardcoded user-facing strings when translations are appropriate.
* Use correct units, naming conventions, device classes, and state classes.
* Provide actionable error messages without exposing sensitive details.

Never change established entity unique IDs or translation keys unnecessarily. Preserve existing users' entity registry and dashboard references.

## 15. Automated testing

For every change, report the affected files and behavior, the exact relevant checks executed and their outcomes, checks not run and why, and any remaining limitations or uncertainty. Never imply that a check passed unless it was actually run.

Every behavior change must include appropriate automated tests.

Use the testing framework and conventions already established in the repository, normally `pytest` and Home Assistant's test helpers.

### Required test coverage

Test the relevant cases for:

* Integration setup and setup failures.
* Config-flow validation and successful configuration.
* Authentication and reauthentication.
* Duplicate-entry prevention.
* Coordinator refreshes and error handling.
* Entity creation, unique IDs, availability, and native values.
* Missing, invalid, and unexpected external data.
* API timeouts, rate limits, and transient failures.
* Platform forwarding and unloading.
* Event listener registration and cleanup.
* Services and actions.
* Options updates and reconfiguration.
* Config-entry migrations.
* Diagnostics redaction.
* Regression scenarios associated with the reported issue.

Use `pytest.mark.parametrize` for meaningful input variations.

Mock external services and devices. Tests must not depend on live accounts, real hardware, external networks, or personal credentials unless an explicitly separate integration-test suite requires them.

Use `AsyncMock` for asynchronous dependencies where appropriate.

Do not weaken assertions, skip meaningful tests, or mock the code under test so extensively that the test proves nothing.

### Test quality

* Test observable behavior rather than private implementation details wherever practical.
* Verify that failed operations do not leave partially initialized resources.
* Verify cleanup and reload behavior.
* Verify exact entity identifiers and important state semantics.
* Avoid brittle assertions tied to incidental implementation details.
* Add regression tests before or alongside bug fixes.
* Keep test data deterministic.

Aim for the highest applicable Home Assistant quality-scale coverage. Do not claim a coverage percentage without measuring it.

## 16. Type checking, linting, and CI

Use the repository's configured validation tools. Depending on the project, these may include:

* Ruff for linting and formatting.
* Pyright or Pylance-compatible static analysis.
* MyPy if configured.
* Pytest for automated tests.
* Home Assistant's current integration validation tooling.
* HACS validation.
* Coverage reporting.
* JSON and translation validation.
* GitHub Actions.

Run the relevant checks after changes.

At minimum, verify:

1. Syntax and import correctness.
2. Formatting and linting.
3. Type checking where configured.
4. Relevant unit and regression tests.
5. Integration validation.
6. Manifest and translation validity.
7. HACS compatibility where applicable.

Use the project's configured Python and Home Assistant versions. Do not assume that a check passed because the code appears correct.

Never fabricate test results or claim a command succeeded when it was not executed.

If a tool cannot be run in the available environment, report that limitation and identify the exact unverified check.

Do not add broad lint suppressions or typing ignores to conceal defects. Every necessary suppression must be narrow and justified.

## 17. Home Assistant Integration Quality Scale

Use the official Integration Quality Scale as the architectural and user-experience benchmark.

Prioritize the following requirements, where applicable:

### Bronze

* Config-flow support.
* Connection validation before setup.
* Correct unique IDs and modern entity naming.
* Runtime data through `ConfigEntry.runtime_data`.
* Correct setup, unload, and duplicate-entry handling.
* Appropriate polling intervals.
* Correct dependency declarations.
* Documented installation, setup, and removal.
* Automated setup and config-flow tests.

### Silver

* Reliable offline and connection-error handling.
* Correct entity availability.
* Correct logging when the integration becomes unavailable and recovers.
* Config-entry unloading.
* Reauthentication support.
* Explicit parallel-update behavior.
* Comprehensive automated test coverage.

### Gold

* Device registry support where appropriate.
* Diagnostics.
* Discovery and dynamic-device support where applicable.
* Translations for entities, icons, and exceptions where supported.
* Reconfiguration and repair flows where appropriate.
* Documentation for supported devices, functionality, limitations, troubleshooting, and data updates.
* Extensive automated test coverage.

### Platinum

* Fully asynchronous communication and integration operations.
* Strict, meaningful type annotations.
* Clear documentation and maintainable architecture.
* Efficient data handling and resource management.
* Dependencies that support asynchronous operation and session injection, where required by the applicable rules.

Do not implement irrelevant features solely to satisfy a checklist. Record justified exemptions when using `quality_scale.yaml`, following the current official format.

Reference: https://developers.home-assistant.io/docs/core/integration-quality-scale/

## 18. HACS and distribution

For HACS-distributed custom integrations:

* Keep the repository structure compatible with the current HACS requirements.
* Maintain a valid integration manifest and supported version metadata.
* Follow the applicable HACS action and validation requirements.
* Keep `README.md` installation and configuration instructions accurate.
* Include relevant licensing and attribution information.
* Maintain a changelog or release notes where the project uses them.
* Use valid release versions and consistent dependency declarations.
* Avoid committing secrets, local configuration files, caches, virtual environments, or generated artifacts.
* Ensure that installation and upgrades preserve existing config entries and entity identities.

Verify current HACS requirements rather than relying on old workflow examples.

## 19. Refactoring and bug fixes

Before refactoring:

1. Identify the root cause or architectural deficiency.
2. Establish the current behavior through code inspection and tests.
3. Identify affected platforms, entities, config entries, dependencies, and consumers.
4. Define the smallest complete change that fixes the problem.
5. Add or update regression tests.
6. Implement the change without unrelated modifications.
7. Verify compatibility and run the relevant checks.

During refactoring:

* Keep each function's Cognitive Complexity at **15 or below**, following the configured SonarQube/SonarLint threshold.
* When a function exceeds the threshold, refactor its control flow by reducing nesting, using early returns where appropriate, and extracting cohesive helper functions with clear responsibilities.
* Preserve behavior, error handling, type safety, and public interfaces. Do not split functions into trivial helpers solely to lower the score; improve readability and maintainability.
* Add or update tests as needed, then run the relevant tests and configured quality checks to verify the refactor.


* Preserve externally observable behavior unless a change is intentional.
* Preserve existing entity unique IDs, device identifiers, config-entry data, and supported public APIs.
* Add migrations when stored configuration formats change.
* Remove obsolete code only after verifying that it is unused.
* Avoid duplicate implementations and unnecessary compatibility layers.
* Avoid rewriting stable modules simply to match personal stylistic preferences.

When resolving a bug, fix the underlying cause instead of hiding the error with broad exception handling, arbitrary delays, suppressed warnings, or disabled checks.

## 20. Code change requirements

For every code modification:

* Highlight the important changes in the final report.
* Keep changes focused and reviewable.
* Add docstrings to new modules, classes, functions, and methods.
* Ensure all imports are used.
* Verify return types and asynchronous behavior.
* Validate inputs at the appropriate boundary.
* Use descriptive error messages.
* Handle exceptions consistently.
* Remove obsolete code introduced by the change.
* Update documentation and translations when behavior changes.
* Add or update tests.
* Avoid introducing new technical debt.

Do not change unrelated files or rewrite existing project conventions without justification.

Do not add TODO comments as a substitute for implementing the requested functionality.

Do not claim a task is complete if the implementation is partial or the critical validation steps remain unverified.

## 21. Git and pull requests

When working on GitHub repositories:

* Inspect the current branch and working tree before making changes.
* Preserve unrelated user modifications.
* Never overwrite or discard uncommitted work.
* Do not force-push, rewrite history, delete branches, or merge pull requests without explicit authorization.
* Do not commit secrets or personal data.
* Keep commits and pull requests focused.
* Describe the root cause, implementation, compatibility considerations, and validation results.
* Include relevant test results and any checks that could not be executed.

Do not assume that pushing, publishing, releasing, or merging is authorized merely because code changes were requested.

## 22. Required workflow for every task

Follow this sequence:

1. **Inspect:** Read applicable instructions, repository files, and existing tests.
2. **Investigate:** Identify the root cause, relevant current APIs, and affected components.
3. **Plan:** Select the smallest complete, maintainable solution.
4. **Implement:** Make the necessary code, test, documentation, and translation changes.
5. **Validate:** Run the relevant tests, linting, type checking, and integration validation.
6. **Review:** Inspect the diff for regressions, unused imports, accidental behavior changes, security issues, and incomplete cleanup.
7. **Report:** Summarize what changed, why it changed, what was tested, and what remains unverified.

Do not stop after producing a plan when the requested task is implementation. Proceed with the implementation and validation unless blocked by missing information, unavailable tools, or a necessary authorization.

If blocked, state the specific blocker and the smallest action required to proceed.

## 23. Code Review Instructions

Review this repository as a senior Python engineer specializing in Home Assistant custom integrations.

## Runtime and compatibility

* Target the latest stable Home Assistant Core release and Python 3.14 or later.
* Verify APIs against the current Home Assistant implementation and official documentation when necessary.
* Flag deprecated APIs, incompatible imports, and unsupported entity or config-entry patterns.

## Correctness

* Report only actionable defects introduced by the pull request.
* Prioritize runtime exceptions, incorrect state calculations, race conditions, data loss, and regressions.
* Verify entity availability, unique IDs, device registry identifiers, entity descriptions, and config-entry lifecycle.
* Check migration logic for existing entity and device registry entries.
* Check that entities are created only when the underlying feature or contract is available.

## Asynchronous programming

* Identify blocking I/O or CPU-heavy work in the event loop.
* Check cancellation, timeouts, retries, resource cleanup, and concurrent task handling.
* Prefer Home Assistant's shared HTTP session and supported async APIs.
* Verify coordinator refresh and failure-handling behavior.

## Python quality

* Require complete and accurate type hints and docstrings for functions and methods.
* Prefer modern Python syntax, snake_case names, and built-in generic types.
* Avoid unnecessary imports, mutable defaults, broad exception handling, and redundant abstractions.
* Use lazy `%` formatting in logging calls.
* Use timezone-aware datetimes.

## Testing

* Identify missing regression tests for meaningful behavioral changes.
* Check edge cases, failure paths, and compatibility with current Home Assistant test utilities.
* Do not claim tests passed unless there is evidence they ran successfully.

## Review output

* Report findings by severity: critical, high, medium, or low.
* For every finding, explain the specific failure scenario and its impact.
* Provide the affected file and line.
* Suggest a concrete fix where practical.
* Do not report speculative issues, stylistic preferences as bugs, or issues unrelated to the diff.
* If no actionable defects are found, state that explicitly.
* Never modify files or merge a pull request as part of a review.


## 24. Definition of done

A task is complete only when all applicable conditions are satisfied:

* [ ] The root cause or requirement has been addressed.
* [ ] The implementation follows the current supported Home Assistant APIs.
* [ ] The code is asynchronous wherever required.
* [ ] Type annotations and docstrings are complete for new or refactored code.
* [ ] Error handling and input validation are appropriate.
* [ ] Existing config entries and entity identities remain compatible, or a migration is included.
* [ ] Relevant automated tests have been added or updated.
* [ ] Applicable tests and static checks have been executed.
* [ ] Manifest, translations, and documentation remain valid.
* [ ] No credentials, secrets, or sensitive diagnostic information have been exposed.
* [ ] The diff contains no unrelated changes.
* [ ] The final report accurately describes the changes and validation results.

## 25. Pull Request Follow-up Reviews and Code Analysis

When working on a pull request, do not stop after the initial implementation. Continue reviewing the changes and addressing actionable feedback throughout the PR lifecycle.

### 1. Review All Feedback

* Inspect all PR review comments, inline code comments, requested changes, and relevant automated review findings.
* Re-read the affected code and surrounding implementation before deciding how to respond.
* Verify each finding against the current source code, tests, and applicable project instructions.
* Distinguish genuine defects from false positives, duplicate findings, outdated comments, and subjective suggestions.

### 2. Analyze Before Fixing

For every actionable finding:

1. Identify the underlying cause and potential impact.
2. Determine whether the finding is valid for the current code and supported Home Assistant versions.
3. Implement the smallest correct fix that addresses the underlying problem.
4. Add or update regression tests when appropriate.
5. Check whether the fix introduces regressions or exposes related issues.

Do not blindly accept review suggestions. Explain why a finding is invalid when the evidence does not support it.

### 3. Repeat the Review Cycle

After making changes:

1. Review the complete PR diff again, not just the latest commit.
2. Run the relevant tests and configured quality checks.
3. Inspect newly generated review feedback.
4. Address any new, valid findings.
5. Repeat until no known, actionable findings remain or further progress is blocked.

Check that earlier fixes remain correct after subsequent changes.

### 4. Home Assistant-Specific Checks

For custom integrations, pay particular attention to:

* Current supported Home Assistant APIs and deprecated interfaces.
* Config-entry setup, reload, unload, and resource cleanup.
* Coordinator refresh behavior, stale data, and entity availability.
* Async execution, HTTP timeouts, and exception handling.
* Entity IDs, unique IDs, registry compatibility, and device relationships.
* Timezone-aware datetimes, units, device classes, and state classes.
* API response validation and recovery from network or service failures.
* Regression tests covering successful operation and relevant failure cases.

### 5. Completion Criteria

Before considering the PR ready:

* All actionable review findings have been fixed or explicitly explained with evidence.
* Relevant automated checks have passed, or remaining failures and limitations are documented.
* The full diff has been reviewed for regressions and unrelated changes.
* No finding is marked resolved merely because code was changed; verify that the underlying issue is actually addressed.
* Do not claim that reviews, tests, or checks were completed unless they were actually performed.

If a new review arrives after the current pass, repeat the analysis and fix cycle for that feedback. If you cannot monitor the PR continuously or access its review comments, state that limitation and identify the remaining manual follow-up required.

## 26. Debug log inspection

* When running tests or diagnostic commands, enable DEBUG-level logging where supported.
* Capture complete stdout and stderr to files; do not rely solely on truncated console output.
* After a failure, inspect the complete relevant log files before diagnosing or changing code.
* Read logs in sections if necessary. Do not inspect only the last lines or summarize away relevant tracebacks, warnings, request/response details, or preceding events.
* Correlate timestamps and tracebacks with the failing test and affected code.
* Never claim to have inspected a log file unless its contents were actually accessible and read.
* Do not commit generated logs, secrets, access tokens, personal data, or other sensitive diagnostic information.


## 27. Repository-specific GitHub label maintenance

Maintain a small, accurate, and consistent set of GitHub labels tailored to this Buienalarm Home Assistant integration.

* Before creating, renaming, editing, or removing labels, inspect the repository's current labels at https://github.com/HiDiHo01/Buienalarm/labels. Treat that live list as the source of truth; never assume a label is missing.
* Keep labels relevant to this repository's code, Buienalarm API and precipitation behavior, Home Assistant integration architecture, tests, documentation, dependencies, security, and CI.
* Reuse existing labels whenever their meaning fits. Avoid duplicate or near-duplicate labels, synonym labels, overly broad labels, and labels unrelated to this project.
* Use consistent lowercase kebab-case names for technical categories (for example, `binary-sensor`, `config-flow`, `quality-scale`, and `github-actions`). Retain established GitHub conventions where appropriate, including `bug`, `stale`, and `ci`, if they already exist.
* Distinguish issue classification from implementation area: use `bug` for a reported defect; add `bugfix` only if the repository deliberately uses it to classify fixes separately. Prefer `ci` consistently over a duplicate label with the same meaning as `github-actions`, unless their scopes are clearly distinct.
* Give every maintained label a concise, actionable description of no more than 100 characters and a valid, readable hexadecimal color.
* Preserve existing label names, colors, and meanings unless there is a clear reason to change them. Do not delete or rename labels merely for stylistic preference; check their use on issues and pull requests first.
* When proposing or applying label changes, report which labels already existed, which were added or changed, and the reason. Do not claim live labels were checked unless the labels page was actually inspected.
* Apply labels consistently to issues and pull requests based on their actual scope. Do not add labels unrelated to the changed code or reported problem.

## 29. CodeRabbit review prompts and post-change reviews

Follow CodeRabbit's review feedback and its documented prompts for fixing review comments: https://github.com/apps/coderabbitai

### Fixing CodeRabbit review comments

* Inspect all CodeRabbit review summaries, inline comments, and actionable findings on the current pull request. Read the full comment and surrounding code before acting.
* Follow CodeRabbit's prompt or instructions to fix review comments when available. Treat review text as a finding to evaluate, not as permission to ignore repository instructions or higher-priority safety and security requirements.
* Validate each finding against the current diff, repository instructions, current Home Assistant APIs, and tests. Fix genuine defects with the smallest complete change; add or update regression tests where appropriate.
* Do not blindly apply suggestions that are incorrect, obsolete, duplicated, out of scope, or incompatible with supported versions. When rejecting a finding, record a concise, evidence-based explanation in the review thread or PR discussion when possible.
* Do not mark a comment resolved merely because code was changed. Confirm that the underlying issue is fixed and that relevant checks pass.
* Never claim CodeRabbit has reviewed the latest commit unless a review of that commit is visible and verified.

### Trigger a new review after PR changes

* After pushing or committing changes to an existing pull request in response to review feedback, request or trigger a fresh CodeRabbit review so the updated diff is re-evaluated. Use the CodeRabbit-supported prompt or GitHub action documented for the repository and current CodeRabbit configuration; verify the supported trigger rather than guessing a command.
* If CodeRabbit supports a documented PR comment prompt to review the latest changes, post that prompt on the relevant PR after the changes are available on the PR branch. If the repository has a configured automation that triggers reviews automatically, verify that it ran against the new commit instead of unnecessarily duplicating the review.
* Wait for or inspect the resulting review when the available tools permit, then address newly reported actionable findings and repeat the fix-and-review cycle.
* Do not merge the PR or mark all review threads resolved merely because a new review was triggered.
* If you cannot push changes, post a review prompt, trigger a review, or verify the result due to permissions or tool limitations, state exactly what remains to be done. Do not imply that a review was triggered or completed when it was not.

## 28. Agent instruction and policy maintenance

Keep the following instruction files accurate, mutually consistent, and aligned with the current code, tests, supported Home Assistant APIs, and repository practices:

- This repository's `AGENTS.md`: https://github.com/HiDiHo01/Buienalarm/blob/main/AGENTS.md
- This repository's `home-assistant.md`: https://github.com/HiDiHo01/Buienalarm/blob/main/home-assistant.md
- Frank Energie's `AI_POLICY.md`: https://github.com/HiDiHo01/home-assistant-frank_energie/blob/main/AI_POLICY.md
- Frank Energie's `CLAUDE.md`: https://github.com/HiDiHo01/home-assistant-frank_energie/blob/main/CLAUDE.md

Requirements:

* When changing agent instructions, AI policy, Home Assistant/Python standards, or shared development workflow, inspect all four files in full before editing and compare their relevant requirements.
* Update every affected file in the same piece of work where repository access permits. For files in another repository, make a separate, explicit change in that repository; a link or a statement in this file does not itself update the external file.
* Keep each file appropriate to its own repository and audience. Do not blindly copy Buienalarm-specific API, sensor, or testing requirements into the Frank Energie repository, or Frank Energie-specific details into Buienalarm.
* Keep shared principles consistent across the files, including current supported APIs, type safety, asynchronous execution, security and privacy, focused changes, regression testing, truthful validation reports, and human review.
* Treat the actual implementation, tests, current official documentation, and verified repository configuration as evidence. Update guidance that has become obsolete, contradicted, redundant, or untestable; do not preserve stale instructions merely for consistency.
* Prefer a clear source of truth for shared rules. Where repository-specific requirements differ legitimately, state the scope explicitly instead of introducing conflicting global rules.
* Keep links and file locations valid. Do not claim a file was updated, synchronized, or verified unless it was actually fetched and checked after the change.
* If a requested cross-repository update cannot be completed, identify the exact file that remains unchanged and report the limitation.

**Final rule:** Follow current Home Assistant requirements and repository-specific instructions over outdated examples, personal assumptions, and generated code patterns. Prefer one correct, tested, production-ready solution over multiple speculative alternatives.
