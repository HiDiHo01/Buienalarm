# Testing Home Assistant compatibility

The integration's Home Assistant requirement has no upper version limit.
Prereleases are excluded. Python must still satisfy Home Assistant's runtime
requirements; the repository currently supports Python `>=3.14.2,<3.15`.

## Latest stable release

The [latest-stable workflow](../.github/workflows/latest-home-assistant.yml) runs
on every pull request, pushes to `main`, manual dispatches, and daily at 06:43
`Europe/Amsterdam`. It reads the latest stable GitHub release from
`home-assistant/core` and installs that **exact** release in a clean environment.
An incompatible Python baseline or missing dependency fails the check instead
of letting the resolver silently choose an older Home Assistant version.

This environment does not install `pytest-homeassistant-custom-component`.
The standard-library [compatibility tests](../compatibility/test_latest_home_assistant.py)
exercise module imports, custom integration discovery, config-flow validation,
config-entry setup, both entity platforms, and unloading. Weather calls are mocked
and use a real HTTP session without multicast discovery; the Home Assistant
managers and entity lifecycle run normally.
Logs include the installed Home Assistant version and are uploaded on failure.

To run the same check locally after installing the current stable Home Assistant
in a separate virtual environment:

```sh
python -m pip check
python -m unittest discover -s compatibility -v
```

## Full regression suite

The root `poetry.lock` tracks the current stable Home Assistant independently of
test fixtures. The full regression suite has its own Poetry project and lock
file in `test_dependencies/`, so an upstream fixture pin cannot hold back the main environment.
Run the two environments from the repository root:

```sh
poetry install --no-root
poetry --project test_dependencies install --no-root
poetry --project test_dependencies run pytest -vv
```

`pytest-homeassistant-custom-component` generates its fixtures for one exact
Home Assistant release and declares that dependency upstream. Its requirement
and the direct pytest requirement are open-ended here, so newer compatible
fixture releases are allowed. Renovate checks Home Assistant and the helper
together daily and proposes a reviewed lock-file update.

The regression-test lock can temporarily lag a new Home Assistant release while
the helper catches up. The main environment and independent compatibility check
continue to use the latest stable release during that gap. These are different checks:
passing the compatibility check does not mean the full pytest suite ran on that
same Home Assistant version.
