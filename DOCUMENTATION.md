# Charging Power Calculator — Home Assistant Custom Integration

## Overview

This integration calculates the optimal EV charging power based on available solar surplus. It determines whether to charge, at what power level, and whether to use 1-phase or 3-phase charging — all to maximize self-consumption of solar energy while avoiding grid import.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Home Assistant                                                    │
│                                                                    │
│  ┌──────────────┐         ┌──────────────────────────┐            │
│  │ Input Sensors│────────▶│ ChargingPowerCoordinator │            │
│  │  - grid_power│         │   (runs every 31s)       │            │
│  │  - ev_power  │         └────────────┬─────────────┘            │
│  │  - battery   │                      │                          │
│  │  - battery_soc────┐                 ▼                          │
│  │  - charging  │    │    ┌──────────────────────────┐            │
│  └──────────────┘    │    │ Output Entities           │            │
│                      │    │  - setpoint_power (W)     │            │
│  ┌───────────────┐   │    │  - setpoint_ampere (A)    │            │
│  │ Curve Config  │───┘    │  - surplus_power (W)      │            │
│  │  (breakpoints)│        │  - battery_reserve (W)    │            │
│  └───────┬───────┘        │  - charging_on (bool)     │            │
│          │                │  - is_1_phase (bool)      │            │
│          │                └──────────────────────────┘            │
│          │                                                        │
│          ▼                ┌──────────────────────────┐            │
│  ┌───────────────┐        │ Controls (device page)    │            │
│  │ Lovelace Card │        │  - Reserve at 20% (slider)│            │
│  │ (curve editor)│───────▶│  - Reserve at 50% (slider)│            │
│  └───────────────┘  svc   │  - Reserve at 80% (slider)│            │
│                           └──────────────────────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

## Configuration Inputs

| Parameter | Entity Type | Description |
|-----------|-------------|-------------|
| `grid_power` | sensor | Grid power in Watts (positive = importing, negative = exporting) |
| `ev_charging_power` | sensor | Current EV charging power in Watts |
| `house_battery_power` | sensor | House battery charging power in Watts (positive = charging battery) |
| `house_battery_soc` | sensor *(optional)* | Battery state of charge (0–100%). Enables the characteristic curve |
| `current_charging_on` | binary_sensor / input_boolean | Whether the EV charger is currently active |
| `max_charging_power_house_battery` | number (default: 2500 W) | Fallback reserve when SoC sensor is unavailable |
| `min_charging_power_ev` | number (default: 1400 W) | Minimum EV charging power (~6A single phase) |
| `fine_adjust` | number (default: 500 W) | Manual bias/offset to tweak the setpoint |

## Output Entities

| Entity | Type | Unit | Description |
|--------|------|------|-------------|
| Setpoint EV Charging Power | sensor | W | Recommended EV charging power |
| Setpoint Ampere | sensor | A | Recommended current per phase |
| Surplus Power Available | sensor | W | Calculated total surplus |
| Battery Reserve Power | sensor | W | Current interpolated reserve from curve |
| Setpoint Charging On | binary_sensor | — | Whether EV charging should be ON |
| Is 1 Phase Charging | binary_sensor | — | Whether to use 1-phase (vs 3-phase) |
| Reserve at 20% SoC | number | W | Slider control for curve breakpoint |
| Reserve at 50% SoC | number | W | Slider control for curve breakpoint |
| Reserve at 80% SoC | number | W | Slider control for curve breakpoint |

## Constants

| Name | Value | Description |
|------|-------|-------------|
| `UPDATE_INTERVAL` | 31 s | Polling / calculation interval |
| `VOLTAGE` | 230 V | Mains voltage (EU) |
| `AMPERE_MIN` | 6 A | Minimum charging current (EV standard) |
| `AMPERE_MAX` | 16 A | Maximum charging current |
| `START_EXPORT_THRESHOLD` | -500 W | Grid export must exceed 500 W to start |
| `START_EXPORT_SECONDS` | 60 s | Export must persist for 60 s before starting |
| `STOP_SETPOINT_SECONDS` | 60 s | Negative setpoint must persist 60 s before stopping |
| `PHASE_SWITCH_UP_W` | 3500 W | Switch from 1-phase to 3-phase above this |
| `PHASE_SWITCH_DOWN_W` | 3000 W | Switch from 3-phase to 1-phase below this |
| `PHASE_SWITCH_PAUSE` | 90 s | Pause after phase switching (charger needs time) |

## Core Algorithm — Pseudocode

```
FUNCTION calculate_surplus_and_setpoint():
    // ──────────────────────────────────────────────
    // STEP 1: Read sensor inputs
    // ──────────────────────────────────────────────
    grid_power       ← read sensor (+ = importing from grid, − = exporting)
    ev_power         ← read sensor (current EV consumption)
    battery_power    ← read sensor (house battery charge power)
    battery_soc      ← read sensor (house battery state of charge, 0–100%)
    charging_on      ← read sensor (is EV charger currently active?)

    IF any required input is unavailable:
        RETURN last known values (no update)

    // ──────────────────────────────────────────────
    // STEP 1b: Resolve battery reserve from curve
    // ──────────────────────────────────────────────
    IF battery_soc sensor is configured AND available:
        battery_reserve ← INTERPOLATE(curve, battery_soc)
        // Piecewise-linear interpolation between breakpoints
        // Default curve: [[0,3000], [20,2500], [60,2000], [80,500], [100,500]]
    ELSE:
        battery_reserve ← max_battery_power (static fallback)

    // ──────────────────────────────────────────────
    // STEP 2: Calculate surplus power
    // ──────────────────────────────────────────────
    // Surplus = what we're exporting + what battery is taking + what EV is already using
    // This represents the total "available solar" that could go to EV charging
    surplus ← −grid_power + battery_power + ev_power

    // Interpretation:
    //   grid_power = -1000 (exporting 1kW)
    //   battery_power = 2000 (battery charging 2kW)
    //   ev_power = 3000 (EV already drawing 3kW)
    //   → surplus = 1000 + 2000 + 3000 = 6000 W available for EV

    // ──────────────────────────────────────────────
    // STEP 3: Phase-switch pause guard
    // ──────────────────────────────────────────────
    IF currently in phase-switch pause period:
        RETURN last values unchanged (wait 90s for charger to stabilize)

    // ──────────────────────────────────────────────
    // STEP 4: Determine charging setpoint
    // ──────────────────────────────────────────────
    setpoint ← 0

    IF charger is NOT currently active:
        // --- START condition ---
        IF grid_power < −500 W (exporting more than 500W):
            start tracking "export duration"
        ELSE:
            reset "export duration" timer

        IF export has persisted for ≥ 60 seconds:
            setpoint ← min_ev_power (start at minimum, e.g. 1400 W)

    ELSE (charger IS active):
        // --- RUNNING condition ---
        setpoint ← surplus − battery_reserve + fine_adjust

        // Explanation:
        //   battery_reserve comes from the characteristic curve (or static fallback).
        //   We subtract it to "reserve" that capacity for the house battery.
        //   We add fine_adjust as a user-configurable bias.
        //
        // Example (battery at 30% SoC, curve gives reserve = 2400 W):
        //   surplus = 6000 W, battery_reserve = 2400 W, fine_adjust = 500 W
        //   → setpoint = 6000 − 2400 + 500 = 4100 W for EV
        //
        // Example (battery at 85% SoC, curve gives reserve = 500 W):
        //   surplus = 6000 W, battery_reserve = 500 W, fine_adjust = 500 W
        //   → setpoint = 6000 − 500 + 500 = 6000 W for EV (nearly all to car)

    // ──────────────────────────────────────────────
    // STEP 5: Apply minimum threshold & stop logic
    // ──────────────────────────────────────────────
    IF setpoint > 0:
        IF setpoint < min_ev_power:
            setpoint ← min_ev_power   // Never go below minimum charging power
        charging_on ← TRUE
        reset "stop timer"

    ELSE IF setpoint < 0:
        // --- STOP condition (with hysteresis) ---
        start tracking "negative setpoint duration"
        IF negative setpoint has persisted for ≥ 60 seconds:
            charging_on ← FALSE

    ELSE (setpoint == 0):
        reset "stop timer"

    // ──────────────────────────────────────────────
    // STEP 6: Decide phase count (1-phase vs 3-phase)
    // ──────────────────────────────────────────────
    phase ← current_phase  // keep current by default (hysteresis band)

    IF setpoint < 3000 W:
        phase ← 1
    ELSE IF setpoint > 3500 W:
        phase ← 3
    // Between 3000–3500 W: keep current phase (avoids oscillation)

    // ──────────────────────────────────────────────
    // STEP 7: Calculate ampere from setpoint
    // ──────────────────────────────────────────────
    IF charging_on AND setpoint > 0:
        // Safety check: 1-phase can't exceed 3680 W (230V × 16A)
        IF phase == 1 AND setpoint > 3680 W:
            phase ← 3

        watts_per_amp ← 230 V × phase_count
        ampere ← CEIL(setpoint / watts_per_amp)
        ampere ← CLAMP(ampere, 6, 16)

    // ──────────────────────────────────────────────
    // STEP 8: Handle phase switching pause
    // ──────────────────────────────────────────────
    IF phase has changed from last cycle:
        pause_until ← now + 90 seconds
        // Next cycles will skip calculation until pause expires

    // ──────────────────────────────────────────────
    // STEP 9: Output results
    // ──────────────────────────────────────────────
    RETURN:
        surplus_power       → surplus
        battery_reserve     → battery_reserve (interpolated from curve)
        setpoint_power      → max(0, setpoint) if charging_on, else 0
        setpoint_ampere     → ampere
        charging_on         → charging_on
        phase_count         → phase
        is_1_phase          → (phase == 1)
```

## Algorithm Key Concepts

### Surplus Power Formula

```
surplus = −grid_power + house_battery_power + ev_power
```

This "reconstructs" total available solar by adding back what the EV and battery are already consuming to the current export. It answers: *"If we turned off EV and battery, how much would we be exporting?"*

### Setpoint (while charging)

```
setpoint = surplus − battery_reserve + fine_adjust
```

- **`−battery_reserve`**: Reserves capacity for the house battery. When SoC is low, reserve is high (battery priority). When SoC is high, reserve is low (EV priority). Derived from the characteristic curve via piecewise-linear interpolation, or from the static `max_battery_power` fallback.
- **`+fine_adjust`**: User-tunable offset. Positive = more aggressive (may pull small amounts from grid). Negative = more conservative (leaves more surplus unused).

### Battery Reserve Curve

The curve maps house battery SoC (%) → reserve power (W):

```
Reserve (W)
3000 ┤●
     │ ╲
2500 ┤  ●─────────●
     │             ╲
2000 ┤              ●
     │               ╲
 500 ┤                ●────●
   0 ┼───┬───┬───┬───┬───┬───►
     0   20  40  60  80  100  SoC (%)
```

**Interpolation**: For a SoC value between two breakpoints, the reserve is linearly interpolated.

**Editing**: The curve can be modified via:
1. Number entity sliders on the device page (fixed at 20%, 50%, 80% SoC)
2. Visual Lovelace card with draggable breakpoints (unlimited points)
3. Service call `charging_power_calculator.set_battery_reserve_curve`

### Hysteresis / Debouncing

The algorithm uses time-based hysteresis to avoid rapid toggling:

| Transition | Condition | Hold Time |
|------------|-----------|-----------|
| OFF → ON | Grid export > 500 W | Must hold for 60 s |
| ON → OFF | Setpoint negative | Must hold for 60 s |
| Phase switch | Setpoint crosses band | 90 s pause after switch |

### Phase Switching Band

```
        1-phase          hysteresis band         3-phase
    ◄──────────────┤ 3000 W ════════ 3500 W ├──────────────►
```

The 500 W dead-band prevents oscillation when the surplus hovers around the switching point.

## File Structure

```
charging_power_calculator/
├── __init__.py          # HA entry setup, service registration, card auto-loading
├── coordinator.py       # Core algorithm (DataUpdateCoordinator) + curve interpolation
├── sensor.py            # Sensor entities (power, ampere, surplus, battery reserve)
├── binary_sensor.py     # Binary sensor entities (on/off, phase)
├── number.py            # Number entities (curve breakpoint sliders)
├── config_flow.py       # UI configuration + options flow
├── const.py             # Constants and defaults
├── services.yaml        # Service definitions
├── manifest.json        # Integration metadata
├── strings.json         # UI strings
├── translations/
│   └── en.json          # English translations
└── www/
    └── battery-reserve-curve-card.js  # Custom Lovelace card (auto-registered)
```

## Example Scenario

| Time | Grid | Battery | EV | Surplus | Setpoint | Action |
|------|------|---------|----|---------|----------|--------|
| 12:00 | -800 W | 2000 W | 0 W | 2800 W | — | Export detected, start timer |
| 12:01 | -600 W | 2000 W | 0 W | 2600 W | 1400 W | Timer hit 60s → start at min |
| 12:02 | -100 W | 2000 W | 1400 W | 3500 W | 1500 W | Running: 3500−2500+500 |
| 12:03 | -500 W | 2000 W | 1500 W | 4000 W | 2000 W | Ramp up |
| 12:04 | -1000 W | 2500 W | 2000 W | 5500 W | 3500 W | Ramp up more |
| 12:05 | -1200 W | 2500 W | 3500 W | 7200 W | 5200 W | Switch to 3-phase, pause 90s |
| 12:07 | +200 W | 1000 W | 5200 W | 6000 W | 4000 W | After pause, adjust down |
