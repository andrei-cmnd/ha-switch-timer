"""Diagnostics for Switch Timer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from . import SwitchTimerConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SwitchTimerConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the hub and every timer."""
    return {
        "entry": {"title": entry.title, "data": dict(entry.data)},
        "timers": {
            subentry_id: manager.as_diagnostics()
            for subentry_id, manager in entry.runtime_data.managers.items()
        },
    }
