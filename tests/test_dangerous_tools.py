"""Tests for dangerous tools (restart, shutdown)."""

# pylint: disable=redefined-outer-name
from unittest.mock import AsyncMock, patch

import pytest

from mcp_airq.tools.dangerous import restart_device, shutdown_device


@pytest.fixture
def mock_airq():
    """Create a mock AirQ instance."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_restart_device(mock_ctx, mock_airq):
    """restart_device calls airq.restart() and returns confirmation."""
    with patch.object(
        mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq
    ):
        result = await restart_device(mock_ctx)
        assert "restarting" in result.lower()
        mock_airq.restart.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_device(mock_ctx, mock_airq):
    """shutdown_device calls airq.shutdown() and returns confirmation."""
    with patch.object(
        mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq
    ):
        result = await shutdown_device(mock_ctx)
        assert "shut down" in result.lower()
        mock_airq.shutdown.assert_awaited_once()
