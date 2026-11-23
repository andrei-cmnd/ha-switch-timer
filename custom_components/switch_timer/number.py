"""Run-time number for Switch Timer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_RUN_TIME_MAX,
    CONF_RUN_TIME_MIN,
    CONF_RUN_TIME_STEP,
    DEFAULT_RUN_TIME_MAX,
    DEFAULT_RUN_TIME_MIN,
    DEFAULT_RUN_TIME_STEP,
)
from .entity import SwitchTimerEntity
from .manager import SwitchTimerManager

if TYPE_CHECKING:
    from . import SwitchTimerConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchTimerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a run-time number for every timer, now and when timers are added."""
    entry.runtime_data.async_register_platform(
        lambda manager: async_add_entities(
            [RunTimeNumber(manager)], config_subentry_id=manager.subentry_id
        )
    )


class RunTimeNumber(SwitchTimerEntity, RestoreNumber):
    """Minutes used when a timed run starts without an explicit duration."""

    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, manager: SwitchTimerManager) -> None:
        """Initialize the number."""
        super().__init__(manager, "run_time")
        self._attr_native_value = manager.run_minutes

    @property
    def native_min_value(self) -> float:
        """Lowest run time (timer setting)."""
        return self.manager.config.get(CONF_RUN_TIME_MIN, DEFAULT_RUN_TIME_MIN)

    @property
    def native_max_value(self) -> float:
        """Highest run time (timer setting)."""
        return self.manager.config.get(CONF_RUN_TIME_MAX, DEFAULT_RUN_TIME_MAX)

    @property
    def native_step(self) -> float:
        """Run time step (timer setting)."""
        return self.manager.config.get(CONF_RUN_TIME_STEP, DEFAULT_RUN_TIME_STEP)

    def _clamp(self, value: float) -> float:
        return min(max(value, self.native_min_value), self.native_max_value)

    async def async_added_to_hass(self) -> None:
        """Restore the last value, clamped to the current range; follow setting edits."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self._attr_native_value = self._clamp(last.native_value)
            self.manager.async_set_run_minutes(self._attr_native_value)
        self.async_on_remove(
            self.manager.async_add_listener(self._async_settings_changed)
        )

    @callback
    def _async_settings_changed(self) -> None:
        if self._attr_native_value is None:
            return
        value = self._clamp(self._attr_native_value)
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.manager.async_set_run_minutes(value)
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set the run time."""
        self._attr_native_value = value
        self.manager.async_set_run_minutes(value)
        self.async_write_ha_state()
