"""Device configuration loading from environment variables or config file."""

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceConfig:
    """Configuration for a single air-Q device."""

    address: str
    password: str
    name: str


def load_config() -> list[DeviceConfig]:
    """Load device configs from AIRQ_DEVICES env var or AIRQ_CONFIG_FILE.

    AIRQ_DEVICES: JSON array of objects with 'address', 'password', and
    optional 'name' fields.

    AIRQ_CONFIG_FILE: path to a JSON file with the same structure.

    Raises ValueError if no devices are configured or JSON is malformed.
    """
    raw = os.environ.get("AIRQ_DEVICES")
    if raw is None:
        config_file = os.environ.get("AIRQ_CONFIG_FILE")
        if config_file is None:
            raise ValueError(
                "No air-Q devices configured. Set AIRQ_DEVICES env var "
                "(JSON array) or AIRQ_CONFIG_FILE (path to JSON file)."
            )
        with open(config_file) as f:
            raw = f.read()

    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in device config: {exc}") from exc

    if not isinstance(entries, list) or len(entries) == 0:
        raise ValueError("Device config must be a non-empty JSON array.")

    devices = []
    for i, entry in enumerate(entries):
        if "address" not in entry or "password" not in entry:
            raise ValueError(
                f"Device entry {i} missing required 'address' or 'password' field."
            )
        devices.append(
            DeviceConfig(
                address=entry["address"],
                password=entry["password"],
                name=entry.get("name", entry["address"]),
            )
        )

    return devices
