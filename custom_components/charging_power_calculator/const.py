DOMAIN = "charging_power_calculator"
PLATFORMS = ["sensor", "binary_sensor"]

CONF_GRID_POWER = "grid_power"
CONF_EV_POWER = "ev_charging_power"
CONF_HOUSE_BATTERY_POWER = "house_battery_power"
CONF_CURRENT_CHARGING_ON = "current_charging_on"

CONF_MAX_BATTERY_POWER = "max_charging_power_house_battery"
CONF_MIN_EV_POWER = "min_charging_power_ev"
CONF_FINE_ADJUST = "fine_adjust"

DEFAULT_MAX_BATTERY_POWER = 2500.0
DEFAULT_MIN_EV_POWER = 1400.0
DEFAULT_FINE_ADJUST = 500.0

UPDATE_INTERVAL_SECONDS = 31
START_EXPORT_THRESHOLD = -500.0
START_EXPORT_SECONDS = 60
STOP_SETPOINT_SECONDS = 60
PHASE_SWITCH_PAUSE_SECONDS = 90

PHASE_SWITCH_UP_W = 3500.0
PHASE_SWITCH_DOWN_W = 3000.0

VOLTAGE = 230.0
AMPERE_MIN = 6
AMPERE_MAX = 16

KEY_SURPLUS = "surplus_power_avail"
KEY_SETPOINT_POWER = "setpoint_ev_charging_power"
KEY_SETPOINT_AMPERE = "setpoint_ampere"
KEY_IS_1_PHASE = "is_1_phase_charging"
KEY_SETPOINT_CHARGING_ON = "setpoint_charging_on"
KEY_PHASE_COUNT = "phase_count"
