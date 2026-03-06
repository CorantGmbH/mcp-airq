"""MCP server for air-Q air quality sensor devices."""

import sys
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiohttp
from mcp.server.fastmcp import FastMCP

from mcp_airq.config import load_config
from mcp_airq.devices import DeviceManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp-airq")


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[DeviceManager]:
    """Create shared aiohttp session and device manager for the server lifetime."""
    configs = load_config()
    logger.info("Starting air-Q MCP server with %d device(s)", len(configs))
    async with aiohttp.ClientSession() as session:
        yield DeviceManager(session, configs)


mcp = FastMCP(
    name="air-Q",
    instructions=(
        "This server provides access to air-Q air quality sensor devices. "
        "Use list_devices to see available devices. Most tools accept an "
        "optional 'device' parameter to select which device to query — "
        "if only one device is configured, it is selected automatically."
    ),
    lifespan=app_lifespan,
)

# Import tools to register them with the mcp instance
from mcp_airq.tools import dangerous, read, write  # noqa: E402, F401


def main():
    """Entry point for the mcp-airq command."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
