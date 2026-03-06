# mcp-airq

[![PyPI](https://img.shields.io/pypi/v/mcp-airq)](https://pypi.org/project/mcp-airq/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-airq)](https://pypi.org/project/mcp-airq/)
[![License](https://img.shields.io/pypi/l/mcp-airq)](LICENSE)
[![Tests](https://github.com/CorantGmbH/mcp-airq/actions/workflows/tests.yml/badge.svg)](https://github.com/CorantGmbH/mcp-airq/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/CorantGmbH/mcp-airq/branch/main/graph/badge.svg)](https://codecov.io/gh/CorantGmbH/mcp-airq)

MCP server for [air-Q](https://www.air-q.com) air quality sensor devices. Enables Claude Desktop, Claude Code, and other MCP clients to directly query and configure air-Q devices on your local network.

Built on [aioairq](https://pypi.org/project/aioairq/), the official async Python library for air-Q.

## Installation

```bash
pip install mcp-airq
```

Or run directly with [uvx](https://docs.astral.sh/uv/):

```bash
uvx mcp-airq
```

## Configuration

Configure your air-Q devices via the `AIRQ_DEVICES` environment variable (JSON array):

```json
[
  {"address": "192.168.4.1", "password": "your_password", "name": "Living Room"},
  {"address": "office_air-q.local", "password": "other_pass", "name": "Office"}
]
```

Or point to a JSON file:

```bash
export AIRQ_CONFIG_FILE=/path/to/devices.json
```

Each device entry requires:
- `address` — IP address or mDNS hostname (e.g. `abcde_air-q.local`)
- `password` — Device password (default: `airqsetup`)
- `name` (optional) — Human-readable name; defaults to address

## Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "airq": {
      "command": "uvx",
      "args": ["mcp-airq"],
      "env": {
        "AIRQ_DEVICES": "[{\"address\": \"192.168.4.1\", \"password\": \"airqsetup\", \"name\": \"Living Room\"}]"
      }
    }
  }
}
```

## Claude Code

```bash
claude mcp add airq -- uvx mcp-airq
```

Then set the `AIRQ_DEVICES` environment variable before launching Claude Code.

## Available Tools

### Read-Only

| Tool              | Description                                                          |
| ----------------- | -------------------------------------------------------------------- |
| `list_devices`    | List all configured air-Q devices                                    |
| `get_air_quality` | Get current sensor readings (temperature, CO₂, humidity, PM, VOC, …) |
| `get_device_info` | Get device metadata (name, model, firmware version)                  |
| `get_config`      | Get full device configuration                                        |
| `get_logs`        | Get device log entries                                               |
| `identify_device` | Make device blink its LEDs for visual identification                 |

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

- By exact name: `"Living Room"`
- By partial match (case-insensitive): `"living"`, `"office"`

If only one device is configured, it is selected automatically.

## Example Prompts

- *"How is the air quality in the living room?"*
- *"Show CO₂ on the LEDs"*
- *"Enable night mode from 10 PM to 7 AM"*
- *"Set brightness to 50%"*
- *"What's in the device log?"*
- *"Make the air-Q blink"*

## Development

```bash
git clone https://github.com/CorantGmbH/mcp-airq.git
cd mcp-airq
pip install -e ".[dev]"
pytest
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
