"""Serve the bundled Lovelace card and load it in the frontend."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "switch-timer-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / CARD_FILENAME
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card JS and add it to every dashboard, no Lovelace resource needed.

    The URL carries a hash of the file, so browsers may cache it and still pick
    up a new version after an update.
    """
    if not {"frontend", "http"} <= hass.config.components:
        _LOGGER.debug("Frontend not loaded; the card is not registered")
        return
    digest = await hass.async_add_executor_job(_file_hash, CARD_PATH)
    if digest is None:
        _LOGGER.warning(
            "Switch Timer card not found at %s; build it with `npm run build` in frontend/",
            CARD_PATH,
        )
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=True)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={digest}")


def _file_hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except FileNotFoundError:
        return None
