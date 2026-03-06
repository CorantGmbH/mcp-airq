# Changelog

## [1.0.0] - 2026-03-06

Initial stable release.

### Tools

**Read-only**
- `list_devices` — List all configured air-Q devices with names and addresses
- `get_air_quality` — Get current sensor readings (temperature, CO₂, humidity, PM, VOC, …)
- `get_device_info` — Get device metadata (ID, name, model, firmware/hardware version)
- `get_config` — Get full device configuration as JSON
- `get_logs` — Get device log entries
- `identify_device` — Make device blink its LEDs for visual identification
- `get_led_theme` — Get current LED visualization theme
- `get_possible_led_themes` — List all available LED visualization themes
- `get_night_mode` — Get current night mode configuration
- `get_brightness_config` — Get current LED brightness configuration

**Configuration**
- `set_device_name` — Rename a device
- `set_led_theme` — Change LED visualization theme
- `set_night_mode` — Configure night mode schedule and settings
- `set_brightness` — Adjust LED brightness (day/night)
- `configure_network` — Set static IP or switch to DHCP

**Device control**
- `restart_device` — Restart the device (~30s downtime)
- `shutdown_device` — Shut down the device (manual restart required)

### Features
- Multi-device support with case-insensitive substring name matching
- Automatic device selection when only one device is configured
- Shared `aiohttp.ClientSession` across all device connections
- `@handle_airq_errors` decorator catches all aioairq and network exceptions and returns user-friendly strings
- Configuration via `AIRQ_DEVICES` environment variable (JSON) or `AIRQ_CONFIG_FILE`
