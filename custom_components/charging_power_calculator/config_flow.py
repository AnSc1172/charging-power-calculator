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
    CONF_HOUSE_BATTERY_SOC,
    CONF_MAX_BATTERY_POWER,
    CONF_MIN_EV_POWER,
    DEFAULT_FINE_ADJUST,
    DEFAULT_MAX_BATTERY_POWER,
    DEFAULT_MIN_EV_POWER,
    DOMAIN,
)


class ChargingPowerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return ChargingPowerOptionsFlow(config_entry)

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
                vol.Optional(CONF_HOUSE_BATTERY_SOC): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
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


class ChargingPowerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self._config_entry, data={**self._config_entry.data, **user_input}
            )
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        current = self._config_entry.data

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_GRID_POWER,
                    default=current.get(CONF_GRID_POWER),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Required(
                    CONF_EV_POWER,
                    default=current.get(CONF_EV_POWER),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Required(
                    CONF_HOUSE_BATTERY_POWER,
                    default=current.get(CONF_HOUSE_BATTERY_POWER),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Required(
                    CONF_CURRENT_CHARGING_ON,
                    default=current.get(CONF_CURRENT_CHARGING_ON),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean"])
                ),
                vol.Optional(
                    CONF_HOUSE_BATTERY_SOC,
                    description={"suggested_value": current.get(CONF_HOUSE_BATTERY_SOC)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Optional(
                    CONF_MAX_BATTERY_POWER,
                    default=current.get(CONF_MAX_BATTERY_POWER, DEFAULT_MAX_BATTERY_POWER),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=10000, step=100, unit_of_measurement="W")
                ),
                vol.Optional(
                    CONF_MIN_EV_POWER,
                    default=current.get(CONF_MIN_EV_POWER, DEFAULT_MIN_EV_POWER),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=10000, step=100, unit_of_measurement="W")
                ),
                vol.Optional(
                    CONF_FINE_ADJUST,
                    default=current.get(CONF_FINE_ADJUST, DEFAULT_FINE_ADJUST),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=-5000, max=5000, step=50, unit_of_measurement="W")
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
