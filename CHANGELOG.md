# Changelog

## [1.5.0] - 2026-03-14

### Added

- The existing `mcp-airq` executable now also works as a direct CLI: every MCP
  tool is available as a terminal subcommand, using either hyphenated command
  names (for example `list-devices`) or the original MCP tool names
  (`list_devices`).
- Added an explicit `mcp-airq serve` command to force stdio MCP server mode
  from an interactive terminal.

### Changed

- CLI output is now shell-pipeline friendly: successful data stays on `stdout`,
  runtime errors go to `stderr`, and command failures return exit code `1`.
- Added `--compact-json`, `--json`, and `--yaml` output modes for direct CLI
  usage, making it easy to chain `mcp-airq` with tools like `jq` or `yq`.

## [1.3.1] - 2026-03-13

### Changed

- Development workflow now uses a project-local `.venv` plus `uv.lock` for
  reproducible environments instead of machine-specific Python/PATH setups.
- Replaced `pylint` and `black` in local validation with `ruff check` and
  `ruff format`, and aligned pre-commit plus CI with the same `uv run`-based
  commands.
- `pyright` now resolves imports from the repo-local `.venv` instead of
  absolute user-specific paths.

## [1.3.0] - 2026-03-13

### Changed

- All sensor keys in `get_air_quality` and `get_air_quality_history` output are
  now normalized to lowercase (e.g. `TypPS` → `typps`, `DeviceID` → `deviceid`,
  `ch2o_M10` → `ch2o_m10`). This aligns the local MCP server output with the
  air-Q Cloud API, which already uses lowercase keys.
- Sensor guide display names updated to lowercase accordingly.

## [1.2.1] - 2026-03-13

### Changed

- `get_air_quality_history` now always returns column-oriented JSON (no `compact`
  parameter). Response always includes `_sensor_guide`. Timestamps are returned
  as Unix seconds (divided by 1000) instead of milliseconds, saving tokens for
  long time ranges.
- Improved `get_air_quality_history` docstring: `sensors` parameter is now
  clearly documented as a JSON array — not a string — with correct/incorrect
  usage examples to prevent mis-use by LLMs.

## [1.2.0] - 2026-03-12

### Added

- New `get_air_quality_history` tool: retrieves historical air quality data
  stored on the device's SD card. Accepts the same time-range interface as the
  Cloud MCP (`last_hours`, `from_datetime`/`to_datetime`, `sensors`,
  `max_points`). Internally navigates the device's year/month/day file
  hierarchy, downloads matching files (compressed via `/file_zlib` when
  available), and filters/downsamples the results. Requires aioairq ≥ 0.5.0.
- Bumped minimum `aioairq` version to `>=0.5.0` (adds
  `get_historical_files_list` and `get_historical_file` API).

## [1.1.6] - 2026-03-10

### Changed

- Pinned minimum `aiohttp` version to `>=3.13.3` (latest release) to ensure
  all known aiohttp CVEs are resolved for fresh installs.

## [1.1.5] - 2026-03-10

### Changed

- Raised minimum dependency versions to `mcp>=1.26.0` and `aiohttp>=3.13.0`,
  eliminating 3 high-severity CVEs in the MCP SDK and 5 aiohttp CVEs.
- Added `[project.urls]` to `pyproject.toml` (Homepage, Repository, Issues,
  Changelog), enabling source-code verification from the PyPI package page.

### Improved

- `@handle_airq_errors` decorator now logs each caught exception with an
  appropriate log level (`debug`, `warning`, or `error` with full traceback)
  instead of silently discarding exception details.
- Config file path is checked for world-readable permissions at startup; a
  `WARNING` with a `chmod 600` hint is logged if group or other read bits are set.

## [1.1.4] - 2026-03-09

### Changed

- `get_air_quality` now embeds a `_sensor_guide` filtered to only the sensors
  present in the device response. Descriptions for sensors not reported by the
  device are omitted, significantly reducing response size (up to ~90 % for
  typical devices). The full guide is still available via the
  `airq_sensor_guide` prompt.
- Sensor guide data restructured from a static string into a typed, structured
  list in `guides.py`. `build_sensor_guide(data_keys)` generates the filtered
  Markdown guide; `SENSOR_GUIDE` (used by prompts) is derived from the same
  source.

## [1.1.3] - 2026-03-07

### Changed

- Help text now shows the version number in the header line.
- Replaced the confusing nested-JSON example in the help text with a clean
  separate example for `AIRQ_DEVICES` to avoid unreadable `\"` escapes.
- Improved test coverage from 89% to 99%.

## [1.1.2] - 2026-03-07

### Fixed

- Increased `aiohttp.ClientSession` timeout to 30 s total / 15 s connect (was
  aiohttp's built-in default of 5 s connect). Devices with high latency or slow
  mDNS resolution are now reliably reachable.

## [1.1.1] - 2026-03-07

### Added

- `mcp-airq --version` prints the installed version and exits.
- `mcp-airq --help` (and `mcp-airq` called from an interactive terminal)
  prints a human-readable description of the server, explains that it is
  designed to be launched by an MCP client, and shows how to add it to
  Claude Desktop and Claude Code.

## [1.1.0] - 2026-03-07

### Added

- **Location support**: Device configs now accept an optional `location` field
  to group devices by physical location (e.g. `"location": "Wohnzimmer"`).
- **Group support**: Device configs now accept an optional `group` field for
  a second, orthogonal grouping dimension (e.g. `"group": "zu Hause"`). A device
  can have both a location and a group independently.
- `list_devices` includes `location` and `group` for each device when configured.
- `get_air_quality` accepts `location` and `group` parameters to query all devices
  in a given location or group at once, returning sensor data keyed by device name.
  Exactly one of `device`, `location`, or `group` may be specified per call.
- `DeviceManager.resolve_location()` and `resolve_group()` resolve by
  case-insensitive substring matching across the respective field.

### Internal

- `DeviceManager._resolve_by()` private helper eliminates duplication between
  location and group resolution.

## [1.0.2] - 2026-03-07

### Fixed

- `get_air_quality` and `get_config` now embed the full sensor/config guide
  directly in every response (`_sensor_guide` / `_config_guide` fields) instead
  of a short `_note` pointing to the prompt. This guarantees correct
  interpretation of units and index semantics (e.g. `mold` is a mold-FREE index,
  `tvoc` is in ppb) regardless of whether the client invokes the prompt.

### Refactored

- Extracted guide strings from `prompts.py` into a new `guides.py` module
  (`SENSOR_GUIDE`, `CONFIG_GUIDE`). Both `prompts.py` and `tools/read.py`
  import from there, keeping the content in one place.

## [1.0.1] - 2026-03-07

### Fixed

- `get_air_quality`: Sensor index semantics are now embedded directly in the
  tool description and in every response via a `_note` field, ensuring that
  `mold` and `virus` (both "free" indices where 100 % = best) and
  `health`/`performance` (0–1000, higher = better) are always interpreted
  correctly regardless of whether the `airq_sensor_guide` prompt is invoked.
- `get_config`: Tool description now explicitly references `airq_config_guide`,
  and every response includes a `_note` field pointing to that prompt.

### Developer tooling

- `pyrightconfig.json`: Added `pythonPath` pointing to the micromamba
  environment so pyright resolves `aioairq`, `aiohttp`, and `mcp` correctly.

## [1.0.0] - 2026-03-07

### Prompts

- `airq_sensor_guide` — Explains all sensor keys with their units and value semantics (e.g. `mold` and `virus` are quality indices where 100 % = best, 0 % = worst)
- `airq_config_guide` — Documents all device configuration keys returned by `get_config`, including network, LED/night mode, measurement settings, virtual sensors, and alarms

### Developer tooling

- Added `pre-commit` with black, pylint, pytest, pyright, and standard pre-commit-hooks (same setup as firmware-D)
- Added `pyrightconfig.json` targeting the `src/` layout
- Extended GitHub Actions workflow (`tests.yml`) with pylint and pyright steps on Python 3.11
- Added `pylint`, `black`, `pyright`, and `pytest-xdist` to dev dependencies

## [0.1.0] - 2026-03-06

Initial release.

### Tools

**Read-only**
- `list_devices` — List all configured air-Q devices with names and addresses
- `get_air_quality` — Get current sensor readings (temperature, CO₂, humidity, PM, VOC, …)
- `get_device_info` — Get device metadata (ID, name, model, firmware/hardware version)
- `get_config` — Get full device configuration as JSON
- `get_logs` — Get device log entries
- `identify_device` — Make device blink its LEDs for visual identification
- `get_led_theme` — Get current LED visualization theme
- `get_possible_led_themes` — List all available LED visualization themes
- `get_night_mode` — Get current night mode configuration
- `get_brightness_config` — Get current LED brightness configuration

**Configuration**
- `set_device_name` — Rename a device
- `set_led_theme` — Change LED visualization theme
- `set_night_mode` — Configure night mode schedule and settings
- `set_brightness` — Adjust LED brightness (day/night)
- `configure_network` — Set static IP or switch to DHCP

**Device control**
- `restart_device` — Restart the device (~30s downtime)
- `shutdown_device` — Shut down the device (manual restart required)

### Features
- Multi-device support with case-insensitive substring name matching
- Automatic device selection when only one device is configured
- Shared `aiohttp.ClientSession` across all device connections
- `@handle_airq_errors` decorator catches all aioairq and network exceptions and returns user-friendly strings
- Configuration via `AIRQ_DEVICES` environment variable (JSON) or `AIRQ_CONFIG_FILE`
