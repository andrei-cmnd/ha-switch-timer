"""Actions for the Switch Timer integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er
import voluptuous as vol

from .const import ATTR_MINUTES, DOMAIN, SERVICE_EXTEND, SERVICE_START, SERVICE_STOP

if TYPE_CHECKING:
    from .manager import SwitchTimerManager

_MINUTES = vol.All(vol.Coerce(int), vol.Range(min=1))

SCHEMA_WITH_MINUTES = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_MINUTES): _MINUTES,
    }
)
SCHEMA_STOP = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_ids})


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the start, extend and stop actions."""

    async def async_start(call: ServiceCall) -> None:
        for manager in _managers(hass, call):
            await manager.async_start(call.data.get(ATTR_MINUTES))

    async def async_extend(call: ServiceCall) -> None:
        for manager in _managers(hass, call):
            await manager.async_extend(call.data.get(ATTR_MINUTES))

    async def async_stop(call: ServiceCall) -> None:
        for manager in _managers(hass, call):
            await manager.async_stop()

    hass.services.async_register(
        DOMAIN, SERVICE_START, async_start, SCHEMA_WITH_MINUTES
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EXTEND, async_extend, SCHEMA_WITH_MINUTES
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP, async_stop, SCHEMA_STOP)


def _managers(hass: HomeAssistant, call: ServiceCall) -> list[SwitchTimerManager]:
    """Resolve the targeted entities to their managers.

    A target is either one of our own entities or the controlled entity itself.
    """
    registry = er.async_get(hass)
    hubs = [
        entry.runtime_data for entry in hass.config_entries.async_loaded_entries(DOMAIN)
    ]

    managers: list[SwitchTimerManager] = []
    for entity_id in call.data[ATTR_ENTITY_ID]:
        manager: SwitchTimerManager | None = None
        reg_entry = registry.async_get(entity_id)
        for hub in hubs:
            if reg_entry is not None and reg_entry.platform == DOMAIN:
                manager = hub.managers.get(reg_entry.config_subentry_id or "")
            else:
                manager = hub.manager_for_entity(entity_id)
            if manager is not None:
                break
        if manager is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entity_not_managed",
                translation_placeholders={"entity_id": entity_id},
            )
        if manager not in managers:
            managers.append(manager)
    return managers
