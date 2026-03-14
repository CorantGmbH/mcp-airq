"""Tests for server entry point and lifespan."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_airq.devices import DeviceManager
from mcp_airq.server import app_lifespan, main


def test_main_version(capsys):
    """--version prints version string and exits."""
    with patch("sys.argv", ["mcp-airq", "--version"]):
        main()
    captured = capsys.readouterr()
    assert "mcp-airq" in captured.out


def test_main_help(capsys):
    """--help prints help text and exits."""
    with patch("sys.argv", ["mcp-airq", "--help"]):
        main()
    captured = capsys.readouterr()
    assert "MCP" in captured.out or "mcp-airq" in captured.out


def test_main_tty_shows_help(capsys):
    """When stdin is a tty (interactive terminal), help text is shown."""
    with patch("sys.argv", ["mcp-airq"]), patch("sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = True
        main()
    captured = capsys.readouterr()
    assert "mcp-airq" in captured.out


def test_main_runs_server():
    """When stdin is not a tty, mcp.run() is called."""
    with (
        patch("sys.argv", ["mcp-airq"]),
        patch("sys.stdin") as mock_stdin,
        patch("mcp_airq.server.mcp") as mock_mcp,
    ):
        mock_stdin.isatty.return_value = False
        main()
        mock_mcp.run.assert_called_once_with(transport="stdio")


def test_main_serve_runs_server():
    """The explicit serve command forces MCP server mode."""
    with patch("sys.argv", ["mcp-airq", "serve"]), patch("mcp_airq.server.mcp") as mock_mcp:
        main()
        mock_mcp.run.assert_called_once_with(transport="stdio")


def test_main_cli_delegates_to_run_cli():
    """CLI subcommands are delegated to the direct CLI implementation."""
    with (
        patch("sys.argv", ["mcp-airq", "list-devices"]),
        patch("mcp_airq.server.run_cli") as mock_run_cli,
    ):
        main()
        mock_run_cli.assert_called_once_with(["list-devices"])


@pytest.mark.asyncio
async def test_app_lifespan():
    """app_lifespan yields a DeviceManager and closes the session."""
    configs = [MagicMock(address="10.0.0.1", password="pw", name="Test")]
    with patch("mcp_airq.server.load_config", return_value=configs):
        async with app_lifespan(MagicMock()) as mgr:
            assert isinstance(mgr, DeviceManager)
