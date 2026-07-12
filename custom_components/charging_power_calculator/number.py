from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    CONF_BATTERY_CURVE,
    DEFAULT_BATTERY_CURVE,
    DOMAIN,
)
from .coordinator import ChargingPowerCoordinator

CURVE_BREAKPOINTS = [
    {"soc": 20, "label": "Reserve at 20% SoC"},
    {"soc": 50, "label": "Reserve at 50% SoC"},
    {"soc": 80, "label": "Reserve at 80% SoC"},
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: ChargingPowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            CurveBreakpointNumber(coordinator, entry, bp["soc"], bp["label"])
            for bp in CURVE_BREAKPOINTS
        ]
    )


class CurveBreakpointNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 5000
    _attr_native_step = 50
    _attr_native_unit_of_measurement = "W"
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: ChargingPowerCoordinator,
        entry: ConfigEntry,
        soc: int,
        label: str,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._soc = soc
        self._attr_name = label
        self._attr_unique_id = f"{entry.entry_id}_curve_soc_{soc}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Charging Power Calculator",
            manufacturer="Custom",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float:
        curve = self._entry.data.get(CONF_BATTERY_CURVE, DEFAULT_BATTERY_CURVE)
        return ChargingPowerCoordinator._interpolate_curve(self._soc, curve)

    async def async_set_native_value(self, value: float) -> None:
        curve = list(self._entry.data.get(CONF_BATTERY_CURVE, DEFAULT_BATTERY_CURVE))
        curve = [list(p) for p in curve]

        replaced = False
        for point in curve:
            if point[0] == self._soc:
                point[1] = value
                replaced = True
                break

        if not replaced:
            curve.append([self._soc, value])
            curve.sort(key=lambda p: p[0])

        self.hass.config_entries.async_update_entry(
            self._entry, data={**self._entry.data, CONF_BATTERY_CURVE: curve}
        )
        await self._coordinator.async_request_refresh()
        self.async_write_ha_state()
