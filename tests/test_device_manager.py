"""Tests for DeviceManager device resolution."""

import pytest
from aioairq import AirQ


def test_device_names(multi_device_manager):
    """device_names returns all configured names."""
    assert multi_device_manager.device_names == [
        "Living Room",
        "Office",
        "Bedroom",
    ]


def test_single_device_auto_resolve(single_device_manager):
    """With one device, resolve(None) returns it."""
    airq = single_device_manager.resolve(None)
    assert isinstance(airq, AirQ)


def test_multi_device_none_raises(multi_device_manager):
    """With multiple devices, resolve(None) raises."""
    with pytest.raises(ValueError, match="Multiple devices"):
        multi_device_manager.resolve(None)


def test_exact_match(multi_device_manager):
    """Exact name match works."""
    airq = multi_device_manager.resolve("Office")
    assert isinstance(airq, AirQ)


def test_substring_match(multi_device_manager):
    """Case-insensitive substring match works."""
    airq = multi_device_manager.resolve("office")
    assert isinstance(airq, AirQ)


def test_partial_match(multi_device_manager):
    """Partial name match works if unambiguous."""
    airq = multi_device_manager.resolve("Bed")
    assert isinstance(airq, AirQ)


def test_ambiguous_match_raises(multi_device_manager):
    """Ambiguous substring raises."""
    # "room" matches "Living Room" and "Bedroom"
    with pytest.raises(ValueError, match="Ambiguous"):
        multi_device_manager.resolve("room")


def test_no_match_raises(multi_device_manager):
    """No match raises with available devices."""
    with pytest.raises(ValueError, match="No device matching"):
        multi_device_manager.resolve("Kitchen")


def test_instance_caching(single_device_manager):
    """Same device name returns the same AirQ instance."""
    a = single_device_manager.resolve("TestDevice")
    b = single_device_manager.resolve("TestDevice")
    assert a is b


def test_get_config_for(single_device_manager):
    """get_config_for returns the DeviceConfig."""
    cfg = single_device_manager.get_config_for("TestDevice")
    assert cfg.address == "192.168.1.100"
    assert cfg.password == "testpass"
