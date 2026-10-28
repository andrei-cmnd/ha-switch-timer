"""Tests for serving and loading the bundled card."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.switch_timer import card


@pytest.fixture
def frontend_loaded(hass: HomeAssistant) -> Mock:
    """Pretend frontend and http are set up; return the http mock."""
    hass.config.components.update({"frontend", "http"})
    hass.http = Mock(async_register_static_paths=AsyncMock())
    return hass.http


async def test_card_registered_with_content_hash(
    hass: HomeAssistant, frontend_loaded: Mock, tmp_path: Path
) -> None:
    """The card is served and added as an extra module with a content hash."""
    card_js = tmp_path / card.CARD_FILENAME
    card_js.write_text("console.log('card');")
    digest = hashlib.sha256(card_js.read_bytes()).hexdigest()[:12]

    with (
        patch.object(card, "CARD_PATH", card_js),
        patch.object(card, "add_extra_js_url") as add_url,
    ):
        await card.async_register_card(hass)

    (configs,) = frontend_loaded.async_register_static_paths.call_args.args
    assert configs[0].url_path == "/switch_timer/switch-timer-card.js"
    assert configs[0].path == str(card_js)
    assert configs[0].cache_headers is True
    add_url.assert_called_once_with(
        hass, f"/switch_timer/switch-timer-card.js?v={digest}"
    )


async def test_card_hash_changes_with_content(
    hass: HomeAssistant, frontend_loaded: Mock, tmp_path: Path
) -> None:
    """A rebuilt card gets a new URL, so cached copies are not reused."""
    card_js = tmp_path / card.CARD_FILENAME
    urls = []
    for content in ("v1", "v2"):
        card_js.write_text(content)
        with (
            patch.object(card, "CARD_PATH", card_js),
            patch.object(card, "add_extra_js_url") as add_url,
        ):
            await card.async_register_card(hass)
        urls.append(add_url.call_args.args[1])

    assert urls[0] != urls[1]


async def test_card_missing_is_skipped(
    hass: HomeAssistant,
    frontend_loaded: Mock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Without a built card the integration still works and logs a warning."""
    with (
        patch.object(card, "CARD_PATH", tmp_path / "missing.js"),
        patch.object(card, "add_extra_js_url") as add_url,
    ):
        await card.async_register_card(hass)

    frontend_loaded.async_register_static_paths.assert_not_called()
    add_url.assert_not_called()
    assert "npm run build" in caplog.text


async def test_card_skipped_without_frontend(hass: HomeAssistant) -> None:
    """Headless setups (no frontend) don't register the card."""
    with patch.object(card, "add_extra_js_url") as add_url:
        await card.async_register_card(hass)

    add_url.assert_not_called()
