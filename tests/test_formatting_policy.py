"""Verify formatter consistency and the production CI/commit formatting path."""

from pathlib import Path
import runpy
import tomllib

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_VERIFY_VERSIONS = runpy.run_path(
    str(_ROOT / ".github/scripts/check_formatter_versions.py")
)["verify_formatter_versions"]


@pytest.mark.parametrize(
    ("dependency", "required", "locked", "installed", "message"),
    [
        ("^0.16.9", "==0.16.9", "0.16.9", "0.16.9", "exact stable version"),
        ("0.16.9", "==0.16.8", "0.16.9", "0.16.9", "required-version"),
        ("0.16.9", "==0.16.9", "0.16.8", "0.16.9", "lockfile version"),
        ("0.16.9", "==0.16.9", "0.16.9", "0.16.8", "installed Ruff version"),
    ],
)
def test_formatter_version_drift_is_rejected(
    tmp_path: Path,
    dependency: str,
    required: str,
    locked: str,
    installed: str,
    message: str,
) -> None:
    """Independent dependency, configuration, lock and installed updates fail."""
    project_path = tmp_path / "pyproject.toml"
    project_path.write_text(
        f'[tool.poetry.group.dev.dependencies]\nruff = "{dependency}"\n'
        f'[tool.ruff]\nrequired-version = "{required}"\n',
        encoding="utf-8",
    )
    lock_path = tmp_path / "poetry.lock"
    lock_path.write_text(
        f'[[package]]\nname = "ruff"\nversion = "{locked}"\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match=message):
        _VERIFY_VERSIONS(project_path, lock_path, installed)


def test_repository_formatter_and_hooks_use_the_same_environment() -> None:
    """The checked-in formatter pins and both commit hooks use locked Poetry."""
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pinned_version = project["tool"]["poetry"]["group"]["dev"]["dependencies"]["ruff"]
    assert (
        _VERIFY_VERSIONS(
            _ROOT / "pyproject.toml", _ROOT / "poetry.lock", pinned_version
        )
        == pinned_version
    )
    hooks = yaml.safe_load(
        (_ROOT / "pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    local_hooks = {
        hook["id"]: hook
        for repository in hooks["repos"]
        if repository["repo"] == "local"
        for hook in repository["hooks"]
    }
    assert (
        local_hooks["ruff-check"]["entry"] == "poetry run ruff check --select I --fix"
    )
    assert local_hooks["ruff-format"]["entry"] == "poetry run ruff format"
    assert all("isort" not in repository["repo"] for repository in hooks["repos"])


def test_formatter_patch_uses_immutable_pr_head() -> None:
    """Corrective patches are based on the contributor's head, not the merge ref."""
    workflow = yaml.safe_load(
        (_ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")
    )
    formatting_steps = workflow["jobs"]["ruff"]["steps"]
    checkout = formatting_steps[0]
    assert (
        checkout["with"]["ref"]
        == "${{ github.event.pull_request.head.sha || github.sha }}"
    )
    assert checkout["with"]["persist-credentials"] is False
    assert workflow["permissions"] == {"contents": "read"}
