from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_BATTERY_CURVE,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_CURVE,
)
from .coordinator import ChargingPowerCoordinator

CARD_URL = "/charging_power_calculator/battery-reserve-curve-card.js"
CARD_DIR = Path(__file__).parent / "www"
CARD_FILENAME = "battery-reserve-curve-card.js"

SERVICE_SCHEMA_SET_CURVE = vol.Schema(
    {
        vol.Required("entry_id"): cv.string,
        vol.Required("curve"): vol.All(
            cv.ensure_list,
            [vol.All(vol.ExactSequence([vol.Coerce(float), vol.Coerce(float)]))],
        ),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ChargingPowerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Serve the Lovelace card JS and auto-register it (only once)
    if f"{DOMAIN}_card_registered" not in hass.data:
        hass.data[f"{DOMAIN}_card_registered"] = True
        card_path = str(CARD_DIR / CARD_FILENAME)
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, card_path, cache_headers=False)]
        )
        add_extra_js_url(hass, CARD_URL)

    async def handle_set_curve(call: ServiceCall) -> None:
        entry_id = call.data["entry_id"]
        curve = call.data["curve"]
        target_entry = hass.config_entries.async_get_entry(entry_id)
        if target_entry is None:
            return
        hass.config_entries.async_update_entry(
            target_entry, data={**target_entry.data, CONF_BATTERY_CURVE: curve}
        )
        coord = hass.data[DOMAIN].get(entry_id)
        if coord:
            await coord.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_SET_CURVE):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_CURVE, handle_set_curve, schema=SERVICE_SCHEMA_SET_CURVE
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_SET_CURVE)
    return unload_ok
