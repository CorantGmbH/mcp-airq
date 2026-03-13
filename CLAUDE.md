# CLAUDE.md

## Project Overview

MCP (Model Context Protocol) server for [air-Q](https://www.air-q.com) air quality sensor devices. Enables Claude Desktop, Claude Code, and other MCP clients to query and configure air-Q devices on the local network.

Built as a thin tool layer on top of [aioairq](https://pypi.org/project/aioairq/) (the official async Python library for air-Q).

## Architecture

```
Claude Desktop/Code/Web
    └── MCP Client (JSON-RPC 2.0 over STDIO)
            └── mcp-airq (this project)
                    └── aioairq → air-Q device(s) via HTTP + AES-256
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `server.py` | FastMCP instance, lifespan (aiohttp session), entry point |
| `config.py` | Loads device config from `AIRQ_DEVICES` env var or `AIRQ_CONFIG_FILE` |
| `devices.py` | `DeviceManager`: caches `AirQ` instances, resolves device names (substring match) |
| `errors.py` | `@handle_airq_errors` decorator — catches aioairq exceptions, returns readable strings |
| `tools/_helpers.py` | Shared helpers: `_manager()`, `_resolve()`, `_json()` |
| `tools/read.py` | 11 read-only tools (list_devices, get_air_quality, get_air_quality_history, get_device_info, get_config, get_logs, identify_device, get_led_theme, get_possible_led_themes, get_night_mode, get_brightness_config) |
| `tools/write.py` | 5 write tools (set_device_name, set_led_theme, set_night_mode, set_brightness, configure_network) |
| `tools/dangerous.py` | 2 destructive tools (restart_device, shutdown_device) |

### Design Patterns

- **Lifespan**: `aiohttp.ClientSession` is created/closed in `app_lifespan()`. The `DeviceManager` is yielded as the lifespan context and accessed in tools via `ctx.request_context.lifespan_context`.
- **Error handling**: The `@handle_airq_errors` decorator wraps all tool functions. It catches `InvalidAuth`, `APIAccessDenied`, `ClientError`, `TimeoutError` and returns user-friendly strings instead of crashing the MCP session.
- **ToolAnnotations**: Every tool is annotated with `readOnlyHint`, `destructiveHint`, and `idempotentHint` for correct client behavior.
- **Multi-device**: Each tool has an optional `device: str | None` parameter. Single-device setups auto-resolve; multi-device uses case-insensitive substring matching.

## Commands

```bash
# Create/update the project environment
uv sync --frozen --extra dev

# Run tests
uv run pytest

# Install and run commit hooks
uv run pre-commit install
uv run pre-commit run --all-files

# Run the server (STDIO transport)
uv run mcp-airq

# Build for distribution
uvx hatch build
```

> **Note:** The repo uses a project-local `.venv` managed by `uv`. Avoid machine-specific
> Python paths or globally installed lint/test tools when working on this project.

## Device Configuration

Via environment variable `AIRQ_DEVICES` (JSON array):

```json
[
  {"address": "192.168.1.100", "password": "airqsetup", "name": "Living Room"}
]
```

Or via `AIRQ_CONFIG_FILE` pointing to a JSON file with the same structure.

## Dependencies

- `mcp` — MCP SDK (FastMCP)
- `aioairq` — air-Q device communication (handles AES-256 encryption)
- `aiohttp` — async HTTP (session shared across all device connections)

## Code Conventions

- Python ≥ 3.11, type hints with built-in generics (`list`, `dict`, `str | None`)
- All tools are async, return `str` (JSON-serialized or plain text)
- Tools use docstrings as their MCP description (FastMCP extracts them automatically)
- Tests use `pytest` + `pytest-asyncio`, mock `AirQ` methods — no real device needed
- Keep the tool layer thin: business logic belongs in `aioairq`, not here

## Code Quality

- **DRY**: Before completing a task, review changes for repeated patterns. Extract shared
  helpers into `tools/_helpers.py` (tool code) or `tests/conftest.py` (test fixtures).
- **Review before committing**: Run `git diff --staged` to verify changes are clean,
  consistent, and don't introduce duplication. Run `ruff check`, `pyright`, and the relevant tests
  before committing to catch issues early.
- **Consistent serialization**: Use `_json()` from `tools/_helpers.py` for JSON responses.
  Use `json.dumps()` directly only for compact inline formatting (e.g. in f-strings).

## Versioning

When bumping the version, update it in **all three** of these files:

1. `pyproject.toml` — `version = "x.y.z"`
2. `server.json` — `"version": "x.y.z"` (appears twice: top-level and inside `packages[]`)
3. `CHANGELOG.md` — add a new `## [x.y.z] - YYYY-MM-DD` section

## Related Projects

- **aioairq**: `../../aioairq/` — the async Python library this server wraps
- **firmware-D**: `../../Firmware/firmware-D/` — the air-Q MicroPython firmware (defines the HTTP API)
