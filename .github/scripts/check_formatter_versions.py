"""Reject drift between the pinned formatter, its lockfile and CI installation."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import re
import sys
import tomllib


def verify_formatter_versions(
    project_path: Path, lock_path: Path, installed_version: str
) -> str:
    """Return the Ruff version when every formatter source agrees."""
    project = tomllib.loads(project_path.read_text(encoding="utf-8"))
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    try:
        dependency_version = project["tool"]["poetry"]["group"]["dev"]["dependencies"][
            "ruff"
        ]
        required_version = project["tool"]["ruff"]["required-version"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "Configure both the Ruff development dependency and required-version"
        ) from error
    if (
        not isinstance(dependency_version, str)
        or re.fullmatch(r"\d+\.\d+\.\d+", dependency_version) is None
    ):
        raise ValueError(
            "The Ruff development dependency must be an exact stable version"
        )
    if required_version != f"=={dependency_version}":
        raise ValueError(
            "Ruff required-version must match the exact development dependency"
        )
    locked_versions = [
        package.get("version")
        for package in lock.get("package", [])
        if isinstance(package, dict) and package.get("name") == "ruff"
    ]
    if locked_versions != [dependency_version]:
        raise ValueError(
            "The Ruff lockfile version must match the development dependency"
        )
    if installed_version != dependency_version:
        raise ValueError(
            "The installed Ruff version must match the development dependency"
        )
    return dependency_version


def main() -> int:
    """Validate the checkout's configuration against the installed formatter."""
    repository_root = Path(__file__).resolve().parents[2]
    try:
        verified_version = verify_formatter_versions(
            repository_root / "pyproject.toml",
            repository_root / "poetry.lock",
            version("ruff"),
        )
    except (OSError, ValueError, PackageNotFoundError) as error:
        print(f"Formatter version check failed: {error}", file=sys.stderr)
        return 1
    print(f"Formatter versions agree: Ruff {verified_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
