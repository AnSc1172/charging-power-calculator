from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    KEY_SETPOINT_AMPERE,
    KEY_SETPOINT_POWER,
    KEY_SURPLUS,
)
from .coordinator import ChargingPowerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: ChargingPowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            ChargingPowerSensor(
                coordinator,
                "Setpoint EV Charging Power",
                KEY_SETPOINT_POWER,
                "W",
                entry.entry_id,
            ),
            ChargingPowerSensor(
                coordinator,
                "Setpoint Ampere",
                KEY_SETPOINT_AMPERE,
                "A",
                entry.entry_id,
            ),
            ChargingPowerSensor(
                coordinator,
                "Surplus Power Available",
                KEY_SURPLUS,
                "W",
                entry.entry_id,
            ),
        ]
    )


class ChargingPowerSensor(CoordinatorEntity[ChargingPowerCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: ChargingPowerCoordinator,
        name: str,
        key: str,
        unit: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{entry_id}_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data.get("available", True))
