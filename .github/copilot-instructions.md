# GitHub Copilot Instructions

These instructions apply to all work in this repository, including implementation, debugging, tests, documentation, and code review.

## Required instructions

1. Read the repository-root `AGENTS.md` and `home-assistant.md` in full before starting. Follow both; `home-assistant.md` contains mandatory Buienalarm-specific requirements.
2. Follow any additional applicable instructions in parent directories and nested `AGENTS.md` files. If `AI_POLICY.md` exists in the repository root, `.github/`, or `docs/`, read and follow it.
3. Treat repository instructions as requirements, not suggestions. If instructions conflict, follow higher-priority instructions and explain any unresolved conflict. Do not assume a missing instruction file exists.
4. Inspect the current implementation, tests, manifest, quality-scale checklist, and relevant workflows before deciding on a change. Verify current Home Assistant APIs against official documentation or source when the change depends on them.
5. Make the smallest complete change that fixes the verified problem. Preserve established entity IDs, unique IDs, config-entry behavior, sensor semantics, and compatibility unless a deliberate, justified change requires otherwise.
6. For Home Assistant and Python code, follow the current supported Home Assistant APIs and the Python standards in `AGENTS.md`. Keep I/O asynchronous, validate external data, handle errors and cancellation correctly, use timezone-aware datetimes, and avoid fabricated entity values.
7. Add or update focused regression tests for behavioral changes. Run relevant tests and configured quality checks when available. Report only checks actually run and their real results; clearly state anything not verified.
8. Update documentation, translations, and `quality_scale.yaml` when the change affects them. Do not mark Quality Scale requirements complete or claim a tier without evidence.
9. Keep diffs focused. Do not introduce unrelated refactors, speculative compatibility code, redundant abstractions, or unrequested alternatives. Deliver the single best solution.
10. For code reviews, report only actionable, evidence-based findings. Include severity, affected file/line, concrete failure scenario, impact, and a practical fix. Do not modify files as part of a review unless explicitly asked to implement fixes.

## Buienalarm-specific correctness

- Trace data from the actual API response through parsing and coordinator data to the entity state.
- Validate payload shape, field types, timestamps, freshness, units, and precipitation semantics; do not infer meaning from field names alone.
- Never turn missing, malformed, stale, or indeterminate data into a plausible zero, empty value, or confirmed binary-sensor `off` state.
- Keep rain/snow/current-period logic aligned with verified API semantics and tested interval boundaries.
- Preserve config-entry and entity-registry compatibility; test migrations and lifecycle changes where relevant.

When instructions are unclear, inspect the source and tests and state what remains unverified instead of guessing.
