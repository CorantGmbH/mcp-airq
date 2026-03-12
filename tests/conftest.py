"""Shared test fixtures."""

# pylint: disable=redefined-outer-name
from unittest.mock import MagicMock

import pytest

from mcp_airq.config import DeviceConfig
from mcp_airq.devices import DeviceManager


@pytest.fixture
def mock_session():
    """A mock aiohttp.ClientSession."""
    return MagicMock()


@pytest.fixture
def single_device_configs():
    """Config list with one device."""
    return [DeviceConfig("192.168.1.100", "testpass", "TestDevice")]


@pytest.fixture
def multi_device_configs():
    """Config list with multiple devices, some sharing a location and group."""
    return [
        DeviceConfig(
            "192.168.1.100",
            "pass1",
            "Living Room",
            location="Wohnzimmer",
            group="zu Hause",
        ),
        DeviceConfig("192.168.1.101", "pass2", "Office", group="Arbeit"),
        DeviceConfig(
            "192.168.1.102", "pass3", "Bedroom", location="Wohnzimmer", group="zu Hause"
        ),
    ]


@pytest.fixture
def single_device_manager(mock_session, single_device_configs):
    """DeviceManager with one device."""
    return DeviceManager(mock_session, single_device_configs)


@pytest.fixture
def multi_device_manager(mock_session, multi_device_configs):
    """DeviceManager with multiple devices."""
    return DeviceManager(mock_session, multi_device_configs)


@pytest.fixture
def mock_ctx(single_device_manager):
    """Create a mock Context with the device manager as lifespan context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = single_device_manager
    return ctx
