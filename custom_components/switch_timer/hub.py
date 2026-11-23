"""The Switch Timer hub: one config entry, one timer subentry per controlled entity."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DEFAULT_OPTIONS, SUBENTRY_TYPE_TIMER
from .manager import SwitchTimerManager

_LOGGER = logging.getLogger(__name__)

type EntityAdder = Callable[[SwitchTimerManager], None]


class SwitchTimerHub:
    """Keep one manager (and its entities) per timer subentry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.entry = entry
        self.managers: dict[str, SwitchTimerManager] = {}
        self._adders: list[EntityAdder] = []
        self._lock = asyncio.Lock()  # one timer per entity
        self._sync_lock = asyncio.Lock()  # one sync at a time

    async def async_setup(self) -> None:
        """Create managers for the existing timers and follow the entity registry."""
        await self.async_sync()
        self.entry.async_on_unload(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._async_registry_updated
            )
        )

    @callback
    def async_unload(self) -> None:
        """Unload all managers; saved runs are kept."""
        for manager in self.managers.values():
            manager.async_unload()
        self.managers.clear()

    @callback
    def async_register_platform(self, adder: EntityAdder) -> None:
        """Register a platform's entity factory; called now and for every new timer."""
        self._adders.append(adder)
        for manager in self.managers.values():
            adder(manager)

    def timer_subentries(self) -> dict[str, ConfigSubentry]:
        """Return the timer subentries by id."""
        return {
            subentry_id: subentry
            for subentry_id, subentry in self.entry.subentries.items()
            if subentry.subentry_type == SUBENTRY_TYPE_TIMER
        }

    def manager_for_entity(self, entity_id: str) -> SwitchTimerManager | None:
        """Return the manager controlling entity_id."""
        return next(
            (m for m in self.managers.values() if m.entity_id == entity_id), None
        )

    async def async_sync(self) -> None:
        """Bring managers in line with the subentries (added, removed, edited)."""
        async with self._sync_lock:
            await self._async_sync()

    async def _async_sync(self) -> None:
        current = self.timer_subentries()
        for subentry_id in list(self.managers.keys() - current.keys()):
            # The timer was removed (HA already removed its entities and device).
            manager = self.managers.pop(subentry_id)
            manager.async_unload()
            await manager.async_remove_storage()
            _LOGGER.debug("%s: timer removed", manager.entity_id)
        for subentry_id, subentry in current.items():
            if (manager := self.managers.get(subentry_id)) is not None:
                if (
                    dict(subentry.data) != manager.config
                    or subentry.title != manager.title
                ):
                    manager.async_update_config(subentry)
                continue
            manager = SwitchTimerManager(self.hass, self.entry, subentry)
            await manager.async_setup()
            self.managers[subentry_id] = manager
            for adder in self._adders:
                adder(manager)
            _LOGGER.debug("%s: timer added", manager.entity_id)

    async def async_ensure_timer(self, entity_id: str) -> tuple[str, bool]:
        """Return (subentry_id, created); create a timer with the defaults if needed."""
        async with self._lock:
            for subentry_id, subentry in self.timer_subentries().items():
                if subentry.unique_id == entity_id:
                    return subentry_id, False
            state = self.hass.states.get(entity_id)
            title = (state and state.attributes.get(ATTR_FRIENDLY_NAME)) or entity_id
            subentry = ConfigSubentry(
                data=MappingProxyType({ATTR_ENTITY_ID: entity_id, **DEFAULT_OPTIONS}),
                subentry_type=SUBENTRY_TYPE_TIMER,
                title=title,
                unique_id=entity_id,
            )
            self.hass.config_entries.async_add_subentry(self.entry, subentry)
            await self.async_sync()
            return subentry.subentry_id, True

    @callback
    def _async_registry_updated(
        self, event: Event[er.EventEntityRegistryUpdatedData]
    ) -> None:
        """Remove a timer whose entity was deleted; follow a renamed entity."""
        data = event.data
        if data["action"] == "remove":
            old_id, new_id = data["entity_id"], None
        elif data["action"] == "update" and "old_entity_id" in data:
            old_id, new_id = data["old_entity_id"], data["entity_id"]
        else:
            return
        for subentry in self.timer_subentries().values():
            if subentry.data[ATTR_ENTITY_ID] != old_id:
                continue
            if new_id is None:
                _LOGGER.debug("%s was deleted; removing its timer", old_id)
                self.hass.config_entries.async_remove_subentry(
                    self.entry, subentry.subentry_id
                )
            else:
                _LOGGER.debug("%s was renamed to %s; timer follows", old_id, new_id)
                self.hass.config_entries.async_update_subentry(
                    self.entry,
                    subentry,
                    data={**subentry.data, ATTR_ENTITY_ID: new_id},
                    unique_id=new_id,
                )
