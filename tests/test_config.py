"""Tests for config loading."""

import json
import os
import pytest

from mcp_airq.config import DeviceConfig, load_config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure no leftover env vars."""
    monkeypatch.delenv("AIRQ_DEVICES", raising=False)
    monkeypatch.delenv("AIRQ_CONFIG_FILE", raising=False)


def test_load_from_env_single_device(monkeypatch):
    """Load a single device from AIRQ_DEVICES."""
    devices_json = json.dumps(
        [{"address": "192.168.1.1", "password": "secret", "name": "MyAirQ"}]
    )
    monkeypatch.setenv("AIRQ_DEVICES", devices_json)
    configs = load_config()
    assert len(configs) == 1
    assert configs[0] == DeviceConfig("192.168.1.1", "secret", "MyAirQ")


def test_load_from_env_multiple_devices(monkeypatch):
    """Load multiple devices from AIRQ_DEVICES."""
    devices_json = json.dumps([
        {"address": "192.168.1.1", "password": "p1", "name": "A"},
        {"address": "192.168.1.2", "password": "p2", "name": "B"},
    ])
    monkeypatch.setenv("AIRQ_DEVICES", devices_json)
    configs = load_config()
    assert len(configs) == 2


def test_name_defaults_to_address(monkeypatch):
    """If name is omitted, default to address."""
    devices_json = json.dumps([{"address": "10.0.0.1", "password": "pw"}])
    monkeypatch.setenv("AIRQ_DEVICES", devices_json)
    configs = load_config()
    assert configs[0].name == "10.0.0.1"


def test_load_from_file(monkeypatch, tmp_path):
    """Load from AIRQ_CONFIG_FILE."""
    config_file = tmp_path / "devices.json"
    config_file.write_text(
        json.dumps([{"address": "1.2.3.4", "password": "x", "name": "File"}])
    )
    monkeypatch.setenv("AIRQ_CONFIG_FILE", str(config_file))
    configs = load_config()
    assert configs[0].name == "File"


def test_no_config_raises():
    """Raise ValueError when no config is set."""
    with pytest.raises(ValueError, match="No air-Q devices configured"):
        load_config()


def test_invalid_json_raises(monkeypatch):
    """Raise ValueError for malformed JSON."""
    monkeypatch.setenv("AIRQ_DEVICES", "not json")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_config()


def test_empty_array_raises(monkeypatch):
    """Raise ValueError for empty device list."""
    monkeypatch.setenv("AIRQ_DEVICES", "[]")
    with pytest.raises(ValueError, match="non-empty"):
        load_config()


def test_missing_address_raises(monkeypatch):
    """Raise ValueError when address is missing."""
    monkeypatch.setenv("AIRQ_DEVICES", json.dumps([{"password": "pw"}]))
    with pytest.raises(ValueError, match="missing required"):
        load_config()


def test_missing_password_raises(monkeypatch):
    """Raise ValueError when password is missing."""
    monkeypatch.setenv("AIRQ_DEVICES", json.dumps([{"address": "1.2.3.4"}]))
    with pytest.raises(ValueError, match="missing required"):
        load_config()
