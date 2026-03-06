"""Potentially dangerous tools (restart, shutdown)."""

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from mcp_airq.devices import DeviceManager
from mcp_airq.errors import handle_airq_errors
from mcp_airq.server import mcp

DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False
)


def _manager(ctx: Context) -> DeviceManager:
    """Extract DeviceManager from request context."""
    return ctx.request_context.lifespan_context


@mcp.tool(annotations=DESTRUCTIVE)
@handle_airq_errors
async def restart_device(ctx: Context, device: str | None = None) -> str:
    """Restart a device. It will be unreachable for about 30 seconds."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    await airq.restart()
    return "Device is restarting. It will be available again in about 30 seconds."


@mcp.tool(annotations=DESTRUCTIVE)
@handle_airq_errors
async def shutdown_device(ctx: Context, device: str | None = None) -> str:
    """Shut down a device. It must be manually powered on again. Only use if explicitly requested."""
    mgr = _manager(ctx)
    airq = mgr.resolve(device)
    await airq.shutdown()
    return "Device has been shut down. It must be manually powered on again."
