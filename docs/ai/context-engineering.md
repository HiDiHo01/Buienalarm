# Context Engineering for AI-Assisted Development

## Goal

Keep AI work accurate across long sessions and different agents by loading only relevant context, preserving verified findings, and continuously checking for stale or contradictory information.

## Context source map

| Context | Canonical location | Load when |
|---|---|---|
| Task routing and non-negotiable repository requirements | `/AGENTS.md` | Every task |
| Buienalarm behavior, API assumptions, entity semantics, testing | `/home-assistant.md` | Every task |
| AI usage, trust boundaries, verification and handoff policy | `/AI_POLICY.md` | Every AI-assisted task |
| Python/Home Assistant engineering rules, tests, typing, Quality Scale, HACS | `/docs/ai/engineering-standards.md` | Implementation, refactoring, debugging, code review, or related engineering work |
| Git/GitHub, pull-request review cycles, diagnostics, labels, instruction maintenance | `/docs/ai/repository-workflow.md` | Repository operations, PR work, reviews, diagnostics, labels, or instruction changes |
| Agent-specific entry point | `/CLAUDE.md`, `/.github/copilot-instructions.md`, or tool configuration | When using that agent |
| Actual implementation and runtime contract | `custom_components/buienalarm/` | According to task scope |
| Expected behavior and regression evidence | `tests/` and fixtures | Before behavior changes |
| Current quality status | `quality_scale.yaml` | Integration behavior, docs, or quality-scale work |
| CI and automation behavior | `.github/workflows/` and project configuration | When checks or automation are affected |

This table is a navigation aid, not proof that a path exists. Verify paths in the current branch before relying on them.

## Task protocol

### 1. Define a bounded task

Write down:

- **Goal:** one observable outcome.
- **Scope:** files or components likely to be involved.
- **Constraints:** compatibility, entity registry, API semantics, security, and user-facing behavior.
- **Acceptance criteria:** testable conditions for completion.
- **Out of scope:** adjacent cleanup that must not be bundled in.

Prefer one independently verifiable change per task. Split unrelated goals into separate tasks.

### 2. Load context progressively

1. Read all applicable instructions, including parent and nested instructions.
2. Follow the task-routing requirements in `AGENTS.md`; load detailed engineering and repository-workflow references when applicable.
3. Inspect the repository status, relevant files, manifest, and configuration.
4. Search for call sites, data producers/consumers, tests, fixtures, translations, and workflows affected by the change.
5. Read additional files only when needed to establish the actual behavior or contract.
6. Verify version-sensitive Home Assistant APIs against current official documentation or source.

Do not substitute broad summaries for the source that determines the answer. Do not assume a filename, function, endpoint, entity, test, or workflow exists until verified.

### 3. Separate evidence from assumptions

Use these labels in investigations and handoffs:

- **Verified:** directly confirmed in current source, tests, workflow output, or authoritative documentation.
- **Inferred:** a reasoned interpretation supported by named evidence.
- **Unknown / NOT VERIFIED:** requires runtime access, live API evidence, missing fixtures, or a check not yet run.

For each suspected defect, trace:

`external input → parsing/validation → coordinator/runtime data → entity calculation → exposed state/attributes`

Record the specific files, symbols, and tests that support the conclusion. A passing entity-existence test does not prove that sensor values, units, timestamps, or availability are correct.

### 4. Implement with a small change surface

- Make the smallest complete change that meets the acceptance criteria.
- Preserve entity IDs, unique IDs, configuration behavior, and established semantics unless a verified defect requires changing them.
- Add or update focused regression tests.
- Update translations, documentation, and `quality_scale.yaml` when affected.
- Avoid speculative abstractions, duplicate rules, unrelated refactors, and unsupported compatibility claims.

### 5. Verify and report

Run relevant tests and quality checks available in the repository. Report:

- Commands actually executed and their outcomes.
- Files changed and the reason for each change.
- Behavior verified by tests versus behavior only inspected statically.
- Checks not run and why.
- Remaining risks, assumptions, and unknowns.

Never say a test, live API call, CI workflow, review, or merge succeeded unless its result was observed.

## Session handoff format

For work that spans sessions or requires a fresh agent, maintain a concise handoff in the task or pull request. Do not create a permanent handoff file for every small task.

```markdown
## Task
- Goal:
- Acceptance criteria:
- Scope / constraints:

## Verified findings
- Finding:
  Evidence: path, symbol or test, and commit/ref if relevant.

## Changes
- Path:
  Reason:

## Verification
- Command/check:
  Result: PASS / FAIL / NOT RUN

## Unresolved
- Question or risk:
  Evidence needed:

## Next action
- One concrete next step:
```

Keep it short enough to scan. Store durable decisions in repository documentation or tests, not only in chat history. Never paste secrets or unnecessary raw production payloads into a handoff.

## Context rot controls

Context is stale when it no longer matches the current branch, source, configuration, dependencies, tests, or upstream APIs. Before reusing a prior conclusion:

1. Confirm the branch and current commit.
2. Re-open the cited files and check that the relevant code still exists.
3. Re-run the smallest test or search that can falsify the conclusion.
4. Replace outdated notes rather than appending contradictory updates.
5. Preserve unresolved uncertainty instead of converting it into a fact.

Review instruction files when architecture, supported versions, test commands, or CI behavior changes. Remove duplicated guidance and keep one canonical home for each rule. A rule should state its intent and the failure mode it prevents; avoid turning the instruction set into a second copy of the codebase.

## Completion checklist

- [ ] The task has measurable acceptance criteria.
- [ ] Applicable instructions and current source were inspected.
- [ ] Findings distinguish verified facts from inference and unknowns.
- [ ] The diff is limited to the task.
- [ ] Relevant regression tests and documentation are updated.
- [ ] Checks and limitations are reported accurately.
- [ ] Any handoff reflects current evidence and has one clear next action.
