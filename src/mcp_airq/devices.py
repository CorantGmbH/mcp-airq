"""Device manager: maintains AirQ instances and resolves device names."""

import aiohttp
from aioairq import AirQ

from mcp_airq.config import DeviceConfig


class DeviceManager:
    """Holds the shared aiohttp session and creates AirQ instances on demand."""

    def __init__(
        self, session: aiohttp.ClientSession, configs: list[DeviceConfig]
    ) -> None:
        self._session = session
        self._configs = {cfg.name: cfg for cfg in configs}
        self._instances: dict[str, AirQ] = {}

    @property
    def device_names(self) -> list[str]:
        """Return all configured device names."""
        return list(self._configs.keys())

    def resolve(self, device: str | None) -> AirQ:
        """Resolve a device name to an AirQ instance.

        If device is None and exactly one device is configured, use that one.
        Otherwise match by case-insensitive substring.
        Raises ValueError on ambiguity or no match.
        """
        if device is None:
            if len(self._configs) == 1:
                device = next(iter(self._configs))
            else:
                raise ValueError(
                    f"Multiple devices configured. Specify one of: "
                    f"{', '.join(self._configs.keys())}"
                )

        # Exact match first
        if device in self._configs:
            return self._get_or_create(device)

        # Case-insensitive substring match
        needle = device.lower()
        matches = [name for name in self._configs if needle in name.lower()]
        if len(matches) == 1:
            return self._get_or_create(matches[0])
        if len(matches) == 0:
            raise ValueError(
                f"No device matching '{device}'. "
                f"Available: {', '.join(self._configs.keys())}"
            )
        raise ValueError(
            f"Ambiguous device '{device}'. Matches: {', '.join(matches)}"
        )

    def get_config_for(self, device_name: str) -> DeviceConfig:
        """Return the DeviceConfig for a resolved device name."""
        return self._configs[device_name]

    def _get_or_create(self, name: str) -> AirQ:
        """Get cached AirQ instance or create one."""
        if name not in self._instances:
            cfg = self._configs[name]
            self._instances[name] = AirQ(
                cfg.address, cfg.password, self._session
            )
        return self._instances[name]
