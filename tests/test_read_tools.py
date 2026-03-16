"""Tests for read-only tools."""

import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from airq_mcp_timeseries.models import PlotResult
from mcp.server.fastmcp.utilities.types import Image
from mcp.types import BlobResourceContents, EmbeddedResource, TextResourceContents

from mcp_airq.config import DeviceConfig
from mcp_airq.devices import DeviceManager
from mcp_airq.tools.read import (
    _collect_historical_data,
    _downsample,
    _filter_sensors,
    _parse_time_range,
    export_air_quality_history,
    get_air_quality,
    get_air_quality_history,
    get_brightness_config,
    get_config,
    get_device_info,
    get_led_theme,
    get_logs,
    get_night_mode,
    get_possible_led_themes,
    identify_device,
    list_devices,
    plot_air_quality_history,
)


@pytest.fixture
def mock_ctx_with_group(mock_session):
    """Create a mock Context with a device that has a group configured."""
    configs = [DeviceConfig("10.0.0.1", "pw", "MyAirQ", group="zu Hause")]
    mgr = DeviceManager(mock_session, configs)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = mgr
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
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
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
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
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
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await get_device_info(mock_ctx)
        data = json.loads(result)
        assert data["model"] == "air-Q Pro"
        assert data["hw_version"] == "D"


@pytest.mark.asyncio
async def test_get_config(mock_ctx, mock_airq):
    """get_config returns device configuration."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await get_config(mock_ctx)
        data = json.loads(result)
        assert data["devicename"] == "Test"


@pytest.mark.asyncio
async def test_get_logs(mock_ctx, mock_airq):
    """get_logs returns log entries."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await get_logs(mock_ctx)
        data = json.loads(result)
        assert len(data) == 2


@pytest.mark.asyncio
async def test_identify_device(mock_ctx, mock_airq):
    """identify_device triggers blink and returns device ID."""
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await identify_device(mock_ctx)
        assert "abc123def456" in result
        assert "blinking" in result.lower()


@pytest.mark.asyncio
async def test_list_devices_with_group(mock_ctx_with_group):
    """list_devices includes group when configured."""
    result = await list_devices(mock_ctx_with_group)
    data = json.loads(result)
    assert data[0]["group"] == "zu Hause"


@pytest.mark.asyncio
async def test_get_led_theme(mock_ctx, mock_airq):
    """get_led_theme returns the current LED theme."""
    mock_airq.get_led_theme.return_value = {"left": "air", "right": "air"}
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await get_led_theme(mock_ctx)
        data = json.loads(result)
        assert data["left"] == "air"


@pytest.mark.asyncio
async def test_get_possible_led_themes(mock_ctx, mock_airq):
    """get_possible_led_themes returns available theme names."""
    mock_airq.get_possible_led_themes.return_value = ["air", "health", "pollen"]
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await get_possible_led_themes(mock_ctx)
        data = json.loads(result)
        assert "air" in data


@pytest.mark.asyncio
async def test_get_night_mode(mock_ctx, mock_airq):
    """get_night_mode returns night mode configuration."""
    mock_airq.get_night_mode.return_value = {
        "activated": True,
        "start": "22:00",
        "end": "07:00",
    }
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await get_night_mode(mock_ctx)
        data = json.loads(result)
        assert data["activated"] is True


@pytest.mark.asyncio
async def test_get_brightness_config(mock_ctx, mock_airq):
    """get_brightness_config returns day and night brightness values."""
    mock_airq.get_brightness_config.return_value = {"day": 80, "night": 20}
    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=mock_airq):
        result = await get_brightness_config(mock_ctx)
        data = json.loads(result)
        assert data["day"] == 80


# ---------------------------------------------------------------------------
# _parse_time_range helper tests
# ---------------------------------------------------------------------------

NOW = datetime(2026, 3, 12, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_time_range_default_one_hour():
    """Defaults to last 1 hour when no arguments given."""
    from_dt, to_dt, timezone_name = _parse_time_range(NOW, None, None, None)
    assert to_dt == NOW
    assert from_dt == NOW - timedelta(hours=1)
    assert timezone_name == "UTC"


def test_parse_time_range_custom_hours():
    """Accepts a custom last_hours value."""
    from_dt, to_dt, timezone_name = _parse_time_range(NOW, 6.0, None, None)
    assert from_dt == NOW - timedelta(hours=6)
    assert to_dt == NOW
    assert timezone_name == "UTC"


def test_parse_time_range_negative_hours():
    """Rejects non-positive last_hours."""
    result = _parse_time_range(NOW, -1, None, None)
    assert isinstance(result, str)
    assert "positive" in result


def test_parse_time_range_from_to():
    """Accepts both from_datetime and to_datetime."""
    result = _parse_time_range(NOW, None, "2026-03-12T10:00:00+00:00", "2026-03-12T11:00:00+00:00")
    assert not isinstance(result, str)
    from_dt, to_dt, timezone_name = result
    assert from_dt.hour == 10
    assert to_dt.hour == 11
    assert timezone_name == "UTC"


def test_parse_time_range_from_only():
    """Defaults to_datetime to now when only from_datetime is given."""
    result = _parse_time_range(NOW, None, "2026-03-12T10:00:00+00:00", None)
    assert not isinstance(result, str)
    from_dt, to_dt, timezone_name = result
    assert from_dt.hour == 10
    assert to_dt == NOW
    assert timezone_name == "UTC"


def test_parse_time_range_naive_datetime():
    """Naive datetimes get UTC timezone attached."""
    result = _parse_time_range(NOW, None, "2026-03-12T10:00:00", "2026-03-12T11:00:00")
    assert not isinstance(result, str)
    from_dt, to_dt, timezone_name = result
    assert from_dt.tzinfo == timezone.utc
    assert to_dt.tzinfo == timezone.utc
    assert timezone_name == "UTC"


def test_parse_time_range_from_after_to():
    """Rejects from_datetime >= to_datetime."""
    result = _parse_time_range(NOW, None, "2026-03-12T12:00:00+00:00", "2026-03-12T11:00:00+00:00")
    assert isinstance(result, str)
    assert "before" in result


# ---------------------------------------------------------------------------
# _filter_sensors / _downsample helper tests
# ---------------------------------------------------------------------------


def test_filter_sensors_keeps_timestamp():
    """Always keeps timestamp and datetime keys."""
    data = [{"temperature": 22.0, "co2": 400, "timestamp": 1000, "datetime": "x"}]
    result = _filter_sensors(data, ["co2"])
    assert "co2" in result[0]
    assert "timestamp" in result[0]
    assert "datetime" in result[0]
    assert "temperature" not in result[0]


def test_filter_sensors_case_insensitive():
    """Sensor filter is case-insensitive."""
    data = [{"CO2": 400, "Temperature": 22.0, "timestamp": 1000}]
    result = _filter_sensors(data, ["co2"])
    assert "CO2" in result[0]
    assert "Temperature" not in result[0]


def test_downsample_fewer_than_max():
    """No effect when data has fewer entries than max_points."""
    data = [{"v": i} for i in range(5)]
    assert _downsample(data, 100) is data


def test_downsample_evenly_spaced():
    """Correctly downsamples to evenly spaced entries."""
    data = [{"v": i} for i in range(100)]
    result = _downsample(data, 10)
    assert len(result) == 10
    assert result[0]["v"] == 0
    assert result[1]["v"] == 10


# ---------------------------------------------------------------------------
# _collect_historical_data tests
# ---------------------------------------------------------------------------

# 2026-03-12 10:00:00 UTC
_TS_BASE = int(datetime(2026, 3, 12, 10, 0, 0, tzinfo=timezone.utc).timestamp())


def _make_mock_airq(file_names, measurements):
    """Create a mock AirQ with historical data methods."""
    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(return_value=file_names)
    airq.get_historical_file = AsyncMock(return_value=measurements)
    return airq


@pytest.mark.asyncio
async def test_collect_historical_data_single_day():
    """Collects data from files within a single day."""
    measurements = [
        {"timestamp": _TS_BASE * 1000, "temperature": 22.0},
        {"timestamp": (_TS_BASE + 120) * 1000, "temperature": 22.5},
    ]
    airq = _make_mock_airq([str(_TS_BASE)], measurements)

    from_dt = datetime(2026, 3, 12, 9, 55, 0, tzinfo=timezone.utc)
    to_dt = datetime(2026, 3, 12, 10, 5, 0, tzinfo=timezone.utc)
    result = await _collect_historical_data(airq, from_dt, to_dt)

    assert len(result) == 2
    assert result[0]["temperature"] == 22.0


@pytest.mark.asyncio
async def test_collect_historical_data_multi_day():
    """Enumerates multiple days when range spans midnight."""
    from_dt = datetime(2026, 3, 11, 23, 0, 0, tzinfo=timezone.utc)
    to_dt = datetime(2026, 3, 12, 1, 0, 0, tzinfo=timezone.utc)

    ts_day1 = int(from_dt.timestamp())
    ts_day2 = int(datetime(2026, 3, 12, 0, 30, 0, tzinfo=timezone.utc).timestamp())

    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(side_effect=[[str(ts_day1)], [str(ts_day2)]])
    airq.get_historical_file = AsyncMock(
        side_effect=[
            [{"timestamp": ts_day1 * 1000, "co2": 400}],
            [{"timestamp": ts_day2 * 1000, "co2": 410}],
        ]
    )

    result = await _collect_historical_data(airq, from_dt, to_dt)
    assert len(result) == 2
    assert airq.get_historical_files_list.await_count == 2


@pytest.mark.asyncio
async def test_collect_historical_data_skips_missing_day():
    """Gracefully skips days that return HTTP 404."""
    from_dt = datetime(2026, 3, 12, 10, 0, 0, tzinfo=timezone.utc)
    to_dt = datetime(2026, 3, 12, 11, 0, 0, tzinfo=timezone.utc)

    mock_resp = MagicMock()
    mock_resp.status = 404
    mock_resp.message = "Not Found"
    mock_resp.headers = {}

    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(side_effect=aiohttp.ClientResponseError(mock_resp, (), status=404))

    result = await _collect_historical_data(airq, from_dt, to_dt)
    assert result == []


@pytest.mark.asyncio
async def test_collect_historical_data_filters_by_timestamp():
    """Only keeps measurements within [from_ms, to_ms]."""
    ts_in = _TS_BASE * 1000
    ts_out = (_TS_BASE + 7200) * 1000  # 2 hours later — outside range

    airq = _make_mock_airq(
        [str(_TS_BASE)],
        [
            {"timestamp": ts_in, "temperature": 22.0},
            {"timestamp": ts_out, "temperature": 25.0},
        ],
    )

    from_dt = datetime(2026, 3, 12, 9, 55, 0, tzinfo=timezone.utc)
    to_dt = datetime(2026, 3, 12, 10, 5, 0, tzinfo=timezone.utc)
    result = await _collect_historical_data(airq, from_dt, to_dt)

    assert len(result) == 1
    assert result[0]["temperature"] == 22.0


@pytest.mark.asyncio
async def test_collect_historical_data_sorts_by_timestamp():
    """Output is sorted chronologically."""
    ts1 = _TS_BASE * 1000
    ts2 = (_TS_BASE + 60) * 1000
    ts3 = (_TS_BASE + 120) * 1000

    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(return_value=[str(_TS_BASE + 120), str(_TS_BASE)])
    airq.get_historical_file = AsyncMock(
        side_effect=[
            [{"timestamp": ts3, "v": 3}],
            [{"timestamp": ts1, "v": 1}, {"timestamp": ts2, "v": 2}],
        ]
    )

    from_dt = datetime(2026, 3, 12, 9, 55, 0, tzinfo=timezone.utc)
    to_dt = datetime(2026, 3, 12, 10, 5, 0, tzinfo=timezone.utc)
    result = await _collect_historical_data(airq, from_dt, to_dt)

    timestamps = [m["timestamp"] for m in result]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_collect_historical_data_empty():
    """Returns empty list when no files match."""
    airq = _make_mock_airq([], [])

    from_dt = datetime(2026, 3, 12, 10, 0, 0, tzinfo=timezone.utc)
    to_dt = datetime(2026, 3, 12, 11, 0, 0, tzinfo=timezone.utc)
    result = await _collect_historical_data(airq, from_dt, to_dt)

    assert result == []


# ---------------------------------------------------------------------------
# get_air_quality_history tool integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_airq_with_history():
    """Create a mock AirQ with historical data methods configured."""
    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(return_value=[str(_TS_BASE)])
    airq.get_historical_file = AsyncMock(
        return_value=[
            {"timestamp": _TS_BASE * 1000, "temperature": 22.0, "co2": 400},
            {"timestamp": (_TS_BASE + 120) * 1000, "temperature": 22.5, "co2": 410},
        ]
    )
    return airq


@pytest.mark.asyncio
async def test_get_air_quality_history_default_last_hour(mock_ctx, mock_airq_with_history):
    """Defaults to last 1 hour, compact mode."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(mock_ctx)
        data = json.loads(result)
        assert "count" in data
        assert "columns" in data
        assert "from" in data
        assert "to" in data


@pytest.mark.asyncio
async def test_get_air_quality_history_custom_hours(mock_ctx, mock_airq_with_history):
    """Accepts custom last_hours."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(mock_ctx, last_hours=6.0)
        data = json.loads(result)
        assert "columns" in data


@pytest.mark.asyncio
async def test_get_air_quality_history_from_to(mock_ctx, mock_airq_with_history):
    """Accepts from_datetime and to_datetime."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
        )
        data = json.loads(result)
        assert data["count"] == 2
        assert "2026-03-12" in data["from"]


@pytest.mark.asyncio
async def test_get_air_quality_history_from_only(mock_ctx, mock_airq_with_history):
    """Defaults to_datetime to now when only from_datetime is given."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(mock_ctx, from_datetime="2026-03-12T09:00:00+00:00")
        data = json.loads(result)
        assert "columns" in data


@pytest.mark.asyncio
async def test_get_air_quality_history_negative_hours(mock_ctx):
    """Rejects non-positive last_hours."""
    result = await get_air_quality_history(mock_ctx, last_hours=-1)
    assert "positive" in result


@pytest.mark.asyncio
async def test_get_air_quality_history_from_after_to(mock_ctx):
    """Rejects from_datetime >= to_datetime."""
    result = await get_air_quality_history(
        mock_ctx,
        from_datetime="2026-03-12T12:00:00+00:00",
        to_datetime="2026-03-12T11:00:00+00:00",
    )
    assert "before" in result


@pytest.mark.asyncio
async def test_get_air_quality_history_includes_sensor_guide(mock_ctx, mock_airq_with_history):
    """Response always includes _sensor_guide."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
        )
        data = json.loads(result)
        assert "_sensor_guide" in data


@pytest.mark.asyncio
async def test_get_air_quality_history_sensors_filter(mock_ctx, mock_airq_with_history):
    """Filters to requested sensors only."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            sensors=["co2"],
        )
        data = json.loads(result)
        cols = data["columns"]
        assert "co2" in cols
        assert "timestamp" in cols
        assert "temperature" not in cols


@pytest.mark.asyncio
async def test_get_air_quality_history_max_points(mock_ctx):
    """Downsamples to max_points."""
    measurements = [{"timestamp": (_TS_BASE + i * 120) * 1000, "temperature": 20.0 + i * 0.1} for i in range(100)]
    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(return_value=[str(_TS_BASE)])
    airq.get_historical_file = AsyncMock(return_value=measurements)

    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=airq):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T14:00:00+00:00",
            max_points=10,
        )
        data = json.loads(result)
        assert data["count"] == 10
        assert len(data["columns"]["temperature"]) == 10


@pytest.mark.asyncio
async def test_get_air_quality_history_sensors_and_max_points(mock_ctx):
    """Applies both sensors filter and max_points."""
    measurements = [
        {
            "timestamp": (_TS_BASE + i * 120) * 1000,
            "temperature": 20.0 + i,
            "pm10": float(i),
        }
        for i in range(50)
    ]
    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(return_value=[str(_TS_BASE)])
    airq.get_historical_file = AsyncMock(return_value=measurements)

    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=airq):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T12:00:00+00:00",
            sensors=["pm10"],
            max_points=5,
        )
        data = json.loads(result)
        assert data["count"] == 5
        cols = data["columns"]
        assert "pm10" in cols
        assert "timestamp" in cols
        assert "temperature" not in cols


@pytest.mark.asyncio
async def test_get_air_quality_history_empty_data(mock_ctx):
    """Gracefully handles empty data."""
    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(return_value=[])
    airq.get_historical_file = AsyncMock(return_value=[])

    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=airq):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
        )
        data = json.loads(result)
        assert data["count"] == 0
        assert data["columns"] == {}
        assert "_sensor_guide" not in data


@pytest.mark.asyncio
async def test_get_air_quality_history_columnar_format(mock_ctx, mock_airq_with_history):
    """Returns column-oriented data with sensor guide."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
        )
        data = json.loads(result)
        assert "columns" in data
        assert "data" not in data
        assert "_sensor_guide" in data
        cols = data["columns"]
        assert "timestamp" in cols
        assert "datetime" in cols
        assert "temperature" in cols
        assert "co2" in cols
        assert "deviceid" not in cols
        assert len(cols["timestamp"]) == data["count"]


@pytest.mark.asyncio
async def test_get_air_quality_history_sensor_filter_columnar(
    mock_ctx,
    mock_airq_with_history,
):
    """Sensor filter returns only requested columns."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            sensors=["co2"],
        )
        data = json.loads(result)
        cols = data["columns"]
        assert "timestamp" in cols
        assert "co2" in cols
        assert "temperature" not in cols


@pytest.mark.asyncio
async def test_get_air_quality_history_missing_sensor(mock_ctx, mock_airq_with_history):
    """Returns error when requested sensor is not available on device."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            sensors=["radon"],
        )
        assert "not available" in result
        assert "radon" in result


@pytest.mark.asyncio
async def test_get_air_quality_history_adds_timezone_and_history_guide(mock_ctx, mock_airq_with_history):
    """Historical output includes localized timestamps and metadata guidance."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T11:00:00",
            to_datetime="2026-03-12T11:05:00",
            timezone_name="Europe/Berlin",
        )
        data = json.loads(result)
        assert data["timezone"] == "Europe/Berlin"
        assert data["columns"]["datetime"][0].endswith("+01:00")
        assert "_history_guide" in data
        assert "timestamp | s" in data["_history_guide"]


@pytest.mark.asyncio
async def test_get_air_quality_history_splits_compound_values(mock_ctx):
    """Compound sensor values are split into value and quality columns."""
    airq = AsyncMock()
    airq.get_historical_files_list = AsyncMock(return_value=[str(_TS_BASE)])
    airq.get_historical_file = AsyncMock(
        return_value=[
            {"timestamp": _TS_BASE * 1000, "co2": [400.5, 97.0]},
            {"timestamp": (_TS_BASE + 120) * 1000, "co2": [410.0, 96.0]},
        ]
    )

    with patch.object(mock_ctx.request_context.lifespan_context, "resolve", return_value=airq):
        result = await get_air_quality_history(
            mock_ctx,
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            sensors=["co2"],
        )
        data = json.loads(result)
        cols = data["columns"]
        assert cols["co2"] == [400.5, 410.0]
        assert cols["co2_quality"] == [97.0, 96.0]


@pytest.mark.asyncio
async def test_export_air_quality_history_returns_csv_resource(mock_ctx, mock_airq_with_history):
    """CSV export is returned as an embedded resource."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await export_air_quality_history(
            mock_ctx,
            sensor="co2",
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            output_format="csv",
        )
        assert isinstance(result, EmbeddedResource)
        assert isinstance(result.resource, TextResourceContents)
        assert result.resource.mimeType == "text/csv; charset=utf-8"
        lines = result.resource.text.strip().splitlines()
        assert lines[0].startswith("timestamp,")
        assert lines[1].endswith(",400.0")


@pytest.mark.asyncio
async def test_export_air_quality_history_returns_xlsx_resource(mock_ctx, mock_airq_with_history):
    """Excel export is returned as an embedded binary resource."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await export_air_quality_history(
            mock_ctx,
            sensor="co2",
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            output_format="xlsx",
        )
        assert isinstance(result, EmbeddedResource)
        assert isinstance(result.resource, BlobResourceContents)
        assert result.resource.mimeType == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        payload = base64.b64decode(result.resource.blob)
        assert payload[:2] == b"PK"


@pytest.mark.asyncio
async def test_export_air_quality_history_combines_all_devices_into_one_csv_resource(
    mock_session, multi_device_configs
):
    """Export combines all matching devices into one CSV artifact."""
    mgr = DeviceManager(mock_session, multi_device_configs)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = mgr
    named_devices = [
        ("Living Room", AsyncMock()),
        ("Office", AsyncMock()),
        ("Bedroom", AsyncMock()),
    ]
    data_by_device = [
        [{"timestamp": _TS_BASE * 1000, "co2": 400}],
        [{"timestamp": _TS_BASE * 1000, "pm2_5": 12}],
        [{"timestamp": (_TS_BASE + 120) * 1000, "co2": 420}],
    ]

    with (
        patch.object(mgr, "all_devices", return_value=named_devices),
        patch(
            "mcp_airq.tools.read._collect_historical_data",
            side_effect=data_by_device,
        ),
    ):
        result = await export_air_quality_history(
            ctx,
            sensor="co2",
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            output_format="csv",
        )

    assert isinstance(result, EmbeddedResource)
    assert isinstance(result.resource, TextResourceContents)
    assert str(result.resource.uri).endswith("history-all-devices-co2.csv")
    assert "Living Room,co2,ppm,400.0" in result.resource.text
    assert "Bedroom,co2,ppm,420.0" in result.resource.text
    assert "Office" not in result.resource.text


@pytest.mark.asyncio
async def test_plot_air_quality_history_supports_svg_resource(mock_ctx, mock_airq_with_history):
    """SVG plot output is returned as an embedded resource."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await plot_air_quality_history(
            mock_ctx,
            sensor="co2",
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            output_format="svg",
        )
        assert isinstance(result, EmbeddedResource)
        assert isinstance(result.resource, BlobResourceContents)
        assert result.resource.mimeType == "image/svg+xml"
        payload = base64.b64decode(result.resource.blob)
        assert payload.lstrip().startswith(b"<?xml")


@pytest.mark.asyncio
async def test_plot_air_quality_history_combines_all_devices_into_one_resource(mock_session, multi_device_configs):
    """Plot combines all matching devices into one multi-series chart."""
    mgr = DeviceManager(mock_session, multi_device_configs)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = mgr
    named_devices = [
        ("Living Room", AsyncMock()),
        ("Office", AsyncMock()),
        ("Bedroom", AsyncMock()),
    ]
    data_by_device = [
        [{"timestamp": _TS_BASE * 1000, "co2": 400}],
        [{"timestamp": _TS_BASE * 1000, "pm2_5": 12}],
        [{"timestamp": (_TS_BASE + 120) * 1000, "co2": 420}],
    ]
    render_result = PlotResult(output_format="svg", mime_type="image/svg+xml", payload=b"<svg/>")

    with (
        patch.object(mgr, "all_devices", return_value=named_devices),
        patch(
            "mcp_airq.tools.read._collect_historical_data",
            side_effect=data_by_device,
        ),
        patch("mcp_airq.tools.read.render", new=AsyncMock(return_value=render_result)) as render_mock,
    ):
        result = await plot_air_quality_history(
            ctx,
            sensor="co2",
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            output_format="svg",
        )

    assert isinstance(result, EmbeddedResource)
    assert isinstance(result.resource, BlobResourceContents)
    assert str(result.resource.uri).endswith("plot-all-devices-co2.svg")
    assert render_mock.await_args is not None
    model, request = render_mock.await_args.args
    assert [series.label for series in model.series] == ["Living Room", "Bedroom"]
    assert model.y_axis_title == "ppm"
    assert request.selector.devices == ["Living Room", "Bedroom"]


@pytest.mark.asyncio
async def test_plot_air_quality_history_supports_webp_image(mock_ctx, mock_airq_with_history):
    """WebP plot output is returned as an inline image."""
    with patch.object(
        mock_ctx.request_context.lifespan_context,
        "resolve",
        return_value=mock_airq_with_history,
    ):
        result = await plot_air_quality_history(
            mock_ctx,
            sensor="co2",
            from_datetime="2026-03-12T09:55:00+00:00",
            to_datetime="2026-03-12T10:05:00+00:00",
            output_format="webp",
        )
        assert isinstance(result, Image)
