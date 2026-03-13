"""Write tools for configuring air-Q devices."""

import json

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from mcp_airq.errors import handle_airq_errors
from mcp_airq.server import mcp
from mcp_airq.tools._helpers import _resolve

WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)


@mcp.tool(annotations=WRITE)
@handle_airq_errors
async def set_device_name(ctx: Context, name: str, device: str | None = None) -> str:
    """Rename a device. The new name appears on the device display."""
    _, airq = _resolve(ctx, device)
    await airq.set_device_name(name)
    return f"Device name set to '{name}'."


@mcp.tool(annotations=WRITE)
@handle_airq_errors
async def set_led_theme(
    ctx: Context,
    left: str | None = None,
    right: str | None = None,
    device: str | None = None,
) -> str:
    """Set the LED visualization theme for one or both sides of the device.

    Common themes: 'standard', 'CO2', 'VOC', 'Humidity', 'PM2.5', 'Noise'.
    Use get_possible_led_themes to see all available themes.
    """
    _, airq = _resolve(ctx, device)
    if left is None and right is None:
        return "Specify at least one of 'left' or 'right' theme."
    theme = {}
    if left is not None:
        theme["left"] = left
    if right is not None:
        theme["right"] = right
    await airq.set_led_theme(theme)  # type: ignore[arg-type]
    return f"LED theme updated: {json.dumps(theme)}"


@mcp.tool(annotations=WRITE)
@handle_airq_errors
async def set_night_mode(
    ctx: Context,
    activated: bool,
    start_night: str = "22:00",
    start_day: str = "06:00",
    brightness_day: float = 100.0,
    brightness_night: float = 0.0,
    fan_night_off: bool = False,
    wifi_night_off: bool = False,
    alarm_night_off: bool = False,
    device: str | None = None,
) -> str:
    """Configure night mode. Times in 'HH:mm' format (UTC).

    brightness_day/brightness_night are percentages (0-100).
    fan_night_off disables the particle sensor fan at night.
    wifi_night_off caches data to SD and uploads when wifi returns.
    alarm_night_off disables acoustic warnings (fire/gas still trigger).
    """
    _, airq = _resolve(ctx, device)
    night_mode = {
        "activated": activated,
        "start_night": start_night,
        "start_day": start_day,
        "brightness_day": brightness_day,
        "brightness_night": brightness_night,
        "fan_night_off": fan_night_off,
        "wifi_night_off": wifi_night_off,
        "alarm_night_off": alarm_night_off,
    }
    await airq.set_night_mode(night_mode)  # type: ignore[arg-type]
    status = "enabled" if activated else "disabled"
    return f"Night mode {status}. Config: {json.dumps(night_mode)}"


@mcp.tool(annotations=WRITE)
@handle_airq_errors
async def set_brightness(
    ctx: Context,
    default: float,
    night: float | None = None,
    device: str | None = None,
) -> str:
    """Set LED brightness. 'default' is the normal brightness (0-100%), 'night' is optional night brightness."""
    _, airq = _resolve(ctx, device)
    await airq.set_brightness_config(default=default, night=night)
    result = f"Brightness set to {default}%"
    if night is not None:
        result += f" (night: {night}%)"
    return result


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True))
@handle_airq_errors
async def configure_network(
    ctx: Context,
    dhcp: bool = False,
    ip: str | None = None,
    subnet: str | None = None,
    gateway: str | None = None,
    dns: str | None = None,
    device: str | None = None,
) -> str:
    """Configure network settings. Set dhcp=True for DHCP, or provide ip/subnet/gateway/dns for static IP.

    After changing network settings, the device must be restarted.
    """
    _, airq = _resolve(ctx, device)
    if dhcp:
        await airq.set_ifconfig_dhcp()
        return "Network set to DHCP. Restart the device to apply."
    if not all([ip, subnet, gateway, dns]):
        return "For static IP, provide all of: ip, subnet, gateway, dns."
    assert ip and subnet and gateway and dns  # narrowed from str | None after guard above
    await airq.set_ifconfig_static(ip, subnet, gateway, dns)
    return f"Static IP configured: {ip}/{subnet}, gateway={gateway}, dns={dns}. Restart to apply."
