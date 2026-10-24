# Renovate dependency maintenance

Renovate manages Poetry dependencies, `.python-version`, GitHub Actions, and
the pinned Renovate runner. The configuration is split between
[`renovate.json`](../renovate.json), repository policy, and
[`.github/renovate-config.json`](../.github/renovate-config.json), trusted runner
settings. The [workflow](../.github/workflows/renovate.yml) validates both on
every pull request and runs the bot only from `main` on scheduled or manual runs.

## Schedule and merge policy

Branch creation, branch updates, and automatic merges use Monday and Thursday
03:00–06:00 in `Europe/Amsterdam`. GitHub starts the runner at 03:17, 04:17,
and 05:17 on those days using its native timezone setting. Renovate checks the
window again, including on manual runs and when a workflow is delayed.

`platformAutomerge` is disabled so GitHub cannot complete an automatically
queued merge outside `automergeSchedule`. Renovate creates pull requests,
checks CI on an up-to-date branch, and uses squash merges within the window.

| Update | Automatic merge |
| --- | --- |
| Stable `black`, `pylint`, `pytest`, `pytest-asyncio` minor/patch releases | After passing CI and a release age of at least three days |
| Stable GitHub Actions minor/patch releases | After passing CI and a release age of at least three days |
| Stable, versioned GitHub Actions digest changes and immutable digest pins | After passing CI |
| Unversioned or pre-1.0 GitHub Actions | Manual review |
| Home Assistant and its custom-component test plugin | Manual review, grouped together |
| Python 3.14 patch releases | Manual review; other Python series are excluded |
| Renovate runner upgrades | Manual review |
| Major, replacement, rollback, and lock-file maintenance updates | Manual review |

Lock-file maintenance runs on Monday within the same window. Existing Poetry
ranges are retained except the four listed development tools, which bump their
lower bounds so Renovate can target the reviewed version. Poetry's range-based
lock updates have limitations; inspect the resulting lock diff and CI for every
manual baseline or maintenance update.

Minor/patch updates eligible for automerge require a release timestamp for the
three-day age check. An update without a usable timestamp remains blocked.

## One-time GitHub setup

Complete this setup before merging the Renovate pull request, because it hands
scheduled version updates over from Dependabot.

1. Register a dedicated GitHub App and install it only on
   `HiDiHo01/Buienalarm`. This is a self-hosted runner with its own App identity.
   Grant these repository permissions:

   | Permission | Access |
   | --- | --- |
   | Administration | Read |
   | Checks and Commit statuses | Read and write |
   | Contents, Issues, Pull requests, Workflows | Read and write |
   | Metadata | Read, implicit |

2. In **Settings → Secrets and variables → Actions**, add the App's **Client ID**
   as repository variable `RENOVATE_APP_CLIENT_ID`. In **Settings → Environments**,
   create `renovate`, select **Selected branches and tags**, and add only a
   **branch** rule for `main`. Store the generated PEM private key there as the
   environment secret `RENOVATE_APP_PRIVATE_KEY`, rather than a repository or
   organization secret. This prevents a same-repository PR from accessing the key
   by editing the workflow. No manual environment reviewer is needed for scheduled
   runs.
3. Add an active `main` CI ruleset without a bypass for the Renovate App, required
   status checks, and **Require branches to be up to date before merging**. Each required
   check must use **GitHub Actions** as its expected source. A single required-check
   rule must contain at least:
   - `build (3.14.2)`
   - `Validate`
   - `Validate Renovate configuration`

   Keep existing review and check requirements in their current rulesets,
   including Kodiak validation when enabled. Require pull requests before merging.
   The runner verifies the check sources, strict policy, and the App token's
   `current_user_can_bypass: never` result before changing dependencies. It does
   not need access to the full bypass list or permission to edit the ruleset.
   Missing protection or an unavailable caller-bypass status produces a failure.
4. Keep squash merges enabled. After the configuration is merged, use
   **Actions → Renovate → Run workflow** on `main` to verify authentication.
   Manual runs still honor the maintenance and automerge schedules.

The workflow exchanges the App key for a token scoped to this repository and
revokes it when the job ends. The bot job has a 45-minute timeout, within the
installation token's one-hour lifetime. Pull request validation uses no App
credentials. The default `GITHUB_TOKEN` has read-only access; dependency PRs are
created with the App token so their CI can run normally.

The preflight checks the ruleset at startup; it cannot lock an administrator out
of changing repository protection during a run. Keep the CI ruleset enabled.

## Dependabot and Kodiak

Dependabot's `open-pull-requests-limit: 0` disables its ordinary version-update
PRs for the ecosystems Renovate manages. Existing Dependabot security-update
settings and the Dependabot auto-merge workflow remain in effect; security PRs
use GitHub's separate security-update mechanism. Renovate's vulnerability-alert
PRs are disabled to give that security-update path a single owner.

Renovate adds the existing `dependencies` label and uses `renovate-actions/`
branches. It does not add Kodiak's `automerge` label. Let Renovate handle its
eligible merges so the maintenance window and package rules stay effective;
manually adding another merge bot's label delegates that decision to that bot.

## Validation and maintenance

The workflow runs the pinned official `renovate-config-validator` in strict
mode, then executes merge-policy and daylight-saving schedule tests against
that same Renovate version. Updating `RENOVATE_VERSION` updates both validation
and the runner; the built-in `customManagers:githubActionsVersions` preset
opens a reviewable PR for that pin. Review the Node.js requirement on upgrades.

Runtime authentication, registry access, actual update PR creation, and live
merges must be checked after the App and ruleset setup. Configuration validation
alone does not prove those external capabilities work.

References:

- [Renovate GitHub Action](https://github.com/renovatebot/github-action)
- [GitHub App permissions for Renovate](https://docs.renovatebot.com/modules/platform/github/#running-as-a-github-app)
- [GitHub environment branch restrictions and secrets](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Renovate scheduling](https://docs.renovatebot.com/key-concepts/scheduling/)
- [Renovate automerge configuration](https://docs.renovatebot.com/key-concepts/automerge/)
- [Dependabot security-only configuration](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/customizing-dependabot-security-prs)
