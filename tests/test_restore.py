"""Restart tests: a saved run is restored and settled once HA has started."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import CoreState, HomeAssistant, ServiceCall
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.switch_timer.const import DOMAIN

from .conftest import ENDS_AT, ENTRY_ID, PUMP

STORAGE_KEY = f"{DOMAIN}.{ENTRY_ID}"


def _saved_run(hass_storage: dict[str, Any], ends_in: timedelta) -> None:
    now = dt_util.utcnow()
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {
            "run": {
                "started_at": (now + ends_in - timedelta(minutes=30)).isoformat(),
                "ends_at": (now + ends_in).isoformat(),
                "duration": 1800,
            }
        },
    }


@pytest.fixture
def turn_off_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Record homeassistant.turn_off calls; the pump state is set by each test."""
    return async_mock_service(hass, "homeassistant", "turn_off")


async def _boot(
    hass: HomeAssistant, config_entry: MockConfigEntry, pump_state: str
) -> None:
    """Set up the entry as during startup, then finish starting HA."""
    hass.set_state(CoreState.not_running)
    hass.states.async_set(PUMP, pump_state)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def _started(hass: HomeAssistant) -> None:
    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()


async def test_restart_after_end_time_turns_off(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: MockConfigEntry,
    turn_off_calls: list[ServiceCall],
) -> None:
    """End time passed while HA was down: turn off once HA has started."""
    _saved_run(hass_storage, timedelta(minutes=-5))
    await _boot(hass, config_entry, STATE_ON)
    assert turn_off_calls == []

    await _started(hass)

    assert len(turn_off_calls) == 1
    assert turn_off_calls[0].data[ATTR_ENTITY_ID] == PUMP
    assert hass.states.get(ENDS_AT).state == "unknown"
    assert hass_storage[STORAGE_KEY]["data"]["run"] is None


async def test_restart_before_end_time_keeps_counting(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: MockConfigEntry,
    turn_off_calls: list[ServiceCall],
    freezer: FrozenDateTimeFactory,
) -> None:
    """End time still ahead: keep the run and turn off on time."""
    _saved_run(hass_storage, timedelta(minutes=5))
    await _boot(hass, config_entry, STATE_ON)
    await _started(hass)

    state = hass.states.get(ENDS_AT)
    assert state.attributes["mode"] == "timed"
    assert state.attributes["duration"] == 1800
    assert turn_off_calls == []

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(turn_off_calls) == 1


async def test_restart_waits_for_entity(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: MockConfigEntry,
    turn_off_calls: list[ServiceCall],
) -> None:
    """Entity unavailable after the restart: turn off when it becomes available."""
    _saved_run(hass_storage, timedelta(minutes=-5))
    await _boot(hass, config_entry, STATE_UNAVAILABLE)
    await _started(hass)
    assert turn_off_calls == []

    hass.states.async_set(PUMP, STATE_ON)
    await hass.async_block_till_done()

    assert len(turn_off_calls) == 1
    assert hass.states.get(ENDS_AT).state == "unknown"


async def test_restart_entity_found_off_drops_run(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: MockConfigEntry,
    turn_off_calls: list[ServiceCall],
) -> None:
    """Entity came back off: the run is cleared without a turn_off."""
    _saved_run(hass_storage, timedelta(minutes=5))
    await _boot(hass, config_entry, STATE_OFF)
    await _started(hass)

    assert turn_off_calls == []
    assert hass.states.get(ENDS_AT).state == "unknown"
    assert hass_storage[STORAGE_KEY]["data"]["run"] is None


async def test_restart_manual_on_does_nothing(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    turn_off_calls: list[ServiceCall],
    freezer: FrozenDateTimeFactory,
) -> None:
    """On with no timed run: left alone."""
    await _boot(hass, config_entry, STATE_ON)
    await _started(hass)

    freezer.tick(timedelta(hours=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert turn_off_calls == []
    assert hass.states.get(ENDS_AT).attributes["mode"] == "manual"


async def test_malformed_saved_run_is_ignored(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    config_entry: MockConfigEntry,
    turn_off_calls: list[ServiceCall],
) -> None:
    """A corrupt saved run is treated as no run."""
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {"run": {"ends_at": "garbage"}},
    }
    await _boot(hass, config_entry, STATE_ON)
    await _started(hass)

    assert turn_off_calls == []
    assert hass.states.get(ENDS_AT).attributes["mode"] == "manual"


@pytest.mark.usefixtures("setup_entry")
async def test_reload_keeps_run(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Reloading the entry (e.g. after an options change) keeps the run."""
    await hass.services.async_call(
        DOMAIN, "start", {ATTR_ENTITY_ID: PUMP, "minutes": 10}, blocking=True
    )
    ends_at = hass.states.get(ENDS_AT).state

    assert await hass.config_entries.async_reload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ENDS_AT).state == ends_at

    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(PUMP).state == STATE_OFF
