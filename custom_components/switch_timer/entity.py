"""Base entity for Switch Timer."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .manager import SwitchTimerManager


class SwitchTimerEntity(Entity):
    """An entity belonging to one timer (config subentry); one device per timer."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: SwitchTimerManager, key: str) -> None:
        """Initialize the entity."""
        self.manager = manager
        self._attr_translation_key = key
        self._attr_unique_id = f"{manager.subentry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.subentry_id)},
            name=manager.title,
            entry_type=DeviceEntryType.SERVICE,
        )
