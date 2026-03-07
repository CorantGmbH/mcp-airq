"""Tests for read-only tools."""

# pylint: disable=redefined-outer-name
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_airq.config import DeviceConfig
from mcp_airq.devices import DeviceManager
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
    assert "location" not in data[0]  # no location configured
    assert "group" not in data[0]  # no group configured


@pytest.mark.asyncio
async def test_list_devices_with_location(mock_session):
    """list_devices includes location when configured."""
    configs = [DeviceConfig("10.0.0.1", "pw", "MyAirQ", location="Wohnzimmer")]
    mgr = DeviceManager(mock_session, configs)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = mgr
    result = await list_devices(ctx)
    data = json.loads(result)
    assert data[0]["location"] == "Wohnzimmer"


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
async def test_get_air_quality_by_location(mock_session):
    """get_air_quality with location queries all devices at that location."""
    configs = [
        DeviceConfig("10.0.0.1", "pw", "air-Q Basic", location="Wohnzimmer"),
        DeviceConfig("10.0.0.2", "pw", "air-Q Radon", location="Wohnzimmer"),
    ]
    mgr = DeviceManager(mock_session, configs)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = mgr

    mock_airq_1 = AsyncMock()
    mock_airq_1.get_latest_data.return_value = {"temperature": 22.0, "co2": 400}
    mock_airq_2 = AsyncMock()
    mock_airq_2.get_latest_data.return_value = {"temperature": 22.5, "radon": 50}

    with patch.object(
        mgr,
        "resolve_location",
        return_value=[
            ("air-Q Basic", mock_airq_1),
            ("air-Q Radon", mock_airq_2),
        ],
    ):
        result = await get_air_quality(ctx, location="Wohnzimmer")
        data = json.loads(result)
        assert "air-Q Basic" in data
        assert "air-Q Radon" in data
        assert data["air-Q Basic"]["temperature"] == 22.0
        assert data["air-Q Radon"]["radon"] == 50


@pytest.mark.asyncio
async def test_get_air_quality_multiple_selectors_rejected(mock_ctx):
    """get_air_quality rejects more than one selector."""
    result = await get_air_quality(mock_ctx, device="foo", location="bar")
    assert "at most one" in result
    result2 = await get_air_quality(mock_ctx, location="bar", group="baz")
    assert "at most one" in result2


@pytest.mark.asyncio
async def test_get_air_quality_by_group(mock_session):
    """get_air_quality with group queries all devices in that group."""
    configs = [
        DeviceConfig("10.0.0.1", "pw", "air-Q Wohnzimmer", group="zu Hause"),
        DeviceConfig("10.0.0.2", "pw", "air-Q Büro", group="Arbeit"),
        DeviceConfig("10.0.0.3", "pw", "air-Q Schlafzimmer", group="zu Hause"),
    ]
    mgr = DeviceManager(mock_session, configs)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = mgr

    mock_airq_1 = AsyncMock()
    mock_airq_1.get_latest_data.return_value = {"temperature": 22.0}
    mock_airq_3 = AsyncMock()
    mock_airq_3.get_latest_data.return_value = {"temperature": 19.5}

    with patch.object(
        mgr,
        "resolve_group",
        return_value=[
            ("air-Q Wohnzimmer", mock_airq_1),
            ("air-Q Schlafzimmer", mock_airq_3),
        ],
    ):
        result = await get_air_quality(ctx, group="zu Hause")
        data = json.loads(result)
        assert "air-Q Wohnzimmer" in data
        assert "air-Q Schlafzimmer" in data
        assert "air-Q Büro" not in data


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
