# Kodiak pull request automation

Kodiak is a GitHub App configured by [`.kodiak.toml`](../.kodiak.toml).
After a maintainer adds the `automerge` label, it queues the pull request,
updates its branch when required by branch protection, and squash-merges it
when the required checks and reviews pass. Draft pull requests and merge
conflicts must be resolved before merging.

The [Kodiak workflow](../.github/workflows/kodiak.yml) validates the TOML
configuration against a pinned upstream schema on every pull request, pushes
to `main`, and manual runs. It creates the `automerge` label after successful
validation on `main` if that label is missing. Existing label settings are
preserved. Pull request runs only validate configuration and have read-only
repository access; label creation runs separately with `issues: write`.

## One-time GitHub setup

1. Install or configure the [Kodiak GitHub App](https://github.com/marketplace/kodiakhq)
   and grant it access to `HiDiHo01/Buienalarm`.
2. In the repository's **Settings → Branches**, add a **classic branch
   protection rule** for `main`. Kodiak reads GitHub's `branchProtectionRule`;
   a repository ruleset alone does not provide that configuration.
3. Require pull requests and enable **Require status checks to pass before
   merging**. At minimum, select these exact check names after they have run:

   | Required check | Purpose |
   | --- | --- |
   | `build (3.14.2)` | Home Assistant configuration, tests, and package build |
   | `Validate` | HACS and Hassfest validation |
   | `Validate Kodiak configuration` | Kodiak configuration schema validation |

   Keep any other required checks and review requirements already configured.
   Enable **Require branches to be up to date before merging** so Kodiak can
   update queued pull requests before merging them.
4. Keep squash merging enabled in **Settings → General → Pull Requests**.
5. Merge the configuration pull request after review. Confirm the workflow on
   `main` succeeds and creates the `automerge` label before using that label.

These repository settings and the GitHub App installation are prerequisites;
the validation workflow does not create branch protection or install Kodiak.
As inspected on 2026-10-24, the active repository ruleset prevents deletion and
force-pushes and enables Copilot reviews, but does not require CI checks.
Complete the classic protection setup before enabling Kodiak merges.

## Maintainer workflow

1. Finish the code review and address actionable findings.
2. Confirm the pull request is ready for review and has no merge conflicts.
3. Add `automerge` to authorize Kodiak to merge that pull request after branch
   protection requirements pass. Remove it to withdraw that authorization.
4. Check the `kodiakhq: status` check for queue progress or a specific blocker.

Kodiak does not automatically approve pull requests or delete branches with
this configuration. The existing Dependabot minor/patch auto-merge workflow
continues to use GitHub's native auto-merge; Kodiak leaves Dependabot branch
updates to Dependabot. No automatic dependency-merge policy is added here.

If Kodiak reports `missing branch protection for baseRef: 'main'`, check the
classic rule and its branch pattern. A green configuration workflow proves
schema validity; successful live merges still require the app and branch
protection setup above.

## Configuration maintenance

The schema URL pins Kodiak revision
`4aff5fcd5d6446eb273e21ed0a6c6037243a240b`, and the workflow pins
`check-jsonschema` to `0.38.2`. Review upstream configuration changes before
updating those pins. The upstream schema checks types and supported merge
methods; Kodiak also performs its own runtime validation.

References:

- [Kodiak quick start](https://kodiakhq.com/docs/quickstart)
- [Kodiak configuration reference](https://kodiakhq.com/docs/config-reference)
- [Kodiak branch protection query](https://github.com/chdsbd/kodiak/blob/4aff5fcd5d6446eb273e21ed0a6c6037243a240b/bot/kodiak/queries/__init__.py)
