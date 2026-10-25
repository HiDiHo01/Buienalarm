/** Verify the merge policy using the exact Renovate engine used by the workflow. */
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

const validator_root = process.env.RENOVATE_VALIDATOR_ROOT;
assert.ok(validator_root, "Set RENOVATE_VALIDATOR_ROOT to the installed Renovate package.");
const { init: init_logger } = await import(
  pathToFileURL(path.join(validator_root, "dist/logger/index.js"))
);
await init_logger();
// These matchers are pinned with Renovate; upgrades must retain these contracts.
const { applyPackageRules: apply_package_rules } = await import(
  pathToFileURL(path.join(validator_root, "dist/util/package-rules/index.js"))
);
const { isScheduledNow: is_scheduled_now } = await import(
  pathToFileURL(path.join(validator_root, "dist/workers/repository/update/branch/schedule.js"))
);
const repository_config = JSON.parse(await readFile("renovate.json", "utf8"));
const renovate_require = createRequire(path.join(validator_root, "package.json"));
const { parse: parse_yaml } = renovate_require("yaml");
const workflow = parse_yaml(await readFile(".github/workflows/renovate.yml", "utf8"));
const protection_guard = workflow.jobs.renovate.steps.find(
  (step) => step.name === "Require CI protection before dependency changes"
).run;

const dependency_cases = [
  ["black patch", "poetry", "black", "26.1.0", "patch", true],
  ["pytest minor", "poetry", "pytest", "9.0.0", "minor", true],
  ["tool major", "poetry", "pytest", "9.0.0", "major", false],
  ["pre-1.0 tool", "poetry", "black", "0.9.0", "minor", false],
  ["runtime patch", "poetry", "homeassistant", "2026.10.1", "patch", false],
  ["test baseline patch", "poetry", "pytest-homeassistant-custom-component", "0.13.372", "patch", false],
  ["unlisted dependency", "poetry", "aiohttp", "3.14.4", "patch", false],
  ["action minor", "github-actions", "actions/checkout", "7.0.1", "minor", true],
  ["action major", "github-actions", "actions/checkout", "7.0.1", "major", false],
  ["action digest", "github-actions", "actions/checkout", "7.0.1", "digest", true],
  ["unversioned action digest", "github-actions", "hacs/action", "main", "digest", false],
  ["immutable pin", "github-actions", "hacs/action", "1.0.0", "pinDigest", true],
  ["Python patch", "pyenv", "python", "3.14.2", "patch", false],
  ["runner patch", "regex", "renovate", "44.181.5", "patch", false],
  ["lock refresh", "poetry", "black", "26.1.0", "lockFileMaintenance", false],
  ["dependency rollback", "poetry", "black", "26.1.0", "rollback", false]
];

for (const [description, manager, package_name, current_version, update_type, expected] of dependency_cases) {
  test(description, async () => {
    const result = await apply_package_rules({
      ...repository_config,
      manager,
      depName: package_name,
      packageName: package_name,
      currentVersion: current_version,
      currentValue: current_version,
      versioning: manager === "poetry" ? "pep440" : "semver",
      updateType: update_type
    });
    assert.equal(result.automerge, expected);
    assert.equal(result.platformAutomerge, false);
    assert.equal(result.ignoreTests, false);
  });
}

const schedule_cases = [
  ["summer Monday before window", "2026-07-06T00:59:00Z", false],
  ["summer Monday start", "2026-07-06T01:00:00Z", true],
  ["summer Monday end", "2026-07-06T04:00:00Z", false],
  ["winter Monday start", "2026-10-26T02:00:00Z", true],
  ["winter Monday last minute", "2026-10-26T04:59:00Z", true],
  ["winter Monday end", "2026-10-26T05:00:00Z", false],
  ["Thursday after clock change", "2026-10-29T03:17:00Z", true],
  ["Tuesday outside maintenance days", "2026-10-27T03:17:00Z", false],
  ["Sunday clock change", "2026-10-25T02:17:00Z", false]
];

for (const [description, instant, expected] of schedule_cases) {
  test(description, (context) => {
    context.mock.method(Date, "now", () => Date.parse(instant));
    assert.equal(is_scheduled_now(repository_config), expected);
    assert.equal(is_scheduled_now(repository_config, "automergeSchedule"), expected);
  });
}

for (const package_name of ["homeassistant", "pytest-homeassistant-custom-component"]) {
  test(`${package_name} baseline updates on an ordinary Tuesday`, async (context) => {
    context.mock.method(Date, "now", () => Date.parse("2026-10-27T03:17:00Z"));
    const result = await apply_package_rules({
      ...repository_config,
      manager: "poetry",
      depName: package_name,
      packageName: package_name,
      currentVersion: package_name === "homeassistant" ? "2026.10.4" : "0.13.374",
      versioning: "pep440",
      updateType: "patch"
    });
    assert.equal(is_scheduled_now(result), true);
    assert.equal(is_scheduled_now(repository_config), false);
    assert.equal(result.rangeStrategy, "update-lockfile");
    assert.equal(result.groupName, "Home Assistant test baseline");
    assert.equal(result.automerge, false);
    assert.equal(result.ignoreUnstable, true);
  });
}

const required_checks = ["build (3.14.2)", "Validate", "Validate Renovate configuration"];
const protection_rule = {
  ruleset_id: 123,
  type: "required_status_checks",
  parameters: {
    strict_required_status_checks_policy: true,
    required_status_checks: required_checks.map((context) => ({ context, integration_id: 15368 }))
  }
};
const protection_cases = [
  ["required CI protection", [protection_rule], 0, true],
  ["missing CI protection", [], 0, false],
  ["missing required check", [{
    ...protection_rule,
    parameters: {
      ...protection_rule.parameters,
      required_status_checks: [{ context: "Validate Renovate configuration" }]
    }
  }], 0, false],
  ["branches need not be current", [{
    ...protection_rule,
    parameters: { ...protection_rule.parameters, strict_required_status_checks_policy: false }
  }], 0, false],
  ["unrestricted check source", [{
    ...protection_rule,
    parameters: {
      ...protection_rule.parameters,
      required_status_checks: required_checks.map((context) => ({ context }))
    }
  }], 0, false],
  ["incorrect check source", [{
    ...protection_rule,
    parameters: {
      ...protection_rule.parameters,
      required_status_checks: required_checks.map((context) => ({ context, integration_id: 999 }))
    }
  }], 0, false],
  ["GitHub rules API failure", [protection_rule], 1, false],
  ["malformed GitHub rules response", null, 0, false],
  ["App can bypass required CI", [protection_rule], 0, false, {
    enforcement: "active", current_user_can_bypass: "always"
  }],
  ["App can bypass through PRs", [protection_rule], 0, false, {
    enforcement: "active", current_user_can_bypass: "pull_requests_only"
  }],
  ["App exempt from CI", [protection_rule], 0, false, {
    enforcement: "active", current_user_can_bypass: "exempt"
  }],
  ["caller bypass status not visible", [protection_rule], 0, false, { enforcement: "active" }],
  ["ruleset disabled after initial response", [protection_rule], 0, false, {
    enforcement: "disabled", current_user_can_bypass: "never"
  }]
];

for (const [description, rules, api_status, expected, ruleset = {
  enforcement: "active", current_user_can_bypass: "never"
}] of protection_cases) {
  test(description, () => {
    const result = spawnSync("/bin/bash", ["-c", String.raw`
      gh() {
        if [[ "$2" == */rulesets/* ]]; then
          printf '%s\n' "$RENOVATE_TEST_RULESET"
        else
          printf '%s\n' "$RENOVATE_TEST_RULES"
        fi
        return "$RENOVATE_TEST_API_STATUS"
      }
      ${protection_guard}
    `], {
      env: {
        PATH: "/usr/bin:/bin",
        GH_REPO: "test/repository",
        RENOVATE_TEST_RULES: JSON.stringify(rules),
        RENOVATE_TEST_RULESET: JSON.stringify(ruleset),
        RENOVATE_TEST_API_STATUS: api_status === 0 ? "0" : "1"
      },
      encoding: "utf8"
    });
    assert.equal(result.status === 0, expected, result.error?.message ?? result.stderr);
  });
}

test("App job uses a protected environment", () => {
  assert.equal(workflow.jobs.renovate.environment, "renovate");
  assert.equal(workflow.jobs.validate.environment, undefined);
});

test("App token repository comes from the stable repository context", () => {
  const repository_step = workflow.jobs.renovate.steps.find((step) => step.id === "repository");
  const token_step = workflow.jobs.renovate.steps.find((step) => step.id === "app-token");
  assert.equal(repository_step.env.REPOSITORY, "${{ github.repository }}");
  assert.equal(token_step.with.repositories, "${{ steps.repository.outputs.name }}");
});
