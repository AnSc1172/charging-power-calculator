# Charging Power Calculator

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant custom integration that calculates optimal EV charging power from solar surplus, with automatic 1/3-phase switching and hysteresis-based start/stop logic.

## Features

- Calculates available solar surplus power in real-time
- Outputs a charging setpoint in watts and amperes
- Automatic 1-phase ↔ 3-phase switching with hysteresis
- Time-based start/stop debouncing to prevent charger toggling
- Configurable house battery reserve and fine-tuning offset
- Runs entirely locally (no cloud dependency)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right → **Custom repositories**
3. Add `https://github.com/AnSc1172/charging-power-calculator` with category **Integration**
4. Search for "Charging Power Calculator" and install it
5. Restart Home Assistant
6. Add the integration via **Settings → Devices & Services → Add Integration**

### Manual

1. Copy the `custom_components/charging_power_calculator` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & Services → Add Integration**

## Configuration

The integration is configured through the UI. You need to provide:

| Parameter | Description |
|-----------|-------------|
| Grid Power Sensor | Sensor measuring grid power (positive = import, negative = export) |
| EV Charging Power Sensor | Sensor measuring current EV charging consumption |
| House Battery Power Sensor | Sensor measuring house battery charge power |
| Charging Active | Binary sensor or input_boolean indicating if the EV charger is active |
| Max Battery Power | Power reserved for house battery (default: 2500 W) |
| Min EV Power | Minimum EV charging power / start threshold (default: 1400 W) |
| Fine Adjust | Manual offset to bias the setpoint (default: 500 W) |

## Entities

The integration creates the following entities:

### Sensors
| Entity | Unit | Description |
|--------|------|-------------|
| Surplus Power Available | W | Total available solar surplus |
| Setpoint EV Charging Power | W | Recommended charging power |
| Setpoint Ampere | A | Recommended current per phase |

### Binary Sensors
| Entity | Description |
|--------|-------------|
| Setpoint Charging On | Whether the charger should be ON |
| Is 1 Phase Charging | Whether to use single-phase charging |

## How It Works

The algorithm runs every 31 seconds and:

1. **Calculates surplus**: `surplus = −grid_power + battery_power + ev_power`
2. **Determines setpoint**: `setpoint = surplus − battery_reserve + fine_adjust`
3. **Applies hysteresis**: Waits 60s before starting or stopping to avoid toggling
4. **Selects phase**: Switches to 3-phase above 3500 W, back to 1-phase below 3000 W
5. **Calculates ampere**: Converts watts to amps, clamped between 6–16 A

For a detailed explanation with pseudocode, see [DOCUMENTATION.md](DOCUMENTATION.md).

## License

MIT License — see [LICENSE](LICENSE).
