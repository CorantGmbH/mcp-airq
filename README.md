# mcp-airq

![MCP](https://img.shields.io/badge/MCP-compatible-purple)
[![PyPI](https://img.shields.io/pypi/v/mcp-airq)](https://pypi.org/project/mcp-airq/)
[![Total Downloads](https://img.shields.io/pepy/dt/mcp-airq)](https://pepy.tech/project/mcp-airq)
[![Python](https://img.shields.io/pypi/pyversions/mcp-airq)](https://pypi.org/project/mcp-airq/)
[![License](https://img.shields.io/pypi/l/mcp-airq)](LICENSE)
[![Tests](https://github.com/CorantGmbH/mcp-airq/actions/workflows/tests.yml/badge.svg)](https://github.com/CorantGmbH/mcp-airq/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/CorantGmbH/mcp-airq/branch/main/graph/badge.svg)](https://codecov.io/gh/CorantGmbH/mcp-airq)

MCP server for [air-Q](https://www.air-q.com) air quality sensor devices. Enables Claude Desktop, Claude Code, and other MCP clients to directly query and configure air-Q devices on your local network.

Built on [aioairq](https://pypi.org/project/aioairq/), the official async Python library for air-Q.

The same `mcp-airq` executable also works as a direct CLI when you pass a tool
name as a subcommand.

<!-- mcp-name: io.github.CorantGmbH/mcp-airq -->

## Installation

```bash
pip install mcp-airq
```

Or run directly with [uvx](https://docs.astral.sh/uv/):

```bash
uvx mcp-airq
```

## CLI Usage

Use the same command directly from the shell:

```bash
mcp-airq list-devices
mcp-airq get-air-quality --device "Living Room"
mcp-airq get-air-quality-history --device "Living Room" --last-hours 12 --sensors co2
mcp-airq plot-air-quality-history --sensor co2 --device "Living Room" --output-format svg
mcp-airq export-air-quality-history --sensor co2 --device "Living Room" --output-format xlsx
mcp-airq set-night-mode --activated --device "Bedroom"
```

The CLI subcommands mirror the MCP tool names. Both styles work:

```bash
mcp-airq list-devices
mcp-airq list_devices
```

To force MCP server mode from an interactive terminal, run:

```bash
mcp-airq serve
```

The CLI is pipe-friendly: successful command output goes to `stdout`, while
tool errors go to `stderr` with exit code `1`.

```bash
mcp-airq get-air-quality --device "Living Room" | jq '.co2'
mcp-airq get-air-quality --device "Living Room" --compact-json | jq '.co2'
mcp-airq get-air-quality --device "Living Room" --yaml | yq '.co2'
```

## Device Configuration

Create a JSON file with your device(s), e.g. `~/.config/airq-devices.json`:

```json
[
  {"address": "192.168.4.1", "password": "your_password", "name": "air-Q Pro", "location": "Living Room", "group": "Home"},
  {"address": "192.168.4.2", "password": "your_password", "name": "air-Q Radon", "location": "Living Room", "group": "Home"},
  {"address": "office_air-q.local", "password": "other_pass", "name": "Office", "group": "Work"}
]
```

Each entry requires:
- `address` — IP address or mDNS hostname (e.g. `abcde_air-q.local`)
- `password` — Device password (default: `airqsetup`)
- `name` (optional) — Human-readable name; defaults to address
- `location` (optional) — Physical room/area for grouping (e.g. `"Living Room"`)
- `group` (optional) — Second grouping dimension, orthogonal to location (e.g. `"Home"`, `"Work"`)

Then restrict access to the file (it contains passwords):

```bash
chmod 600 ~/.config/airq-devices.json
```

Alternatively, pass the device list inline via the `AIRQ_DEVICES` environment variable as a JSON string.

## Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "airq": {
      "command": "uvx",
      "args": ["mcp-airq"],
      "env": {
        "AIRQ_CONFIG_FILE": "/home/you/.config/airq-devices.json"
      }
    }
  }
}
```

## Claude Code

Register the server once via the CLI:

```bash
claude mcp add airq -e AIRQ_CONFIG_FILE=~/.config/airq-devices.json -- uvx mcp-airq
```

This writes to `~/.claude/settings.json` and is automatically picked up by the **Claude Code VSCode extension** as well — no separate configuration needed.

> **If the server fails to connect:** MCP servers run in a subprocess that may not inherit your shell's PATH. Replace `uvx` with its full path (`which uvx` → e.g. `/home/you/.local/bin/uvx`):
>
> ```bash
> claude mcp add airq -e AIRQ_CONFIG_FILE=~/.config/airq-devices.json -- /home/you/.local/bin/uvx mcp-airq
> ```

## OpenAI Codex

Register the server once via the CLI:

```bash
codex mcp add airq --env AIRQ_CONFIG_FILE=~/.config/airq-devices.json -- uvx mcp-airq
```

This writes to `~/.codex/config.toml` and is automatically picked up by the **Codex VSCode extension** as well.

> **If the server fails to connect:** Use the full path to `uvx` (see note above).

## Available Tools

### Read-Only

| Tool                      | Description                                                          |
| ------------------------- | -------------------------------------------------------------------- |
| `list_devices`            | List all configured air-Q devices (with location/group if set)       |
| `get_air_quality`         | Get sensor readings — by `device`, `location`, or `group`            |
| `get_air_quality_history` | Get historical sensor data as column-oriented JSON                    |
| `plot_air_quality_history` | Render historical charts as `png`, `webp`, `svg`, or `html`         |
| `export_air_quality_history` | Export one historical sensor as `csv` or `xlsx`                   |
| `get_device_info`         | Get device metadata (name, model, firmware version)                  |
| `get_config`              | Get full device configuration                                        |
| `get_logs`                | Get device log entries                                               |
| `identify_device`         | Make device blink its LEDs for visual identification                 |
| `get_led_theme`           | Get current LED visualization theme                                  |
| `get_possible_led_themes` | List all available LED visualization themes                          |
| `get_night_mode`          | Get current night mode configuration                                 |
| `get_brightness_config`   | Get current LED brightness configuration                             |

### Configuration

| Tool                | Description                                             |
| ------------------- | ------------------------------------------------------- |
| `set_device_name`   | Rename a device                                         |
| `set_led_theme`     | Change LED visualization (CO₂, VOC, Humidity, PM2.5, …) |
| `set_night_mode`    | Configure night mode schedule and settings              |
| `set_brightness`    | Adjust LED brightness (day/night)                       |
| `configure_network` | Set static IP or switch to DHCP                         |

### Device Control

| Tool              | Description                                    |
| ----------------- | ---------------------------------------------- |
| `restart_device`  | Restart the device (~30s downtime)             |
| `shutdown_device` | Shut down the device (manual restart required) |

## Multi-Device Support

When multiple devices are configured, specify which device to query:

- By exact name: `"air-Q Pro"`
- By partial match (case-insensitive): `"pro"`, `"radon"`

If only one device is configured, it is selected automatically.

### Location and Group Queries

`get_air_quality` accepts two optional grouping parameters:

- **`location`** — query all devices in the same room (e.g. `"Living Room"`)
- **`group`** — query all devices sharing a group tag (e.g. `"Home"`)

Both are independent: a device can have a location, a group, both, or neither.
Matching is case-insensitive and substring-based.

```text
get_air_quality(location="Living Room")  → air-Q Pro + air-Q Radon
get_air_quality(group="Home")            → air-Q Pro + air-Q Radon + …
get_air_quality(device="air-Q Radon")   → just that one device
```

Exactly one of `device`, `location`, or `group` may be specified per call.

## Example Prompts

- *"How is the air quality in the living room?"* — queries all devices at that location
- *"What's the air quality at home?"* — queries all devices in the "Home" group
- *"Show the CO₂ trend over the last 12 hours as SVG"*
- *"Export the radon history from yesterday as Excel"*
- *"Show me the radon level"* — targets the air-Q Radon device by name
- *"Show CO₂ on the LEDs"*
- *"Enable night mode from 10 PM to 7 AM"*
- *"Set brightness to 50%"*
- *"What's in the device log?"*
- *"Make the air-Q blink"*

## Development

```bash
git clone https://github.com/CorantGmbH/mcp-airq.git
cd mcp-airq
uv sync --frozen --extra dev
uv run pre-commit install
uv run pytest
```

The repository uses a project-local `.venv` plus `uv.lock` for reproducible tooling.
Run all developer commands through `uv run`, for example:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pre-commit run --all-files
```

## Release Process

1. Update `version` in `pyproject.toml`.
2. Commit and create a matching Git tag like `v0.1.1`.
3. Publish a GitHub Release from that tag.

The publish workflow validates that the release tag matches `pyproject.toml`, uploads the package to PyPI, and then publishes the same version to the MCP Registry.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
