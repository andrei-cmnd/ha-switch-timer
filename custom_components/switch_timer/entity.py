"""Base entity for Switch Timer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

if TYPE_CHECKING:
    from . import SwitchTimerConfigEntry


class SwitchTimerEntity(Entity):
    """An entity belonging to one Switch Timer config entry."""

    _attr_has_entity_name = True

    def __init__(self, entry: SwitchTimerConfigEntry, key: str) -> None:
        """Initialize the entity."""
        self.manager = entry.runtime_data
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )
