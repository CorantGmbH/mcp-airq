"""Read-only tools for querying air-Q devices."""

from collections.abc import Sequence

from aioairq import AirQ
from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from mcp_airq.errors import handle_airq_errors
from mcp_airq.guides import CONFIG_GUIDE, build_sensor_guide
from mcp_airq.server import mcp
from mcp_airq.tools._helpers import _json, _manager, _resolve

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def list_devices(ctx: Context) -> str:
    """List all configured air-Q devices with their names, addresses, locations, and groups."""
    mgr = _manager(ctx)
    devices = []
    for name in mgr.device_names:
        cfg = mgr.get_config_for(name)
        entry: dict[str, str] = {"name": name, "address": cfg.address}
        if cfg.location is not None:
            entry["location"] = cfg.location
        if cfg.group is not None:
            entry["group"] = cfg.group
        devices.append(entry)
    return _json(devices)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_air_quality(
    ctx: Context,
    device: str | None = None,
    location: str | None = None,
    group: str | None = None,
    return_average: bool = True,
    clip_negative: bool = True,
    include_uncertainties: bool = False,
) -> str:
    """Get current air quality sensor readings from one or more devices.

    Specify exactly one of:
    - 'device' — query a single device by name
    - 'location' — query all devices at a given location (e.g. "Wohnzimmer")
    - 'group' — query all devices in a group (e.g. "zu Hause")

    When using 'location' or 'group', the response contains one entry per
    device. Returns sensor names mapped to values. Set return_average=True
    for time-averaged data (recommended) or False for instantaneous readings.
    The response includes a _sensor_guide field with full unit and index
    documentation — read it before interpreting any values.
    """
    mgr = _manager(ctx)

    selectors = [x for x in (device, location, group) if x is not None]
    if len(selectors) > 1:
        return "Specify at most one of 'device', 'location', or 'group'."

    multi_devices: Sequence[tuple[str, AirQ]] | None = None
    if location is not None:
        multi_devices = mgr.resolve_location(location)
    elif group is not None:
        multi_devices = mgr.resolve_group(group)

    if multi_devices is not None:
        results: dict[str, object] = {}
        all_keys: set[str] = set()
        for name, airq in multi_devices:
            data = await airq.get_latest_data(
                return_average=return_average,
                clip_negative_values=clip_negative,
                return_uncertainties=include_uncertainties,
            )
            results[name] = data
            all_keys.update(data.keys())
        results["_sensor_guide"] = build_sensor_guide(all_keys)
        return _json(results)

    airq = mgr.resolve(device)
    data = await airq.get_latest_data(
        return_average=return_average,
        clip_negative_values=clip_negative,
        return_uncertainties=include_uncertainties,
    )
    data["_sensor_guide"] = build_sensor_guide(set(data.keys()))
    return _json(data)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_device_info(ctx: Context, device: str | None = None) -> str:
    """Get device metadata: ID, name, model, firmware/hardware version, and suggested area."""
    _, airq = _resolve(ctx, device)
    info = await airq.fetch_device_info()
    return _json(dict(info))


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_config(ctx: Context, device: str | None = None) -> str:
    """Get the full configuration of a device as a JSON dict.

    The response includes a _config_guide field with full documentation of
    all configuration keys — read it before interpreting or modifying values.
    """
    _, airq = _resolve(ctx, device)
    config = await airq.get_config()
    config["_config_guide"] = CONFIG_GUIDE
    return _json(config)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_logs(ctx: Context, device: str | None = None) -> str:
    """Get log entries from a device."""
    _, airq = _resolve(ctx, device)
    logs = await airq.get_log()
    return _json(logs)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def identify_device(ctx: Context, device: str | None = None) -> str:
    """Make a device blink its LEDs in rainbow colors for visual identification. Returns the device ID."""
    _, airq = _resolve(ctx, device)
    device_id = await airq.blink()
    return f"Device is blinking. Device ID: {device_id}"


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_led_theme(ctx: Context, device: str | None = None) -> str:
    """Get the current LED visualization theme for both sides of a device."""
    _, airq = _resolve(ctx, device)
    theme = await airq.get_led_theme()
    return _json(theme)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_possible_led_themes(ctx: Context, device: str | None = None) -> str:
    """List all available LED visualization themes for a device."""
    _, airq = _resolve(ctx, device)
    themes = await airq.get_possible_led_themes()
    return _json(themes)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_night_mode(ctx: Context, device: str | None = None) -> str:
    """Get the current night mode configuration of a device."""
    _, airq = _resolve(ctx, device)
    night_mode = await airq.get_night_mode()
    return _json(night_mode)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_brightness_config(ctx: Context, device: str | None = None) -> str:
    """Get the current LED brightness configuration (day and night values) of a device."""
    _, airq = _resolve(ctx, device)
    brightness = await airq.get_brightness_config()
    return _json(brightness)
