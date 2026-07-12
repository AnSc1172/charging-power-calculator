from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, KEY_IS_1_PHASE, KEY_SETPOINT_CHARGING_ON
from .coordinator import ChargingPowerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: ChargingPowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            ChargingPowerBinarySensor(
                coordinator,
                "Setpoint Charging On",
                KEY_SETPOINT_CHARGING_ON,
                entry.entry_id,
            ),
            ChargingPowerBinarySensor(
                coordinator,
                "Is 1 Phase Charging",
                KEY_IS_1_PHASE,
                entry.entry_id,
            ),
        ]
    )


class ChargingPowerBinarySensor(
    CoordinatorEntity[ChargingPowerCoordinator], BinarySensorEntity
):
    def __init__(
        self,
        coordinator: ChargingPowerCoordinator,
        name: str,
        key: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._key = key
        self._attr_unique_id = f"{entry_id}_{key}"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get(self._key))

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data.get("available", True))
