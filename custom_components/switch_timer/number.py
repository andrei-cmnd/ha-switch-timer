"""Run-time number for Switch Timer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
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

if TYPE_CHECKING:
    from . import SwitchTimerConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwitchTimerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the run-time number."""
    async_add_entities([RunTimeNumber(entry)])


class RunTimeNumber(SwitchTimerEntity, RestoreNumber):
    """Minutes used when a timed run starts without an explicit duration."""

    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, entry: SwitchTimerConfigEntry) -> None:
        """Initialize the number."""
        super().__init__(entry, "run_time")
        options = entry.options
        self._attr_native_min_value = options.get(
            CONF_RUN_TIME_MIN, DEFAULT_RUN_TIME_MIN
        )
        self._attr_native_max_value = options.get(
            CONF_RUN_TIME_MAX, DEFAULT_RUN_TIME_MAX
        )
        self._attr_native_step = options.get(CONF_RUN_TIME_STEP, DEFAULT_RUN_TIME_STEP)
        self._attr_native_value = self.manager.run_minutes

    async def async_added_to_hass(self) -> None:
        """Restore the last value, clamped to the current range."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            value = min(
                max(last.native_value, self.native_min_value), self.native_max_value
            )
            self._attr_native_value = value
            self.manager.async_set_run_minutes(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the run time."""
        self._attr_native_value = value
        self.manager.async_set_run_minutes(value)
        self.async_write_ha_state()
