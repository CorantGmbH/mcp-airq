"""Shared test fixtures."""

import pytest
from unittest.mock import MagicMock

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
    """Config list with multiple devices."""
    return [
        DeviceConfig("192.168.1.100", "pass1", "Living Room"),
        DeviceConfig("192.168.1.101", "pass2", "Office"),
        DeviceConfig("192.168.1.102", "pass3", "Bedroom"),
    ]


@pytest.fixture
def single_device_manager(mock_session, single_device_configs):
    """DeviceManager with one device."""
    return DeviceManager(mock_session, single_device_configs)


@pytest.fixture
def multi_device_manager(mock_session, multi_device_configs):
    """DeviceManager with multiple devices."""
    return DeviceManager(mock_session, multi_device_configs)
