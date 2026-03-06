"""Read-only tools for querying air-Q devices."""

import json

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from mcp_airq.devices import DeviceManager
from mcp_airq.errors import handle_airq_errors
from mcp_airq.server import mcp

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False)


def _manager(ctx: Context) -> DeviceManager:
    """Extract DeviceManager from request context."""
    return ctx.request_context.lifespan_context


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def list_devices(ctx: Context) -> str:
    """List all configured air-Q devices with their names and addresses."""
    mgr = _manager(ctx)
    devices = []
    for name in mgr.device_names:
        cfg = mgr.get_config_for(name)
        devices.append({"name": name, "address": cfg.address})
    return json.dumps(devices, indent=2)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_air_quality(
    ctx: Context,
    device: str | None = None,
    return_average: bool = True,
    clip_negative: bool = True,
    include_uncertainties: bool = False,
) -> str:
    """Get current air quality sensor readings from a device.

    Returns sensor names mapped to values. Set return_average=True for
    time-averaged data (recommended) or False for instantaneous readings.
    """
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    data = await airq.get_latest_data(
        return_average=return_average,
        clip_negative_values=clip_negative,
        return_uncertainties=include_uncertainties,
    )
    return json.dumps(data, indent=2, default=str)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_device_info(ctx: Context, device: str | None = None) -> str:
    """Get device metadata: ID, name, model, firmware/hardware version, and suggested area."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    info = await airq.fetch_device_info()
    return json.dumps(dict(info), indent=2)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_config(ctx: Context, device: str | None = None) -> str:
    """Get the full configuration of a device as a JSON dict."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    config = await airq.get_config()
    return json.dumps(config, indent=2, default=str)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_logs(ctx: Context, device: str | None = None) -> str:
    """Get log entries from a device."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    logs = await airq.get_log()
    return json.dumps(logs, indent=2)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def identify_device(ctx: Context, device: str | None = None) -> str:
    """Make a device blink its LEDs in rainbow colors for visual identification. Returns the device ID."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    device_id = await airq.blink()
    return f"Device is blinking. Device ID: {device_id}"


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_led_theme(ctx: Context, device: str | None = None) -> str:
    """Get the current LED visualization theme for both sides of a device."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    theme = await airq.get_led_theme()
    return json.dumps(theme, indent=2)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_possible_led_themes(ctx: Context, device: str | None = None) -> str:
    """List all available LED visualization themes for a device."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    themes = await airq.get_possible_led_themes()
    return json.dumps(themes, indent=2)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_night_mode(ctx: Context, device: str | None = None) -> str:
    """Get the current night mode configuration of a device."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    night_mode = await airq.get_night_mode()
    return json.dumps(night_mode, indent=2)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_brightness_config(ctx: Context, device: str | None = None) -> str:
    """Get the current LED brightness configuration (day and night values) of a device."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    brightness = await airq.get_brightness_config()
    return json.dumps(brightness, indent=2)
