"""MCP server for air-Q air quality sensor devices."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcp-airq")
except PackageNotFoundError:
    __version__ = "0.0.0"
