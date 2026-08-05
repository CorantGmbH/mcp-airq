"""Compatibility imports for MCP SDK v1 and v2."""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.mcpserver import Context, Image, MCPServer
else:
    try:
        _server = import_module("mcp.server.mcpserver")
    except ModuleNotFoundError:
        _server = import_module("mcp.server.fastmcp")

    Context = _server.Context
    Image = import_module(f"{_server.__name__}.utilities.types").Image
    MCPServer = getattr(_server, "MCPServer", None) or _server.FastMCP
