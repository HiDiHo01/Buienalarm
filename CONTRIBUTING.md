# Contributing to Buienalarm

Contributions that improve the integration's correctness, reliability, documentation, or usability are welcome. Please keep changes focused and follow the repository's Home Assistant-specific requirements in [`AGENTS.md`](AGENTS.md) and [`home-assistant.md`](home-assistant.md). These files take precedence over the brief summary below.

## How to contribute

### 1. Fork the repository

Fork this repository to your GitHub account, then clone your fork locally.

### 2. Create a focused branch

Create a branch that describes the work:

```bash
git checkout -b fix/short-description
```

Use a separate branch for each independent fix or feature. Do not include unrelated formatting changes or refactors.

### 3. Coding guidelines

#### Python and Home Assistant compatibility

- Follow the current supported Home Assistant Core APIs and the Python version declared by the project. Check the repository's `pyproject.toml` and `manifest.json`; do not assume older APIs or examples remain supported.
- Read [`AGENTS.md`](AGENTS.md) and [`home-assistant.md`](home-assistant.md) before working on code. Check any applicable nested instructions as well.
- Follow PEP 8 and the project's configured Black formatting. Use the existing architecture and conventions rather than introducing a parallel pattern.
- Use type hints for functions, methods, parameters, and return values. Add useful docstrings to new modules, classes, functions, and methods.
- Use `snake_case` for variables and functions, `PascalCase` for classes, built-in generic types such as `list[str]` and `dict[str, object]`, and `X | None` for nullable types. Prefix class-internal implementation methods with an underscore.
- Use timezone-aware datetimes. Do not use deprecated Home Assistant APIs when supported replacements exist.
- Prefer small, direct implementations. Avoid unnecessary abstractions, speculative compatibility branches, broad exception handling, and unrelated refactoring.

#### Asynchronous execution and resource safety

- Keep network and other potentially blocking I/O out of Home Assistant's event loop. Use Home Assistant's shared HTTP session and supported asynchronous APIs.
- Set appropriate timeouts, handle expected connection and API failures, preserve cancellation, and clean up resources during unload.
- Use lazy percent-style logging (for example, `_LOGGER.debug("Received %s records", len(records))`) rather than f-string interpolation in logging calls.
- Do not log credentials, sensitive user data, or complete response payloads unless there is a specific, safe diagnostic need.

#### Buienalarm data and entity correctness

- Trace data from the actual API response through parsing and coordinator normalization to each affected entity. Verify the meaning of fields rather than inferring it from their names.
- Validate external payload structure, types, numeric ranges, timestamps, and freshness before exposing values to entities.
- Preserve the distinction between a valid zero, missing data, invalid data, and unavailable data. Do not replace missing or malformed values with plausible defaults.
- Binary sensors must report `on` or `off` only when the available data establishes that state. Missing, malformed, stale, or insufficient data must remain indeterminate or unavailable as supported by the current Home Assistant contract; it must not be converted to `False`.
- Verify precipitation units, rate-versus-total semantics, time intervals, timezone handling, and daylight-saving boundaries.
- Preserve existing entity IDs, unique IDs, config-entry behavior, and registry identities unless a deliberate change includes the required migration and tests.

#### Tests and documentation

- Add or update focused regression tests for every behavioral change. Cover valid data, relevant boundary cases, malformed or missing data, and failure/recovery paths as applicable.
- Prefer deterministic tests with mocked HTTP responses and representative fixtures. Tests should not require live weather services, personal credentials, or physical hardware.
- Assert observable behavior: entity state/value, availability, units, attributes, identifiers, and lifecycle behavior where relevant—not only that an entity was created.
- Update documentation, translations, and the root `quality_scale.yaml` when behavior or applicable Quality Scale evidence changes. Only mark a Quality Scale rule complete after verifying its requirements.
- Do not weaken assertions, add broad lint/type suppressions to hide defects, or claim checks passed unless they were run.

### 4. Run checks

Install the project's development dependencies using its documented environment, then run the relevant checks. The standard test command is:

```bash
pytest
```

Run the configured formatter, linting, type checking, and Home Assistant/HACS validation when available. Check the repository's workflow files for the exact CI commands rather than assuming a command is configured.

Before submitting, inspect the complete diff and confirm that it contains no accidental changes, secrets, generated files, or unrelated refactoring. In the pull request, list the commands actually run and their results. Explicitly identify checks that could not be run.

### 5. Commit and push

Use a concise commit message describing the change:

```bash
git commit -m "Fix precipitation period parsing"
git push origin fix/short-description
```

### 6. Open a pull request

Open a pull request against the appropriate branch. Explain:

- The problem or user need.
- The root cause, when fixing a defect.
- The implementation and any compatibility or entity-registry implications.
- The tests and quality checks run, including their results.
- Any remaining limitations or behavior that could not be verified.

Keep the pull request focused and link related issues when relevant.

### 7. Respond to review feedback

Review each comment against the implementation, project instructions, current Home Assistant APIs, and tests. Fix valid findings and add regression tests where appropriate; do not apply suggestions blindly when they are incorrect or out of scope. After changes, review the full diff and run relevant checks again. Follow the repository's CodeRabbit review instructions in [`AGENTS.md`](AGENTS.md), and do not claim a new review has occurred unless it is verified.

## Reporting issues

When opening an issue, include the Home Assistant and integration versions, a clear description of expected versus actual behavior, relevant sanitized logs, and reproducible steps. Remove credentials, tokens, personal information, and other sensitive data from logs before sharing them.

## Documentation

Keep documentation accurate, concise, and consistent with the actual implementation. Update relevant installation, configuration, troubleshooting, entity, and translation documentation when behavior changes.

## Code of conduct

All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
