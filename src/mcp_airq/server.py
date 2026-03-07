"""MCP server for air-Q air quality sensor devices."""

import argparse
import sys
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiohttp
from mcp.server.fastmcp import FastMCP

from mcp_airq import __version__
from mcp_airq.config import load_config
from mcp_airq.devices import DeviceManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp-airq")


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[DeviceManager]:
    """Create shared aiohttp session and device manager for the server lifetime."""
    configs = load_config()
    logger.info("Starting air-Q MCP server with %d device(s)", len(configs))
    timeout = aiohttp.ClientTimeout(total=30, connect=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
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

# Import tools and prompts to register them with the mcp instance
# pylint: disable=wrong-import-position, unused-import, cyclic-import
from mcp_airq.tools import dangerous, read, write  # noqa: E402, F401
from mcp_airq import prompts  # noqa: E402, F401


_HELP_TEXT = """\
mcp-airq — MCP server for air-Q air quality sensor devices

This command is designed to be launched by an MCP client (e.g. Claude Desktop,
Claude Code, or OpenAI Codex), not run interactively from the terminal.
It communicates via JSON-RPC 2.0 over standard input/output (stdio transport).

To add this server to Claude Desktop, add the following to your
claude_desktop_config.json:

  {
    "mcpServers": {
      "air-Q": {
        "command": "mcp-airq",
        "env": {
          "AIRQ_DEVICES": "[{\\"address\\": \\"<IP>\\", \\"password\\": \\"<PW>\\", \\"name\\": \\"<Name>\\"}]"
        }
      }
    }
  }

To add it to Claude Code, run:

  claude mcp add air-Q mcp-airq -e AIRQ_DEVICES='[{"address":"<IP>","password":"<PW>","name":"<Name>"}]'

Alternatively, set AIRQ_CONFIG_FILE to point to a JSON configuration file
with the same structure as the AIRQ_DEVICES array.

For more information, see: https://github.com/CorantGmbH/mcp-airq
"""


def main():
    """Entry point for the mcp-airq command."""
    parser = argparse.ArgumentParser(
        prog="mcp-airq",
        description="MCP server for air-Q air quality sensor devices",
        add_help=False,
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument(
        "--help", "-h", action="store_true", help="Show this help and exit"
    )

    args, _ = parser.parse_known_args()

    if args.version:
        print(f"mcp-airq {__version__}")
        return

    if args.help or sys.stdin.isatty():
        print(_HELP_TEXT, end="")
        return

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
