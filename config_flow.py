from __future__ import annotations

from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_CURRENT_CHARGING_ON,
    CONF_EV_POWER,
    CONF_FINE_ADJUST,
    CONF_GRID_POWER,
    CONF_HOUSE_BATTERY_POWER,
    CONF_MAX_BATTERY_POWER,
    CONF_MIN_EV_POWER,
    DEFAULT_FINE_ADJUST,
    DEFAULT_MAX_BATTERY_POWER,
    DEFAULT_MIN_EV_POWER,
    DOMAIN,
)


class ChargingPowerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="Charging Power Calculator", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_GRID_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Required(CONF_EV_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Required(CONF_HOUSE_BATTERY_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Required(CONF_CURRENT_CHARGING_ON): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean"])
                ),
                vol.Optional(CONF_MAX_BATTERY_POWER, default=DEFAULT_MAX_BATTERY_POWER): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=10000, step=100, unit_of_measurement="W")
                ),
                vol.Optional(CONF_MIN_EV_POWER, default=DEFAULT_MIN_EV_POWER): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=10000, step=100, unit_of_measurement="W")
                ),
                vol.Optional(CONF_FINE_ADJUST, default=DEFAULT_FINE_ADJUST): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=-5000, max=5000, step=50, unit_of_measurement="W")
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
