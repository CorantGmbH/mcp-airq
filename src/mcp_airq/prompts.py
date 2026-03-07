"""MCP prompts providing sensor and configuration context for air-Q devices."""

from mcp_airq.server import mcp


@mcp.prompt()
def airq_sensor_guide() -> str:
    """Guide for interpreting air-Q sensor values: units, ranges, and semantics."""
    return """\
# air-Q Sensor Interpretation Guide

## Quality indices — higher is always better

| Key         | Range       | Meaning                                                                 |
|-------------|-------------|-------------------------------------------------------------------------|
| health      | 0–1000      | Overall air quality health score. -200 = gas alarm, -800 = fire alarm. |
| performance | 0–1000      | Estimated cognitive performance index.                                  |
| mold        | 0–100 %     | Mold-FREE index. 100 % = no mold risk; 0 % = ventilation insufficient. |
| virus       | 0–100 %     | Low-virus-transmission index. 100 % = fine; 0 % = ventilation insufficient. Uses CO₂ as aerosol proxy. |

## Climate

| Key          | Unit   | Notes                                          |
|--------------|--------|------------------------------------------------|
| temperature  | °C     | Configurable: degF, K                          |
| humidity     | %      | Relative humidity                              |
| humidity_abs | g/m³   | Absolute humidity                              |
| dewpt        | °C     | Dew point. Configurable: degF, K              |
| pressure     | hPa    | Absolute air pressure. Configurable: kPa, mbar, bar, psi |
| pressure_rel | hPa    | Relative pressure (QNH), only if altitude configured |

## Gases

| Key          | Unit    | Notes                                                     |
|--------------|---------|-----------------------------------------------------------|
| co2          | ppm     | CO₂. Auto-calibrated baseline at 410 ppm.                |
| tvoc         | ppb     | Total VOC (electrochemical).                              |
| tvoc_ionsc   | ppb     | Total VOC (PID sensor, ION Science).                      |
| co           | mg/m³   | Carbon monoxide. Fire alarm threshold: > 200 mg/m³.       |
| no2          | µg/m³   | Nitrogen dioxide. Gas alarm threshold: > 20 000 µg/m³.    |
| so2          | µg/m³   | Sulfur dioxide.                                           |
| o3           | µg/m³   | Ozone. Gas alarm threshold: > 1 000 µg/m³.               |
| h2s          | µg/m³   | Hydrogen sulfide. Gas alarm threshold: > 50 000 µg/m³.    |
| oxygen       | %       | O₂. Normal: ~20.9 %. Gas alarm threshold: < 13 %.         |
| ethanol      | µg/m³   |                                                           |
| n2o          | µg/m³   | Nitrous oxide.                                            |
| nh3_MR100    | µg/m³   | Ammonia. Gas alarm threshold: > 100 000 µg/m³.            |
| acid_M100    | ppb     | Organic acids.                                            |
| h2_M1000     | µg/m³   | Hydrogen.                                                 |
| no_M250      | µg/m³   | Nitric oxide.                                             |
| cl2_M20      | µg/m³   | Chlorine. Gas alarm threshold: > 50 000 µg/m³.            |
| ch2o_M10     | µg/m³   | Formaldehyde. Gas alarm threshold: > 2 000 µg/m³.         |
| c3h8_MIPEX   | %       | Propane. Gas alarm threshold: > 0.25 %.                   |
| ch4_MIPEX    | %       | Methane. Gas alarm threshold: > 0.5 %.                    |
| r32          | %       | Refrigerant R-32.                                         |
| r454b        | %       | Refrigerant R-454B.                                       |
| r454c        | %       | Refrigerant R-454C.                                       |

## Particulate matter

| Key                     | Unit            | Notes                                              |
|-------------------------|-----------------|----------------------------------------------------|
| pm1                     | µg/m³           | PM1.0 mass concentration.                          |
| pm2_5                   | µg/m³           | PM2.5 mass concentration. By definition: pm1 ≤ pm2_5 ≤ pm10. |
| pm10                    | µg/m³           | PM10 mass concentration. Fire alarm threshold: PM1 > 400 µg/m³. |
| TypPS                   | µm              | Typical (mean) particle size.                      |
| cnt0_3 … cnt10          | #/100 ml        | Particle count for sizes > 0.3, 0.5, 1, 2.5, 5, 10 µm. |
| pm1_SPS30 … pm10_SPS30  | µg/m³           | PM fractions from optional Sensirion SPS30.        |
| cnt0_5_SPS30 … cnt10_SPS30 | 1/cm³        | Particle counts from optional Sensirion SPS30.     |

## Acoustics

| Key       | Unit  | Notes                                                             |
|-----------|-------|-------------------------------------------------------------------|
| sound     | dB(A) | Average noise level over the measurement period.                  |
| sound_max | dB(A) | Peak noise level within the measurement period.                   |

## Radon

| Key   | Unit   | Notes                              |
|-------|--------|------------------------------------|
| radon | Bq/m³  | Radon activity. Configurable: pCi/L. WHO reference level: 100 Bq/m³. |

## Metadata fields (not sensor measurements)

| Key         | Unit   | Notes                                                       |
|-------------|--------|-------------------------------------------------------------|
| timestamp   | ms     | Unix epoch in milliseconds.                                 |
| uptime      | s      | Device runtime since last reboot.                           |
| measuretime | ms     | Duration of the measurement cycle.                          |
| dCO2dt      | ppb/s  | CO₂ rate of change. Only available after 200 s of runtime.  |
| dHdt        | mg/m³/s| Absolute humidity rate of change. Used internally for sensor compensation. |
| DeviceID    | —      | Device serial (first 10 chars) + unique suffix.             |
| Status      | —      | "OK" or JSON object with per-sensor status messages.        |

## Alarm thresholds (for reference)

Fire alarm (if enabled): CO > 200 mg/m³, PM1 > 400 µg/m³, or temperature > 70 °C.
Gas alarm (if enabled): O₂ < 13 %, NO₂ > 20 000 µg/m³, O₃ > 1 000 µg/m³,
  H₂S > 50 000 µg/m³, CH₂O > 2 000 µg/m³, Cl₂ > 50 000 µg/m³,
  NH₃ > 100 000 µg/m³, CH₄ > 0.5 %, C₃H₈ > 0.25 %.

## Unit configuration

Default units apply unless the device is configured otherwise via the `units` config key.
The actual unit in use can be verified by reading the SensorInfo from GET /config.
"""


@mcp.prompt()
def airq_config_guide() -> str:
    """Guide for interpreting and setting air-Q device configuration keys."""
    return """\
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
