"""Tests for read-only tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_airq.tools.read import (
    get_air_quality,
    get_config,
    get_device_info,
    get_logs,
    identify_device,
    list_devices,
)


@pytest.fixture
def mock_ctx(single_device_manager):
    """Create a mock Context with the device manager as lifespan context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = single_device_manager
    return ctx


@pytest.fixture
def mock_airq():
    """Create a mock AirQ instance."""
    airq = AsyncMock()
    airq.get_latest_data.return_value = {
        "temperature": 22.5,
        "humidity": 45.0,
        "co2": 410,
        "Status": "OK",
    }
    airq.fetch_device_info.return_value = {
        "id": "abc123",
        "name": "TestDevice",
        "model": "air-Q Pro",
        "suggested_area": "living-room",
        "sw_version": "2.1.0",
        "hw_version": "D",
    }
    airq.get_config.return_value = {"devicename": "Test", "Averaging": 300}
    airq.get_log.return_value = ["2024-01-01 OK", "2024-01-02 Warning: low battery"]
    airq.blink.return_value = "abc123def456"
    return airq


@pytest.mark.asyncio
async def test_list_devices(mock_ctx):
    """list_devices returns configured devices."""
    result = await list_devices(mock_ctx)
    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["name"] == "TestDevice"
    assert data[0]["address"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_get_air_quality(mock_ctx, mock_airq):
    """get_air_quality returns sensor data."""
    with patch.object(
        mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq
    ):
        result = await get_air_quality(mock_ctx)
        data = json.loads(result)
        assert data["temperature"] == 22.5
        assert data["co2"] == 410
        mock_airq.get_latest_data.assert_awaited_once_with(
            return_average=True,
            clip_negative_values=True,
            return_uncertainties=False,
        )


@pytest.mark.asyncio
async def test_get_air_quality_with_options(mock_ctx, mock_airq):
    """get_air_quality passes options through."""
    with patch.object(
        mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq
    ):
        await get_air_quality(
            mock_ctx,
            return_average=False,
            clip_negative=False,
            include_uncertainties=True,
        )
        mock_airq.get_latest_data.assert_awaited_once_with(
            return_average=False,
            clip_negative_values=False,
            return_uncertainties=True,
        )


@pytest.mark.asyncio
async def test_get_device_info(mock_ctx, mock_airq):
    """get_device_info returns device metadata."""
    with patch.object(
        mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq
    ):
        result = await get_device_info(mock_ctx)
        data = json.loads(result)
        assert data["model"] == "air-Q Pro"
        assert data["hw_version"] == "D"


@pytest.mark.asyncio
async def test_get_config(mock_ctx, mock_airq):
    """get_config returns device configuration."""
    with patch.object(
        mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq
    ):
        result = await get_config(mock_ctx)
        data = json.loads(result)
        assert data["devicename"] == "Test"


@pytest.mark.asyncio
async def test_get_logs(mock_ctx, mock_airq):
    """get_logs returns log entries."""
    with patch.object(
        mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq
    ):
        result = await get_logs(mock_ctx)
        data = json.loads(result)
        assert len(data) == 2


@pytest.mark.asyncio
async def test_identify_device(mock_ctx, mock_airq):
    """identify_device triggers blink and returns device ID."""
    with patch.object(
        mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq
    ):
        result = await identify_device(mock_ctx)
        assert "abc123def456" in result
        assert "blinking" in result.lower()
