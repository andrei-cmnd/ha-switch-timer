"""The Switch Timer integration.

One "Switch Timer" config entry (the hub) loads the integration and the card. Each
controlled entity gets a "timer" config subentry, created automatically when an admin
picks the entity in a Switch Timer card.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .card import async_register_card
from .const import DOMAIN, STORAGE_VERSION, SUBENTRY_TYPE_TIMER
from .hub import SwitchTimerHub
from .manager import storage_key
from .services import async_setup_services
from .websocket import async_setup_websocket

PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type SwitchTimerConfigEntry = ConfigEntry[SwitchTimerHub]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions, the websocket command and the card."""
    async_setup_services(hass)
    async_setup_websocket(hass)
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SwitchTimerConfigEntry) -> bool:
    """Set up the hub and a manager per timer subentry."""
    hub = SwitchTimerHub(hass, entry)
    entry.runtime_data = hub
    await hub.async_setup()
    entry.async_on_unload(hub.async_unload)
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_entry_updated(
    hass: HomeAssistant, entry: SwitchTimerConfigEntry
) -> None:
    """Timers were added, removed or edited: sync without reloading."""
    await entry.runtime_data.async_sync()


async def async_unload_entry(
    hass: HomeAssistant, entry: SwitchTimerConfigEntry
) -> bool:
    """Unload the hub."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the saved runs when the hub is removed."""
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_TYPE_TIMER:
            await Store(hass, STORAGE_VERSION, storage_key(subentry_id)).async_remove()
