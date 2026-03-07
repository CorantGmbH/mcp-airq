"""MCP prompts providing sensor and configuration context for air-Q devices."""

from mcp_airq.guides import CONFIG_GUIDE, SENSOR_GUIDE
from mcp_airq.server import mcp


@mcp.prompt()
def airq_sensor_guide() -> str:
    """Guide for interpreting air-Q sensor values: units, ranges, and semantics."""
    return SENSOR_GUIDE


@mcp.prompt()
def airq_config_guide() -> str:
    """Guide for interpreting and setting air-Q device configuration keys."""
    return CONFIG_GUIDE
