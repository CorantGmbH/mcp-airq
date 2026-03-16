"""Tests for the direct CLI wrapper."""

import base64
from typing import Any, cast
from unittest.mock import AsyncMock, patch

from mcp.server.fastmcp.utilities.types import Image
from mcp.types import BlobResourceContents, EmbeddedResource, TextResourceContents

from mcp_airq.cli import main


def test_main_runs_list_devices_command(capsys):
    """A simple read command is executed and printed."""
    with patch("mcp_airq.cli._invoke_tool", new_callable=AsyncMock, return_value='["Test"]') as mock_invoke:
        result = main(["list-devices"])

    assert result == 0
    mock_invoke.assert_awaited_once_with("list_devices", {})
    captured = capsys.readouterr()
    assert captured.out == '["Test"]\n'


def test_main_accepts_snake_case_alias(capsys):
    """The original MCP tool name also works as a CLI subcommand."""
    with patch("mcp_airq.cli._invoke_tool", new_callable=AsyncMock, return_value="ok") as mock_invoke:
        result = main(["list_devices"])

    assert result == 0
    mock_invoke.assert_awaited_once_with("list_devices", {})
    assert capsys.readouterr().out == "ok\n"


def test_main_parses_optional_booleans():
    """Boolean optional flags are mapped to the tool arguments."""
    with patch("mcp_airq.cli._invoke_tool", new_callable=AsyncMock, return_value="ok") as mock_invoke:
        main(
            [
                "get-air-quality",
                "--location",
                "Living Room",
                "--no-return-average",
                "--no-clip-negative",
                "--include-uncertainties",
            ]
        )

    mock_invoke.assert_awaited_once_with(
        "get_air_quality",
        {
            "device": None,
            "location": "Living Room",
            "group": None,
            "return_average": False,
            "clip_negative": False,
            "include_uncertainties": True,
        },
    )


def test_main_parses_required_boolean():
    """Required booleans are exposed as --flag / --no-flag."""
    with patch("mcp_airq.cli._invoke_tool", new_callable=AsyncMock, return_value="ok") as mock_invoke:
        main(["set-night-mode", "--activated", "--device", "Bedroom"])

    mock_invoke.assert_awaited_once_with(
        "set_night_mode",
        {
            "activated": True,
            "start_night": "22:00",
            "start_day": "06:00",
            "brightness_day": 100.0,
            "brightness_night": 0.0,
            "fan_night_off": False,
            "wifi_night_off": False,
            "alarm_night_off": False,
            "device": "Bedroom",
        },
    )


def test_main_compacts_json_for_pipes(capsys):
    """Structured JSON can be emitted without whitespace."""
    with patch(
        "mcp_airq.cli._invoke_tool",
        new_callable=AsyncMock,
        return_value='{\n  "co2": 800,\n  "temperature": 21.5\n}',
    ):
        result = main(["get-air-quality", "--device", "Living Room", "--compact-json"])

    assert result == 0
    assert capsys.readouterr().out == '{"co2":800,"temperature":21.5}\n'


def test_main_can_render_yaml(capsys):
    """Structured JSON can be emitted as YAML."""
    with patch(
        "mcp_airq.cli._invoke_tool",
        new_callable=AsyncMock,
        return_value='{"co2": 800, "labels": ["home", "living-room"]}',
    ):
        result = main(["get-air-quality", "--device", "Living Room", "--yaml"])

    assert result == 0
    assert capsys.readouterr().out == 'co2: 800\nlabels:\n  - "home"\n  - "living-room"\n'


def test_main_prints_export_csv_resource(capsys):
    """Text resources are emitted as their payload, not as model reprs."""
    text = "timestamp,series,metric,unit,value\n2026-03-16T10:00:00+01:00,Living Room,co2,ppm,700.0\n"
    resource = EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=cast(Any, "airq://artifacts/history-all-devices-co2.csv"),
            mimeType="text/csv; charset=utf-8",
            text=text,
        ),
    )

    with patch("mcp_airq.cli._invoke_tool", new_callable=AsyncMock, return_value=resource):
        result = main(["export-air-quality-history", "--sensor", "co2", "--output-format", "csv"])

    assert result == 0
    assert capsys.readouterr().out == text


def test_main_writes_export_xlsx_resource(tmp_path, capsys):
    """Binary resources are decoded and written to the requested file."""
    output = tmp_path / "co2.xlsx"
    resource = EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            uri=cast(Any, "airq://artifacts/history-all-devices-co2.xlsx"),
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            blob=base64.b64encode(b"xlsx-bytes").decode(),
        ),
    )

    with patch("mcp_airq.cli._invoke_tool", new_callable=AsyncMock, return_value=resource):
        result = main(
            [
                "export-air-quality-history",
                "--sensor",
                "co2",
                "--output-format",
                "xlsx",
                "--output",
                str(output),
            ]
        )

    assert result == 0
    assert output.read_bytes() == b"xlsx-bytes"
    assert capsys.readouterr().out == f"{output}\n"


def test_main_writes_plot_image(tmp_path, capsys):
    """PNG plots are written to the requested file path."""
    output = tmp_path / "co2.png"
    image = Image(data=b"png-bytes", format="png")

    with patch("mcp_airq.cli._invoke_tool", new_callable=AsyncMock, return_value=image):
        result = main(
            [
                "plot-air-quality-history",
                "--sensor",
                "co2",
                "--device",
                "Living Room",
                "--output",
                str(output),
            ]
        )

    assert result == 0
    assert output.read_bytes() == b"png-bytes"
    assert capsys.readouterr().out == f"{output}\n"


def test_main_returns_non_zero_for_tool_errors(capsys):
    """Tool error strings are written to stderr with a failure exit code."""
    with patch(
        "mcp_airq.cli._invoke_tool",
        new_callable=AsyncMock,
        return_value="Configuration error: missing device",
    ) as mock_invoke:
        result = main(["list-devices"])

    assert result == 1
    mock_invoke.assert_awaited_once_with("list_devices", {})
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Configuration error: missing device\n"
