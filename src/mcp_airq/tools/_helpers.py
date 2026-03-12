"""Shared helpers for tool modules."""

import json

from aioairq import AirQ
from mcp.server.fastmcp import Context

from mcp_airq.devices import DeviceManager


def _manager(ctx: Context) -> DeviceManager:
    """Extract DeviceManager from request context."""
    return ctx.request_context.lifespan_context


def _resolve(ctx: Context, device: str | None) -> tuple[DeviceManager, AirQ]:
    """Extract DeviceManager and resolve the target device."""
    mgr = _manager(ctx)
    return mgr, mgr.resolve(device)


def _json(data: object) -> str:
    """Serialize data as indented JSON with safe default serialization."""
    return json.dumps(data, indent=2, default=str)
