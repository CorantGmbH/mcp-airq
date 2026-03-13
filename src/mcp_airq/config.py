"""Device configuration loading from environment variables or config file."""

import json
import logging
import os
import stat
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceConfig:
    """Configuration for a single air-Q device."""

    address: str
    password: str
    name: str
    location: str | None = None
    group: str | None = None


def _warn_if_world_readable(path: str) -> None:
    """Log a warning if the config file is readable by group or others."""
    try:
        mode = os.stat(path).st_mode
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            logger.warning(
                "Config file '%s' is readable by group/others (mode %s). "
                "This file contains device passwords. "
                "Run 'chmod 600 %s' to restrict access.",
                path,
                oct(mode),
                path,
            )
    except OSError:
        pass  # file access errors are handled later when opening the file


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
        _warn_if_world_readable(config_file)
        with open(config_file, encoding="utf-8") as f:
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
            raise ValueError(f"Device entry {i} missing required 'address' or 'password' field.")
        devices.append(
            DeviceConfig(
                address=entry["address"],
                password=entry["password"],
                name=entry.get("name", entry["address"]),
                location=entry.get("location"),
                group=entry.get("group"),
            )
        )

    return devices
