from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import math
from typing import Any

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    AMPERE_MAX,
    AMPERE_MIN,
    CONF_BATTERY_CURVE,
    CONF_CURRENT_CHARGING_ON,
    CONF_EV_POWER,
    CONF_FINE_ADJUST,
    CONF_GRID_POWER,
    CONF_HOUSE_BATTERY_POWER,
    CONF_HOUSE_BATTERY_SOC,
    CONF_MAX_BATTERY_POWER,
    CONF_MIN_EV_POWER,
    DEFAULT_BATTERY_CURVE,
    DEFAULT_FINE_ADJUST,
    DEFAULT_MAX_BATTERY_POWER,
    DEFAULT_MIN_EV_POWER,
    KEY_BATTERY_RESERVE,
    KEY_IS_1_PHASE,
    KEY_PHASE_COUNT,
    KEY_SETPOINT_AMPERE,
    KEY_SETPOINT_CHARGING_ON,
    KEY_SETPOINT_POWER,
    KEY_SURPLUS,
    PHASE_SWITCH_DOWN_W,
    PHASE_SWITCH_PAUSE_SECONDS,
    PHASE_SWITCH_UP_W,
    START_EXPORT_SECONDS,
    START_EXPORT_THRESHOLD,
    STOP_SETPOINT_SECONDS,
    UPDATE_INTERVAL_SECONDS,
    VOLTAGE,
)


@dataclass
class InputSnapshot:
    grid_power: float
    ev_power: float
    house_battery_power: float
    current_charging_on: bool
    battery_reserve: float
    min_ev_power: float
    fine_adjust: float


_LOGGER = logging.getLogger(__name__)


class ChargingPowerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="charging_power_calculator",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self._entry = entry
        self._start_condition_since = None
        self._stop_condition_since = None
        self._pause_until = None
        self._last_phase = 1
        self._last_setpoint_on = False
        self._last_setpoint_power = 0.0
        self._last_setpoint_ampere = 0
        self._last_battery_reserve = 0.0

    async def _async_update_data(self) -> dict[str, Any]:
        now = dt_util.utcnow()
        snapshot = self._read_inputs()
        if snapshot is None:
            return {
                "available": False,
                KEY_SURPLUS: None,
                KEY_SETPOINT_POWER: self._last_setpoint_power,
                KEY_SETPOINT_AMPERE: None,
                KEY_IS_1_PHASE: self._last_phase == 1,
                KEY_SETPOINT_CHARGING_ON: self._last_setpoint_on,
                KEY_PHASE_COUNT: self._last_phase,
                KEY_BATTERY_RESERVE: self._last_battery_reserve,
            }

        surplus = (
            -snapshot.grid_power
            + snapshot.house_battery_power
            + snapshot.ev_power
        )

        self._last_battery_reserve = snapshot.battery_reserve

        if self._pause_until and now < self._pause_until:
            return {
                "available": True,
                KEY_SURPLUS: surplus,
                KEY_SETPOINT_POWER: self._last_setpoint_power,
                KEY_SETPOINT_AMPERE: self._last_setpoint_ampere,
                KEY_IS_1_PHASE: self._last_phase == 1,
                KEY_SETPOINT_CHARGING_ON: self._last_setpoint_on,
                KEY_PHASE_COUNT: self._last_phase,
                KEY_BATTERY_RESERVE: self._last_battery_reserve,
            }

        setpoint = 0.0

        if not snapshot.current_charging_on:
            if snapshot.grid_power < START_EXPORT_THRESHOLD:
                self._start_condition_since = self._start_condition_since or now
            else:
                self._start_condition_since = None

            if (
                self._start_condition_since
                and (now - self._start_condition_since).total_seconds()
                >= START_EXPORT_SECONDS
            ):
                setpoint = snapshot.min_ev_power
        else:
            self._start_condition_since = None
            setpoint = surplus - snapshot.battery_reserve + snapshot.fine_adjust

        setpoint_on = self._last_setpoint_on

        if setpoint > 0:
            if setpoint < snapshot.min_ev_power:
                setpoint = snapshot.min_ev_power
            setpoint_on = True
            self._stop_condition_since = None
        elif setpoint < 0:
            self._stop_condition_since = self._stop_condition_since or now
            if (
                self._stop_condition_since
                and (now - self._stop_condition_since).total_seconds()
                >= STOP_SETPOINT_SECONDS
            ):
                setpoint_on = False
        else:
            self._stop_condition_since = None

        phase = self._decide_phase(setpoint, self._last_phase)
        ampere = 0

        if setpoint_on and setpoint > 0:
            phase, ampere = self._calculate_ampere(setpoint, phase)

        if phase != self._last_phase:
            self._pause_until = now + timedelta(seconds=PHASE_SWITCH_PAUSE_SECONDS)

        self._last_phase = phase
        self._last_setpoint_on = setpoint_on
        self._last_setpoint_power = max(0.0, setpoint) if setpoint_on else 0.0
        self._last_setpoint_ampere = ampere

        return {
            "available": True,
            KEY_SURPLUS: surplus,
            KEY_SETPOINT_POWER: self._last_setpoint_power,
            KEY_SETPOINT_AMPERE: ampere,
            KEY_IS_1_PHASE: phase == 1,
            KEY_SETPOINT_CHARGING_ON: setpoint_on,
            KEY_PHASE_COUNT: phase,
            KEY_BATTERY_RESERVE: self._last_battery_reserve,
        }

    def _read_inputs(self) -> InputSnapshot | None:
        def _get_float(entity_id: str) -> float | None:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                return None
            try:
                return float(state.state)
            except ValueError:
                return None

        def _get_bool(entity_id: str) -> bool | None:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                return None
            return state.state in ("on", "true", "True", "1")

        grid_power = _get_float(self._entry.data[CONF_GRID_POWER])
        ev_power = _get_float(self._entry.data[CONF_EV_POWER])
        house_battery_power = _get_float(self._entry.data[CONF_HOUSE_BATTERY_POWER])
        current_charging_on = _get_bool(self._entry.data[CONF_CURRENT_CHARGING_ON])

        if (
            grid_power is None
            or ev_power is None
            or house_battery_power is None
            or current_charging_on is None
        ):
            return None

        min_ev_power = self._entry.data.get(
            CONF_MIN_EV_POWER, DEFAULT_MIN_EV_POWER
        )
        fine_adjust = self._entry.data.get(CONF_FINE_ADJUST, DEFAULT_FINE_ADJUST)

        battery_reserve = self._resolve_battery_reserve()

        return InputSnapshot(
            grid_power=grid_power,
            ev_power=ev_power,
            house_battery_power=house_battery_power,
            current_charging_on=current_charging_on,
            battery_reserve=battery_reserve,
            min_ev_power=float(min_ev_power),
            fine_adjust=float(fine_adjust),
        )

    def _resolve_battery_reserve(self) -> float:
        soc_entity = self._entry.data.get(CONF_HOUSE_BATTERY_SOC)
        curve = self._entry.data.get(CONF_BATTERY_CURVE, DEFAULT_BATTERY_CURVE)

        if not soc_entity:
            return float(
                self._entry.data.get(CONF_MAX_BATTERY_POWER, DEFAULT_MAX_BATTERY_POWER)
            )

        state = self.hass.states.get(soc_entity)
        if state is None or state.state in ("unknown", "unavailable"):
            return float(
                self._entry.data.get(CONF_MAX_BATTERY_POWER, DEFAULT_MAX_BATTERY_POWER)
            )

        try:
            soc = float(state.state)
        except ValueError:
            return float(
                self._entry.data.get(CONF_MAX_BATTERY_POWER, DEFAULT_MAX_BATTERY_POWER)
            )

        return self._interpolate_curve(soc, curve)

    @staticmethod
    def _interpolate_curve(soc: float, curve: list[list[float]]) -> float:
        if not curve:
            return DEFAULT_MAX_BATTERY_POWER
        curve = sorted(curve, key=lambda p: p[0])
        if soc <= curve[0][0]:
            return curve[0][1]
        if soc >= curve[-1][0]:
            return curve[-1][1]
        for i in range(len(curve) - 1):
            x0, y0 = curve[i]
            x1, y1 = curve[i + 1]
            if x0 <= soc <= x1:
                t = (soc - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return curve[-1][1]

    def _decide_phase(self, setpoint: float, current_phase: int) -> int:
        if setpoint < PHASE_SWITCH_DOWN_W:
            return 1
        if setpoint > PHASE_SWITCH_UP_W:
            return 3
        return current_phase

    def _calculate_ampere(self, setpoint: float, phase: int) -> tuple[int, int]:
        if phase == 1 and setpoint > 3680:
            phase = 3
        watts_per_amp = VOLTAGE * phase
        ampere = math.ceil(setpoint / watts_per_amp)
        ampere = max(AMPERE_MIN, min(AMPERE_MAX, ampere))
        return phase, ampere
