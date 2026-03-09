"""Guide strings for air-Q sensor and configuration interpretation.

Imported by both prompts.py (to expose as MCP prompts) and read.py
(to embed directly in tool responses so the context is always present,
regardless of whether the client invokes the prompt explicitly).
"""

# ---------------------------------------------------------------------------
# Structured sensor data — single source of truth for the sensor guide
# ---------------------------------------------------------------------------

# Each row: (matching_keys, display_key, unit_or_range, description)
_Row = tuple[frozenset[str], str, str, str]


def _e(keys: str | set[str], display: str, unit: str, desc: str) -> _Row:
    """Create a sensor row. *keys* may be a single key or a set."""
    if isinstance(keys, str):
        keys = {keys}
    return (frozenset(keys), display, unit, desc)


# (section_title, column_headers, rows)
_Category = tuple[str, tuple[str, str, str], list[_Row]]

_SENSOR_CATEGORIES: list[_Category] = [
    (
        "Quality indices — higher is always better",
        ("Key", "Range", "Meaning"),
        [
            _e(
                "health",
                "health",
                "0–1000",
                "Overall air quality health score. -200 = gas alarm, -800 = fire alarm.",
            ),
            _e(
                "performance",
                "performance",
                "0–1000",
                "Estimated cognitive performance index.",
            ),
            _e(
                "mold",
                "mold",
                "0–100 %",
                "Mold-FREE index. 100 % = no mold risk; 0 % = ventilation insufficient.",
            ),
            _e(
                "virus",
                "virus",
                "0–100 %",
                "Low-virus-transmission index. 100 % = fine; 0 % = ventilation insufficient."
                " Uses CO₂ as aerosol proxy.",
            ),
        ],
    ),
    (
        "Climate",
        ("Key", "Unit", "Notes"),
        [
            _e("temperature", "temperature", "°C", "Configurable: degF, K"),
            _e("humidity", "humidity", "%", "Relative humidity"),
            _e("humidity_abs", "humidity_abs", "g/m³", "Absolute humidity"),
            _e("dewpt", "dewpt", "°C", "Dew point. Configurable: degF, K"),
            _e(
                "pressure",
                "pressure",
                "hPa",
                "Absolute air pressure. Configurable: kPa, mbar, bar, psi",
            ),
            _e(
                "pressure_rel",
                "pressure_rel",
                "hPa",
                "Relative pressure (QNH), only if altitude configured",
            ),
        ],
    ),
    (
        "Gases",
        ("Key", "Unit", "Notes"),
        [
            _e("co2", "co2", "ppm", "CO₂. Auto-calibrated baseline at 410 ppm."),
            _e("tvoc", "tvoc", "ppb", "Total VOC (electrochemical)."),
            _e(
                "tvoc_ionsc",
                "tvoc_ionsc",
                "ppb",
                "Total VOC (PID sensor, ION Science).",
            ),
            _e(
                "co",
                "co",
                "mg/m³",
                "Carbon monoxide. Fire alarm threshold: > 200 mg/m³.",
            ),
            _e(
                "no2",
                "no2",
                "µg/m³",
                "Nitrogen dioxide. Gas alarm threshold: > 20 000 µg/m³.",
            ),
            _e("so2", "so2", "µg/m³", "Sulfur dioxide."),
            _e("o3", "o3", "µg/m³", "Ozone. Gas alarm threshold: > 1 000 µg/m³."),
            _e(
                "h2s",
                "h2s",
                "µg/m³",
                "Hydrogen sulfide. Gas alarm threshold: > 50 000 µg/m³.",
            ),
            _e(
                "oxygen",
                "oxygen",
                "%",
                "O₂. Normal: ~20.9 %. Gas alarm threshold: < 13 %.",
            ),
            _e("ethanol", "ethanol", "µg/m³", ""),
            _e("n2o", "n2o", "µg/m³", "Nitrous oxide."),
            _e(
                "nh3_MR100",
                "nh3_MR100",
                "µg/m³",
                "Ammonia. Gas alarm threshold: > 100 000 µg/m³.",
            ),
            _e("acid_M100", "acid_M100", "ppb", "Organic acids."),
            _e("h2_M1000", "h2_M1000", "µg/m³", "Hydrogen."),
            _e("no_M250", "no_M250", "µg/m³", "Nitric oxide."),
            _e(
                "cl2_M20",
                "cl2_M20",
                "µg/m³",
                "Chlorine. Gas alarm threshold: > 50 000 µg/m³.",
            ),
            _e(
                "ch2o_M10",
                "ch2o_M10",
                "µg/m³",
                "Formaldehyde. Gas alarm threshold: > 2 000 µg/m³.",
            ),
            _e(
                "c3h8_MIPEX",
                "c3h8_MIPEX",
                "%",
                "Propane. Gas alarm threshold: > 0.25 %.",
            ),
            _e("ch4_MIPEX", "ch4_MIPEX", "%", "Methane. Gas alarm threshold: > 0.5 %."),
            _e("r32", "r32", "%", "Refrigerant R-32."),
            _e("r454b", "r454b", "%", "Refrigerant R-454B."),
            _e("r454c", "r454c", "%", "Refrigerant R-454C."),
        ],
    ),
    (
        "Particulate matter",
        ("Key", "Unit", "Notes"),
        [
            _e("pm1", "pm1", "µg/m³", "PM1.0 mass concentration."),
            _e(
                "pm2_5",
                "pm2_5",
                "µg/m³",
                "PM2.5 mass concentration. By definition: pm1 ≤ pm2_5 ≤ pm10.",
            ),
            _e(
                "pm10",
                "pm10",
                "µg/m³",
                "PM10 mass concentration. Fire alarm threshold: PM1 > 400 µg/m³.",
            ),
            _e("TypPS", "TypPS", "µm", "Typical (mean) particle size."),
            _e(
                {"cnt0_3", "cnt0_5", "cnt1", "cnt2_5", "cnt5", "cnt10"},
                "cnt0_3 … cnt10",
                "#/100 ml",
                "Particle count for sizes > 0.3, 0.5, 1, 2.5, 5, 10 µm.",
            ),
            _e(
                {"pm1_SPS30", "pm2_5_SPS30", "pm10_SPS30"},
                "pm1_SPS30 … pm10_SPS30",
                "µg/m³",
                "PM fractions from optional Sensirion SPS30.",
            ),
            _e(
                {
                    "cnt0_5_SPS30",
                    "cnt1_SPS30",
                    "cnt2_5_SPS30",
                    "cnt4_SPS30",
                    "cnt10_SPS30",
                },
                "cnt0_5_SPS30 … cnt10_SPS30",
                "1/cm³",
                "Particle counts from optional Sensirion SPS30.",
            ),
        ],
    ),
    (
        "Acoustics",
        ("Key", "Unit", "Notes"),
        [
            _e(
                "sound",
                "sound",
                "dB(A)",
                "Average noise level over the measurement period.",
            ),
            _e(
                "sound_max",
                "sound_max",
                "dB(A)",
                "Peak noise level within the measurement period.",
            ),
        ],
    ),
    (
        "Radon",
        ("Key", "Unit", "Notes"),
        [
            _e(
                "radon",
                "radon",
                "Bq/m³",
                "Radon activity. Configurable: pCi/L. WHO reference level: 100 Bq/m³.",
            ),
        ],
    ),
    (
        "Metadata fields (not sensor measurements)",
        ("Key", "Unit", "Notes"),
        [
            _e("timestamp", "timestamp", "ms", "Unix epoch in milliseconds."),
            _e("uptime", "uptime", "s", "Device runtime since last reboot."),
            _e(
                "measuretime", "measuretime", "ms", "Duration of the measurement cycle."
            ),
            _e(
                "dCO2dt",
                "dCO2dt",
                "ppb/s",
                "CO₂ rate of change. Only available after 200 s of runtime.",
            ),
            _e(
                "dHdt",
                "dHdt",
                "mg/m³/s",
                "Absolute humidity rate of change."
                " Used internally for sensor compensation.",
            ),
            _e(
                "DeviceID",
                "DeviceID",
                "—",
                "Device serial (first 10 chars) + unique suffix.",
            ),
            _e(
                "Status",
                "Status",
                "—",
                '"OK" or JSON object with per-sensor status messages.',
            ),
        ],
    ),
]

_FULL_GUIDE_FOOTER = """\

## Alarm thresholds (for reference)

Fire alarm (if enabled): CO > 200 mg/m³, PM1 > 400 µg/m³, or temperature > 70 °C.
Gas alarm (if enabled): O₂ < 13 %, NO₂ > 20 000 µg/m³, O₃ > 1 000 µg/m³,
  H₂S > 50 000 µg/m³, CH₂O > 2 000 µg/m³, Cl₂ > 50 000 µg/m³,
  NH₃ > 100 000 µg/m³, CH₄ > 0.5 %, C₃H₈ > 0.25 %.

## Unit configuration

Default units apply unless the device is configured otherwise via the `units` config key.
The actual unit in use can be verified by reading the SensorInfo from GET /config.
"""


# ---------------------------------------------------------------------------
# Guide builder
# ---------------------------------------------------------------------------


def _format_table(columns: tuple[str, str, str], rows: list[_Row]) -> str:
    """Render *rows* as a markdown table with the given column headers."""
    lines = [
        f"| {columns[0]} | {columns[1]} | {columns[2]} |",
        "|---|---|---|",
    ]
    for _, display, unit, desc in rows:
        lines.append(f"| {display} | {unit} | {desc} |")
    return "\n".join(lines)


def build_sensor_guide(data_keys: frozenset[str] | set[str]) -> str:
    """Build a sensor guide filtered to sensors present in *data_keys*.

    Only categories that contain at least one matching sensor are included.
    Returns an empty string when nothing matches.
    """
    sections: list[str] = []
    for title, columns, rows in _SENSOR_CATEGORIES:
        matching = [r for r in rows if r[0] & data_keys]
        if matching:
            sections.append(f"## {title}\n\n{_format_table(columns, matching)}")
    if not sections:
        return ""
    return "# air-Q Sensor Interpretation Guide\n\n" + "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

# All known sensor keys — used to generate the full (unfiltered) guide.
_ALL_KEYS: frozenset[str] = frozenset().union(
    *(keys for _, _, rows in _SENSOR_CATEGORIES for keys, _, _, _ in rows)
)

SENSOR_GUIDE = build_sensor_guide(_ALL_KEYS) + _FULL_GUIDE_FOOTER

CONFIG_GUIDE = """\
# air-Q Device Configuration Guide

The `get_config` tool returns the full configuration of a device as a JSON object.
The following describes the most relevant keys returned and what they mean.

## Identity and location

| Key          | Type        | Default        | Description                                                  |
|--------------|-------------|----------------|--------------------------------------------------------------|
| devicename   | str         | None           | Human-readable device name shown on the display.             |
| RoomType     | str         | "living-room"  | Room context. Possible values: living-room, bedroom, kitchen, bathroom, office, workshop, children, toilet, hallway, cellar, attic, outdoor, garage, medical, classroom, other. Full list in `possibleRoomType`. |
| RoomHeight   | float       | 0.0            | Room height in metres. Used for volume-based calculations.   |
| RoomArea     | float       | 0.0            | Room floor area in m². Used for volume-based calculations.   |
| geopos       | {lat, long} | {0.0, 0.0}     | GPS coordinates (decimal degrees).                           |
| country_code | str         | None           | ISO-3166 country code. Enables automatic DST adjustment for night mode. |
| Altitude     | [float, float] | [-10000, 100] | [altitude in m, error in m]. When set, activates the `pressure_rel` virtual sensor. |

## Network

| Key            | Type   | Default        | Description                                                       |
|----------------|--------|----------------|-------------------------------------------------------------------|
| Wifi           | bool   | true           | Enable/disable WiFi entirely.                                     |
| WifiInfo       | bool   | true           | Show WiFi connection state on the lowest LEDs.                    |
| ifconfig       | object | DHCP           | Static IP config: {ip, subnet, gateway, dns}. Absent = DHCP.     |
| WLANantenna    | str    | "internal"     | Antenna selection: "internal" or "external" (industry/special only). Requires reboot. |
| Hot SpotChannel| int    | 11             | WiFi channel for the fallback Hot Spot (1–11).                    |
| TimeServer     | str    | "pool.ntp.org" | NTP server address. Clock is synced every 6 hours.               |

## LEDs and night mode

| Key      | Type   | Default | Description                                                                     |
|----------|--------|---------|---------------------------------------------------------------------------------|
| ledTheme | object | standard| {left: str, right: str}. Theme names listed in `possibleLedTheme`. Each side can be set independently. |
| NightMode| object | —       | Night mode configuration (see below).                                           |
| daytime  | bool   | —       | Read-only. true = device is currently in day mode, false = night mode.          |

**NightMode object fields:**

| Field           | Type   | Default | Description                                                            |
|-----------------|--------|---------|------------------------------------------------------------------------|
| Activated       | bool   | false   | Enable night mode scheduling.                                          |
| StartDay        | str    | "07:00" | Time to switch to day mode (HH:mm, **UTC**).                          |
| StartNight      | str    | "21:00" | Time to switch to night mode (HH:mm, **UTC**).                        |
| BrightnessDay   | float  | 6.0     | LED brightness during day (0 = off, 10 = maximum).                    |
| BrightnessNight | float  | 6.0     | LED brightness during night (0 = off, 10 = maximum).                  |
| FanNightOff     | bool   | false   | Disable particulates sensor fan at night. Disables smoke detection.   |
| WifiNightOff    | bool   | false   | Disable WiFi at night. Data is buffered on SD and uploaded at sunrise. |
| AlarmNightOff   | bool   | false   | Silence user-defined acoustic alarms at night. Fire/gas alarms always sound. |

## Measurement behaviour

| Key                             | Type   | Default      | Description                                                       |
|---------------------------------|--------|--------------|-------------------------------------------------------------------|
| Averaging                       | int    | 30           | Number of readings in the moving average. Set to 1 to disable.   |
| SecondsMeasurementDelay         | int    | 120          | Interval in seconds for SD card storage and cloud upload.         |
| Rejection                       | str    | "50Hz+60Hz"  | Mains frequency filter: "50Hz", "60Hz", or "50Hz+60Hz".          |
| AutoDriftCompensation           | bool   | true         | Long-term baseline drift correction for electrochemical and O₂ sensors. |
| HumidityEnvironmentCompensation | bool   | true         | Extends averaging for electrochemical sensors during rapid humidity changes. |
| SensitivityEnvironmentCompensation | bool | true        | Corrects electrochemical sensor sensitivity for ambient temperature. |
| OffsetEnvironmentCompensation   | bool   | true         | Corrects dynamic offset shifts in NO₂ and O₃ sensors.            |
| units                           | object | sensor-specific | Override default physical units per sensor. Example: {"co": "ppm", "temperature": "degF"}. |
| BuildingStandard                | str    | "None"       | Adjusts VOC evaluation: "None", "WELL", or "RESET".              |

## Health and performance index tuning

| Key                 | Type     | Default | Description                                                   |
|---------------------|----------|---------|---------------------------------------------------------------|
| health_exclude      | [str]    | []      | Sensor keys excluded from the health index calculation.       |
| performance_exclude | [str]    | []      | Sensor keys excluded from the performance index calculation.  |

## Virtual sensors

Some sensors are deactivated by default and must be explicitly enabled.
The current list of deactivated sensors is in `deactivated_sensors`.

| Key          | Deactivated by default | Description                                      |
|--------------|------------------------|--------------------------------------------------|
| mold         | yes                    | Mold-free index. Activated automatically by the "Mold" LED theme.    |
| virus        | yes                    | Low-virus-transmission index. Activated automatically by the "Virus" LED theme. |
| pressure_rel | yes                    | QNH pressure. Activated automatically when `Altitude` is configured. |
| uptime       | yes                    | Device uptime in seconds.                        |
| measuretime  | yes                    | Measurement cycle duration in milliseconds.      |
| fahrenheit   | yes                    | Temperature in °F (parallel to `temperature`).   |
| pm_cnts      | yes                    | Raw particle count channels (cnt0_3 … cnt10).    |

## Alarms

| Key             | Type   | Default | Description                                                        |
|-----------------|--------|---------|--------------------------------------------------------------------|
| FireAlarm       | bool   | false   | Enable fire alarm (CO, PM1, temperature thresholds).              |
| GasAlarm        | bool   | false   | Enable gas alarm (O₂, NO₂, O₃, H₂S, CH₂O, Cl₂, NH₃, CH₄, C₃H₈).|
| AlarmForwarding | bool   | false   | Forward fire/gas alarm state to other air-Q devices on the network.|
| SoundInfo       | object | {}      | User-defined acoustic threshold alerts per sensor.                 |

## Data transmission

| Key               | Type   | Default | Description                                              |
|-------------------|--------|---------|----------------------------------------------------------|
| cloudUpload       | bool   | false   | Upload averaged data to air-Q cloud every 2 minutes.    |
| cloudRemote       | bool   | false   | Allow remote config changes via the cloud shadow.        |
| UnencryptedFolder | bool   | true    | Write unencrypted data copy to SD card.                  |
| csv_output        | bool   | false   | Write monthly CSV files to SD card in addition to JSON.  |
| httpPOST          | object | —       | Push data to a custom HTTP endpoint.                     |
| mqtt              | object | —       | Publish data to an MQTT broker.                          |
| AutoUpdate        | int    | 90      | Auto-update interval in days. 0 = disabled.              |

## Read-only fields in the config response

| Key                    | Description                                                             |
|------------------------|-------------------------------------------------------------------------|
| sensors                | List of sensor keys installed in this device.                           |
| SensorInfo             | Per-sensor hardware and calibration metadata (manufacturer, unit, calibration date, etc.). |
| possibleRoomType       | All valid values for `RoomType`.                                        |
| possibleLedTheme       | All valid values for `ledTheme`.                                        |
| PossibleBuildingStandards | All valid values for `BuildingStandard`.                             |
| deactivated_sensors    | Currently deactivated virtual sensor keys.                              |
| daytime                | Whether the device is currently in day mode (true) or night mode (false).|
| air-Q-Software-Version | Installed firmware version string.                                      |
| air-Q-Hardware-Version | Hardware revision string.                                               |
"""
