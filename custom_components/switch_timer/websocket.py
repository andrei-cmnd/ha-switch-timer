"""Websocket command used by the card to create timers automatically."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components import websocket_api
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import DOMAIN, SUPPORTED_DOMAINS

if TYPE_CHECKING:
    from . import SwitchTimerConfigEntry


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the websocket commands."""
    websocket_api.async_register_command(hass, ws_ensure_timer)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/ensure_timer",
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_ensure_timer(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Make sure entity_id has a timer; create one with the defaults if not."""
    entity_id: str = msg[ATTR_ENTITY_ID]
    entries: list[SwitchTimerConfigEntry] = hass.config_entries.async_loaded_entries(
        DOMAIN
    )
    if not entries:
        connection.send_error(
            msg["id"], "not_loaded", "The Switch Timer integration is not set up"
        )
        return
    if entity_id.split(".", maxsplit=1)[0] not in SUPPORTED_DOMAINS:
        connection.send_error(
            msg["id"],
            "not_supported",
            "Switch Timer works with switches, lights, fans and toggles",
        )
        return
    if hass.states.get(entity_id) is None:
        connection.send_error(msg["id"], "not_found", f"Entity not found: {entity_id}")
        return
    subentry_id, created = await entries[0].runtime_data.async_ensure_timer(entity_id)
    connection.send_result(msg["id"], {"subentry_id": subentry_id, "created": created})
