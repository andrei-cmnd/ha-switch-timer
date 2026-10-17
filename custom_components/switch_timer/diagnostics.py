"""Diagnostics for Switch Timer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from . import SwitchTimerConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SwitchTimerConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "manager": entry.runtime_data.as_diagnostics(),
    }
