"""Ends-at sensor for Switch Timer."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ATTR_CONTROLLED_ENTITY_ID, ATTR_DURATION, ATTR_MODE, ATTR_STARTED_AT
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
    """Set up an ends-at sensor for every timer, now and when timers are added."""
    entry.runtime_data.async_register_platform(
        lambda manager: async_add_entities(
            [EndsAtSensor(manager)], config_subentry_id=manager.subentry_id
        )
    )


class EndsAtSensor(SwitchTimerEntity, SensorEntity):
    """When the current timed run ends; None without one."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    # Static link for the card; no need to store it in the recorder.
    _unrecorded_attributes = frozenset({ATTR_CONTROLLED_ENTITY_ID})

    def __init__(self, manager: SwitchTimerManager) -> None:
        """Initialize the sensor."""
        super().__init__(manager, "ends_at")

    async def async_added_to_hass(self) -> None:
        """Follow the manager."""
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> datetime | None:
        """Return the end time of the timed run."""
        return run.ends_at if (run := self.manager.run) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return mode, duration, start time and the controlled entity."""
        run = self.manager.run
        return {
            ATTR_CONTROLLED_ENTITY_ID: self.manager.entity_id,
            ATTR_MODE: self.manager.mode,
            ATTR_DURATION: run.duration if run else None,
            ATTR_STARTED_AT: run.started_at.isoformat() if run else None,
        }
