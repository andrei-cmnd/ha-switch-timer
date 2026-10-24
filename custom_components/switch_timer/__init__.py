"""The Switch Timer integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, STORAGE_VERSION
from .manager import SwitchTimerManager, storage_key
from .services import async_setup_services

PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type SwitchTimerConfigEntry = ConfigEntry[SwitchTimerManager]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the Switch Timer actions."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SwitchTimerConfigEntry) -> bool:
    """Set up a Switch Timer from a config entry."""
    manager = SwitchTimerManager(hass, entry)
    await manager.async_setup()
    entry.runtime_data = manager
    entry.async_on_unload(manager.async_unload)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SwitchTimerConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the saved run when the entry is removed."""
    await Store(hass, STORAGE_VERSION, storage_key(entry.entry_id)).async_remove()
