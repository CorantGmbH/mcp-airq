"""Tests for package __init__ and prompts."""

import importlib
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import mcp_airq
from mcp_airq.prompts import airq_config_guide, airq_sensor_guide


def test_version_fallback():
    """When package metadata is unavailable, __version__ defaults to '0.0.0'."""
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        importlib.reload(mcp_airq)
        assert mcp_airq.__version__ == "0.0.0"


def test_prompts_return_strings():
    """Both MCP prompt functions return non-empty strings."""
    assert isinstance(airq_sensor_guide(), str)
    assert len(airq_sensor_guide()) > 0
    assert isinstance(airq_config_guide(), str)
    assert len(airq_config_guide()) > 0
