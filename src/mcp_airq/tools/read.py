"""Read-only tools for querying air-Q devices."""

import base64
import json
import logging
import re
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Literal, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import aiohttp
from aioairq import AirQ
from airq_mcp_timeseries.models import (
    PlotRequest,
    PlotResult,
    PlotStyle,
    Selector,
    SeriesPoint,
    SeriesSet,
    TimeSeries,
)
from airq_mcp_timeseries.renderers import render
from airq_mcp_timeseries.services.export import export_series_set
from airq_mcp_timeseries.services.plot_model import build_plot_model
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.utilities.types import Image
from mcp.types import BlobResourceContents, EmbeddedResource, TextResourceContents, ToolAnnotations
from pydantic import AnyUrl

from mcp_airq.errors import handle_airq_errors
from mcp_airq.guides import CONFIG_GUIDE, build_sensor_guide, sensor_unit
from mcp_airq.server import mcp
from mcp_airq.tools._helpers import _json, _manager, _resolve

logger = logging.getLogger(__name__)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
_META_KEYS = {"datetime", "timestamp", "deviceid"}
_FILE_BUFFER_S = 300  # seconds of slack when pre-filtering file names


# ---------------------------------------------------------------------------
# Helpers for historical tools
# ---------------------------------------------------------------------------


def _effective_timezone(timezone_name: str | None) -> tuple[timezone | ZoneInfo, str]:
    """Resolve a user-provided timezone name or default to UTC."""
    if timezone_name in (None, "", "UTC"):
        return timezone.utc, "UTC"
    try:
        return ZoneInfo(timezone_name), timezone_name
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone_name}") from exc


def _parse_time_range(
    now: datetime,
    last_hours: float | None,
    from_datetime: str | None,
    to_datetime: str | None,
    timezone_name: str | None = None,
) -> tuple[datetime, datetime, str] | str:
    """Parse time range parameters. Returns UTC datetimes plus effective timezone name."""
    zone, zone_name = _effective_timezone(timezone_name)

    if from_datetime is not None:
        from_dt = datetime.fromisoformat(from_datetime)
        if from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=zone)
        else:
            from_dt = from_dt.astimezone(zone)
        to_dt = now.astimezone(zone)
        if to_datetime is not None:
            to_dt = datetime.fromisoformat(to_datetime)
            if to_dt.tzinfo is None:
                to_dt = to_dt.replace(tzinfo=zone)
            else:
                to_dt = to_dt.astimezone(zone)
    else:
        hours = last_hours if last_hours is not None else 1.0
        if hours <= 0:
            return "last_hours must be positive."
        to_dt = now.astimezone(zone)
        from_dt = to_dt - timedelta(hours=hours)

    if from_dt >= to_dt:
        return "from_datetime must be before to_datetime."

    return from_dt.astimezone(timezone.utc), to_dt.astimezone(timezone.utc), zone_name


def _filter_sensors(data: list[dict], sensors: list[str]) -> list[dict]:
    """Keep only the requested sensor keys (plus metadata) in each entry."""
    keep = {s.lower() for s in sensors} | _META_KEYS
    return [{k: v for k, v in entry.items() if k.lower() in keep} for entry in data]


def _check_sensors_present(
    data: list[dict],
    sensors: list[str],
) -> str | None:
    """Return an error string if any requested sensors are missing from the data."""
    if not data or not sensors:
        return None
    present = set().union(*(e.keys() for e in data)) - _META_KEYS
    missing = {s.lower() for s in sensors} - {k.lower() for k in present}
    if missing:
        available = sorted(k for k in present if k.lower() not in _META_KEYS)
        msg = f"Sensor(s) not available on this device: {', '.join(sorted(missing))}."
        if available:
            msg += f" Available: {', '.join(available)}."
        return msg
    return None


def _downsample(data: list[dict], max_points: int) -> list[dict]:
    """Evenly downsample a list to at most max_points entries."""
    n = len(data)
    if n <= max_points:
        return data
    step = n / max_points
    return [data[int(i * step)] for i in range(max_points)]


def _history_sensor_keys(data: list[dict]) -> set[str]:
    """Return the sensor keys present in historical rows, excluding metadata."""
    keys: set[str] = set()
    for row in data:
        keys.update(k for k in row if k not in _META_KEYS)
    return keys


def _quality_column_names(raw_value: object, key: str) -> list[str]:
    """Determine derived column names for compound sensor values."""
    if not isinstance(raw_value, (list, tuple)):
        return []
    if len(raw_value) <= 1:
        return []
    if len(raw_value) == 2:
        return [f"{key}_quality"]
    return [f"{key}_{index}" for index in range(1, len(raw_value))]


def _to_columnar(data: list[dict], timezone_name: str) -> dict[str, list]:
    """Convert row-oriented data to column-oriented format with localized datetimes.

    Drops ``deviceid``. ``timestamp`` is returned as Unix seconds. ``datetime`` is
    added as localized ISO 8601 text for readability and spreadsheet exports.
    Compound values like ``[value, quality]`` are split into dedicated columns.
    """
    if not data:
        return {}

    zone, _ = _effective_timezone(timezone_name)
    sensor_keys = sorted(_history_sensor_keys(data))
    derived_keys: list[str] = []
    for key in sensor_keys:
        seen: set[str] = set()
        for row in data:
            for derived in _quality_column_names(row.get(key), key):
                if derived not in seen:
                    derived_keys.append(derived)
                    seen.add(derived)

    columns: dict[str, list] = {"timestamp": [], "datetime": []}
    for key in sensor_keys:
        columns[key] = []
    for key in derived_keys:
        columns[key] = []

    for row in data:
        ts_ms = int(row.get("timestamp", 0) or 0)
        columns["timestamp"].append(ts_ms // 1000)
        columns["datetime"].append(datetime.fromtimestamp(ts_ms / 1000, tz=zone).isoformat())

        for key in sensor_keys:
            raw_value = row.get(key)
            if isinstance(raw_value, (list, tuple)):
                primary = raw_value[0] if len(raw_value) >= 1 else None
                columns[key].append(primary)
                extras = _quality_column_names(raw_value, key)
                for index, derived in enumerate(extras, start=1):
                    columns[derived].append(raw_value[index] if len(raw_value) > index else None)
            else:
                columns[key].append(raw_value)
                for derived in [
                    name for name in derived_keys if name == f"{key}_quality" or name.startswith(f"{key}_")
                ]:
                    columns[derived].append(None)

    return columns


def _history_guide(timezone_name: str, data: list[dict]) -> str:
    """Describe non-sensor history output columns added by this MCP server."""
    has_compound = any(
        isinstance(value, (list, tuple)) and len(value) > 1
        for row in data
        for key, value in row.items()
        if key not in _META_KEYS
    )

    lines = [
        "# History Output Guide",
        "",
        "| Key | Unit | Notes |",
        "|---|---|---|",
        "| timestamp | s | Unix epoch in seconds. |",
        f"| datetime | ISO 8601 | Timestamp rendered in timezone `{timezone_name}`. |",
    ]
    if has_compound:
        lines.append(
            "| `<sensor>_quality` | % | Quality/confidence value when the raw device history returns `[value, quality]`. |"
        )
    return "\n".join(lines)


def _lower_keys(data: dict) -> dict:
    """Lowercase all dict keys."""
    return {k.lower(): v for k, v in data.items()}


def _series_value(row: dict, sensor: str) -> float | None:
    """Extract a numeric value for one sensor from a raw history row."""
    val_raw = row.get(sensor)
    if val_raw is None:
        return None
    if isinstance(val_raw, (list, tuple)):
        val_raw = val_raw[0] if val_raw else None
    try:
        return float(val_raw) if val_raw is not None else None
    except (TypeError, ValueError):
        return None


def _rows_to_time_series(
    device_label: str,
    sensor: str,
    data: list[dict],
    timezone_name: str,
) -> TimeSeries:
    """Convert raw device rows to one TimeSeries."""
    key = sensor.lower()
    zone, _ = _effective_timezone(timezone_name)
    points = []
    for row in data:
        ts_ms = int(row.get("timestamp", 0) or 0)
        ts_iso = datetime.fromtimestamp(ts_ms / 1000, tz=zone).isoformat()
        points.append(SeriesPoint(ts=ts_iso, value=_series_value(row, key)))
    return TimeSeries(id=device_label, label=device_label, unit=sensor_unit(key), points=points)


def _build_series_set(
    sensor: str,
    series: list[TimeSeries],
    from_dt: datetime,
    to_dt: datetime,
    timezone_name: str,
) -> SeriesSet:
    """Build a SeriesSet spanning one or more devices for the same metric."""
    zone, _ = _effective_timezone(timezone_name)
    return SeriesSet(
        metric=sensor.lower(),
        series=series,
        start=from_dt.astimezone(zone).isoformat(),
        end=to_dt.astimezone(zone).isoformat(),
    )


def _resolved_device_label(device_names: Sequence[str], device: str | None) -> str:
    """Resolve a requested device name to the concrete configured label."""
    if device is None:
        if len(device_names) == 1:
            return device_names[0]
        raise ValueError(f"Multiple devices configured. Specify one of: {', '.join(device_names)}")
    if device in device_names:
        return device
    needle = device.lower()
    matches = [name for name in device_names if needle in name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"No device matching '{device}'. Available: {', '.join(device_names)}")
    raise ValueError(f"Ambiguous device '{device}'. Matches: {', '.join(matches)}")


def _resolve_history_targets(
    mgr,
    device: str | None,
    location: str | None,
    group: str | None,
) -> tuple[str, Sequence[tuple[str, AirQ]], Selector] | str:
    """Resolve one historical query target set from device/location/group/all."""
    selectors = [x for x in (device, location, group) if x is not None]
    if len(selectors) > 1:
        return "Specify at most one of 'device', 'location', or 'group'."

    if location is not None:
        return location, mgr.resolve_location(location), Selector(location=location)
    if group is not None:
        return group, mgr.resolve_group(group), Selector(group=group)
    if device is not None:
        label = _resolved_device_label(mgr.device_names, device)
        return label, [(label, mgr.resolve(device))], Selector(devices=[label])
    if len(mgr.device_names) == 1:
        label = mgr.device_names[0]
        return label, [(label, mgr.resolve(None))], Selector(devices=[label])
    named_devices = mgr.all_devices()
    return "all-devices", named_devices, Selector(devices=[name for name, _ in named_devices])


def _sensor_not_available_message(sensor: str, available: set[str]) -> str:
    """Build a consistent error for sensors missing from all selected devices."""
    msg = f"Sensor(s) not available on the selected devices: {sensor.lower()}."
    if available:
        msg += f" Available: {', '.join(sorted(available))}."
    return msg


async def _collect_series_for_targets(
    named_devices: Sequence[tuple[str, AirQ]],
    sensor: str,
    from_dt: datetime,
    to_dt: datetime,
    max_points: int,
    timezone_name: str,
) -> SeriesSet | str:
    """Fetch one metric for multiple devices and merge them into one SeriesSet."""
    key = sensor.lower()
    series: list[TimeSeries] = []
    available: set[str] = set()
    saw_rows = False

    for device_label, airq in named_devices:
        data = await _collect_historical_data(airq, from_dt, to_dt)
        data = [_lower_keys(row) for row in data]
        if data:
            saw_rows = True
            available.update(_history_sensor_keys(data))
        if _check_sensors_present(data, [key]):
            continue
        if max_points > 0:
            data = _downsample(data, max_points)
        time_series = _rows_to_time_series(device_label, key, data, timezone_name)
        if time_series.points:
            series.append(time_series)

    if series:
        return _build_series_set(key, series, from_dt, to_dt, timezone_name)
    if not saw_rows:
        return "No historical data returned for the selected devices in the requested time range."
    return _sensor_not_available_message(key, available)


async def _collect_historical_data(airq: AirQ, from_dt: datetime, to_dt: datetime) -> list[dict]:
    """Download historical data files from the device and filter to the requested time range."""
    from_ms = int(from_dt.timestamp() * 1000)
    to_ms = int(to_dt.timestamp() * 1000)
    from_s = from_ms // 1000
    to_s = to_ms // 1000

    all_data: list[dict] = []
    current_date = from_dt.date()
    end_date = to_dt.date()

    while current_date <= end_date:
        day_path = f"{current_date.year}/{current_date.month}/{current_date.day}"
        try:
            file_names = await airq.get_historical_files_list(day_path)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 404:
                logger.debug("No historical data for %s (HTTP 404)", day_path)
                current_date += timedelta(days=1)
                continue
            raise
        except aiohttp.ClientError:
            logger.debug("Could not list historical files for %s", day_path, exc_info=True)
            current_date += timedelta(days=1)
            continue

        for name in file_names:
            try:
                file_ts = int(name)
            except ValueError:
                continue
            if file_ts < from_s - _FILE_BUFFER_S or file_ts > to_s:
                continue

            file_path = f"{day_path}/{name}"
            try:
                measurements = await airq.get_historical_file(file_path)
            except aiohttp.ClientError:
                logger.debug("Could not download %s", file_path, exc_info=True)
                continue

            for entry in measurements:
                ts = entry.get("timestamp", 0)
                if from_ms <= ts <= to_ms:
                    all_data.append(entry)

        current_date += timedelta(days=1)

    all_data.sort(key=lambda m: m.get("timestamp", 0))
    return all_data


def _slugify(value: str) -> str:
    """Build a stable ASCII-only file stem for exported artifacts."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "airq"


def _artifact_name(prefix: str, device_label: str, sensor: str, output_format: str) -> str:
    """Build a synthetic artifact filename for embedded resources."""
    return f"{_slugify(prefix)}-{_slugify(device_label)}-{_slugify(sensor)}.{output_format}"


def _resource_from_payload(filename: str, payload: bytes | str, mime_type: str) -> EmbeddedResource:
    """Wrap exported bytes/text as an embedded MCP resource."""
    uri = cast(AnyUrl, f"airq://artifacts/{filename}")
    if isinstance(payload, str):
        resource = TextResourceContents(uri=uri, mimeType=mime_type, text=payload)
    else:
        resource = BlobResourceContents(uri=uri, mimeType=mime_type, blob=base64.b64encode(payload).decode())
    return EmbeddedResource(type="resource", resource=resource)


def _plot_output(
    result: PlotResult,
    device_label: str,
    sensor: str,
    output_format: str,
) -> Image | EmbeddedResource:
    """Convert a renderer payload into the most suitable MCP return type."""
    if output_format in {"png", "webp"}:
        assert isinstance(result.payload, bytes)
        return Image(data=result.payload, format=output_format)
    if output_format == "html":
        assert isinstance(result.payload, str)
        return _resource_from_payload(
            _artifact_name("plot", device_label, sensor, output_format),
            result.payload,
            result.mime_type,
        )
    assert isinstance(result.payload, bytes)
    return _resource_from_payload(
        _artifact_name("plot", device_label, sensor, output_format),
        result.payload,
        result.mime_type,
    )


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def list_devices(ctx: Context) -> str:
    """List all configured air-Q devices with their names, addresses, locations, and groups."""
    mgr = _manager(ctx)
    devices = []
    for name in mgr.device_names:
        cfg = mgr.get_config_for(name)
        entry: dict[str, str] = {"name": name, "address": cfg.address}
        if cfg.location is not None:
            entry["location"] = cfg.location
        if cfg.group is not None:
            entry["group"] = cfg.group
        devices.append(entry)
    return _json(devices)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_air_quality(
    ctx: Context,
    device: str | None = None,
    location: str | None = None,
    group: str | None = None,
    return_average: bool = True,
    clip_negative: bool = True,
    include_uncertainties: bool = False,
) -> str:
    """Get current air quality sensor readings from one or more devices.

    Specify exactly one of:
    - 'device' — query a single device by name
    - 'location' — query all devices at a given location (e.g. "Wohnzimmer")
    - 'group' — query all devices in a group (e.g. "zu Hause")

    When using 'location' or 'group', the response contains one entry per
    device. Returns sensor names mapped to values. Set return_average=True
    for time-averaged data (recommended) or False for instantaneous readings.
    The response includes a _sensor_guide field with full unit and index
    documentation — read it before interpreting any values.
    """
    mgr = _manager(ctx)

    selectors = [x for x in (device, location, group) if x is not None]
    if len(selectors) > 1:
        return "Specify at most one of 'device', 'location', or 'group'."

    multi_devices: Sequence[tuple[str, AirQ]] | None = None
    if location is not None:
        multi_devices = mgr.resolve_location(location)
    elif group is not None:
        multi_devices = mgr.resolve_group(group)

    if multi_devices is not None:
        results: dict[str, object] = {}
        all_keys: set[str] = set()
        for name, airq in multi_devices:
            data = await airq.get_latest_data(
                return_average=return_average,
                clip_negative_values=clip_negative,
                return_uncertainties=include_uncertainties,
            )
            data = _lower_keys(data)
            results[name] = data
            all_keys.update(data.keys())
        results["_sensor_guide"] = build_sensor_guide(all_keys)
        return _json(results)

    airq = mgr.resolve(device)
    data = await airq.get_latest_data(
        return_average=return_average,
        clip_negative_values=clip_negative,
        return_uncertainties=include_uncertainties,
    )
    data = _lower_keys(data)
    data["_sensor_guide"] = build_sensor_guide(set(data.keys()))
    return _json(data)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_device_info(ctx: Context, device: str | None = None) -> str:
    """Get device metadata: ID, name, model, firmware/hardware version, and suggested area."""
    _, airq = _resolve(ctx, device)
    info = await airq.fetch_device_info()
    return _json(dict(info))


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_config(ctx: Context, device: str | None = None) -> str:
    """Get the full configuration of a device as a JSON dict.

    The response includes a _config_guide field with full documentation of
    all configuration keys — read it before interpreting or modifying values.
    """
    _, airq = _resolve(ctx, device)
    config = await airq.get_config()
    config["_config_guide"] = CONFIG_GUIDE
    return _json(config)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_logs(ctx: Context, device: str | None = None) -> str:
    """Get log entries from a device."""
    _, airq = _resolve(ctx, device)
    logs = await airq.get_log()
    return _json(logs)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def identify_device(ctx: Context, device: str | None = None) -> str:
    """Make a device blink its LEDs in rainbow colors for visual identification. Returns the device ID."""
    _, airq = _resolve(ctx, device)
    device_id = await airq.blink()
    return f"Device is blinking. Device ID: {device_id}"


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_led_theme(ctx: Context, device: str | None = None) -> str:
    """Get the current LED visualization theme for both sides of a device."""
    _, airq = _resolve(ctx, device)
    theme = await airq.get_led_theme()
    return _json(theme)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_possible_led_themes(ctx: Context, device: str | None = None) -> str:
    """List all available LED visualization themes for a device."""
    _, airq = _resolve(ctx, device)
    themes = await airq.get_possible_led_themes()
    return _json(themes)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_night_mode(ctx: Context, device: str | None = None) -> str:
    """Get the current night mode configuration of a device."""
    _, airq = _resolve(ctx, device)
    night_mode = await airq.get_night_mode()
    return _json(night_mode)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_brightness_config(ctx: Context, device: str | None = None) -> str:
    """Get the current LED brightness configuration (day and night values) of a device."""
    _, airq = _resolve(ctx, device)
    brightness = await airq.get_brightness_config()
    return _json(brightness)


@mcp.tool(annotations=READ_ONLY)
@handle_airq_errors
async def get_air_quality_history(
    ctx: Context,
    device: str | None = None,
    last_hours: float | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    sensors: list[str] | None = None,
    max_points: int | None = None,
    timezone_name: str | None = None,
) -> str:
    """Get historical air quality data stored on the device's SD card.

    IMPORTANT — 'sensors' must be a JSON array, not a plain string.
      Correct:   sensors=["pm1","pm2_5"]
      Wrong:     sensors="pm1"

    IMPORTANT — response size: air-Q records every ~2 minutes, so long ranges
    produce large responses (24 h ≈ 720 readings × ~25 sensors). Always use
    'sensors' and 'max_points' when querying more than 1–2 hours to stay within
    response size limits. Example for a 24 h chart: sensors=["pm1","pm2_5","pm10"],
    max_points=150.

    Time range — specify one of:
    - 'last_hours' — data from the last N hours (default: 1 hour)
    - 'from_datetime' / 'to_datetime' — ISO 8601 strings
      (e.g. "2026-03-10T14:00:00" or "2026-03-10T14:00:00+01:00")
      'from_datetime' takes precedence over 'last_hours'.
      'to_datetime' defaults to now.
    - 'timezone_name' — optional IANA timezone such as "Europe/Berlin".
      Naive datetimes are interpreted in this timezone. Output timestamps are
      localized into `datetime` using the same timezone.

    Optional filtering:
    - 'sensors' — list of sensor names to include (e.g. ["pm1", "pm2_5", "pm10"]).
      Omit to get all sensors.
    - 'max_points' — downsample to at most this many evenly spaced points.

    Response: column-oriented JSON with `timestamp` (Unix seconds) and localized
    `datetime` columns. Compound sensor values like `[value, quality]` are split
    into `<sensor>` and `<sensor>_quality`. Includes `_sensor_guide` and
    `_history_guide`.
    """
    _, airq = _resolve(ctx, device)

    time_range = _parse_time_range(
        datetime.now(timezone.utc),
        last_hours,
        from_datetime,
        to_datetime,
        timezone_name=timezone_name,
    )
    if isinstance(time_range, str):
        return time_range
    from_dt, to_dt, effective_timezone = time_range

    data = await _collect_historical_data(airq, from_dt, to_dt)
    data = [_lower_keys(row) for row in data]

    if sensors:
        error = _check_sensors_present(data, sensors)
        if error:
            return error
        data = _filter_sensors(data, sensors)

    if max_points is not None and max_points > 0:
        data = _downsample(data, max_points)

    sensor_keys = _history_sensor_keys(data)
    zone, _ = _effective_timezone(effective_timezone)
    result: dict[str, object] = {
        "from": from_dt.astimezone(zone).isoformat(),
        "to": to_dt.astimezone(zone).isoformat(),
        "timezone": effective_timezone,
        "count": len(data),
        "columns": _to_columnar(data, effective_timezone),
        "_history_guide": _history_guide(effective_timezone, data),
    }
    guide = build_sensor_guide(sensor_keys)
    if guide:
        result["_sensor_guide"] = guide
    return json.dumps(result, separators=(",", ":"), default=str)


@mcp.tool(annotations=READ_ONLY, structured_output=False)
@handle_airq_errors
async def export_air_quality_history(
    ctx: Context,
    sensor: str,
    device: str | None = None,
    location: str | None = None,
    group: str | None = None,
    last_hours: float | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    output_format: Literal["csv", "xlsx"] = "csv",
    max_points: int = 300,
    timezone_name: str | None = None,
) -> EmbeddedResource | str:
    """Export historical air-Q sensor data as CSV or Excel.

    Selector:
    - `device` — one specific device
    - `location` — all devices at one location
    - `group` — all devices in one group
    - if none is specified, all configured devices are exported together

    OUTPUT FORMAT:
    - "csv" — one UTF-8 CSV file containing all selected devices
    - "xlsx" — one Excel workbook containing all selected devices

    REQUIRED:
    - sensor: one sensor key to export, for example `co2`, `pm2_5`, `radon`

    TIME RANGE:
    - `last_hours` or `from_datetime` / `to_datetime`
    - `timezone_name` controls how timestamps are rendered in the exported file
    """
    mgr = _manager(ctx)
    target_resolution = _resolve_history_targets(mgr, device, location, group)
    if isinstance(target_resolution, str):
        return target_resolution
    scope_label, named_devices, _ = target_resolution

    time_range = _parse_time_range(
        datetime.now(timezone.utc),
        last_hours,
        from_datetime,
        to_datetime,
        timezone_name=timezone_name,
    )
    if isinstance(time_range, str):
        return time_range
    from_dt, to_dt, effective_timezone = time_range

    series_set = await _collect_series_for_targets(
        named_devices,
        sensor,
        from_dt,
        to_dt,
        max_points,
        effective_timezone,
    )
    if isinstance(series_set, str):
        return series_set

    key = sensor.lower()
    export = export_series_set(series_set, output_format=output_format)
    return _resource_from_payload(
        _artifact_name("history", scope_label, key, output_format),
        export.payload,
        export.mime_type,
    )


@mcp.tool(annotations=READ_ONLY, structured_output=False)
async def plot_air_quality_history(
    ctx: Context,
    sensor: str,
    device: str | None = None,
    location: str | None = None,
    group: str | None = None,
    last_hours: float | None = None,
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    title: str | None = None,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
    chart_type: Literal["line", "area"] = "area",
    dark: bool = False,
    output_format: Literal["png", "html", "svg", "webp"] = "png",
    max_points: int = 300,
    timezone_name: str | None = None,
) -> Image | EmbeddedResource | str:
    """Generate a chart of historical air-Q sensor data.

    WHEN TO USE THIS TOOL: Call this whenever the user asks to see a graph,
    chart, plot, or visual representation of historical sensor data.

    Selector:
    - `device` — one specific device
    - `location` — all devices at one location
    - `group` — all devices in one group
    - if none is specified, all configured devices are plotted together

    OUTPUT FORMAT:
    - "png" (default) — one inline image containing all selected devices
    - "webp" — inline image with smaller payload size
    - "svg" — vector graphic as downloadable MCP resource
    - "html" — self-contained interactive HTML as downloadable MCP resource

    REQUIRED:
    - sensor: the sensor key to visualise (one sensor per chart)

    TIME RANGE:
    - `last_hours` or `from_datetime` / `to_datetime`
    - `timezone_name` controls how timestamps are rendered on the X axis and
      how naive input datetimes are interpreted
    """
    try:
        mgr = _manager(ctx)
        target_resolution = _resolve_history_targets(mgr, device, location, group)
        if isinstance(target_resolution, str):
            return target_resolution
        scope_label, named_devices, selector = target_resolution

        effective_hours = last_hours if last_hours is not None else 24.0
        time_range = _parse_time_range(
            datetime.now(timezone.utc),
            effective_hours,
            from_datetime,
            to_datetime,
            timezone_name=timezone_name,
        )
        if isinstance(time_range, str):
            return time_range
        from_dt, to_dt, effective_timezone = time_range

        series_set = await _collect_series_for_targets(
            named_devices,
            sensor,
            from_dt,
            to_dt,
            max_points,
            effective_timezone,
        )
        if isinstance(series_set, str):
            return series_set

        selector = Selector(
            devices=[series.label for series in series_set.series],
            location=selector.location,
            group=selector.group,
        )
        key = sensor.lower()

        request = PlotRequest(
            selector=selector,
            metric=key,
            start=from_dt,
            end=to_dt,
            chart_type=chart_type,
            timezone=effective_timezone,
            output_format=output_format,
            style=PlotStyle(
                title=title,
                x_axis_title=x_axis_title,
                y_axis_title=y_axis_title,
                dark=dark,
            ),
        )

        model = build_plot_model(series_set, request)
        result = await render(model, request)
        return _plot_output(result, scope_label, key, output_format)

    except ValueError as exc:
        return f"Configuration error: {exc}"
    except aiohttp.ClientError as exc:
        return f"Network error: {type(exc).__name__}: {exc}"
    except TimeoutError:
        return "Request timed out. Check that the device is on the same network and powered on."
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("plot_air_quality_history failed: %s", exc, exc_info=True)
        return f"Chart rendering failed: {exc}"
