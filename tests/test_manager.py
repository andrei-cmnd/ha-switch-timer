"""Behavior tests: one or more tests per row of the behavior table."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.switch_timer.const import DOMAIN
from custom_components.switch_timer.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.switch_timer.manager import SwitchTimerManager

from .conftest import ENDS_AT, ENTRY_ID, PUMP, RUN_TIME

pytestmark = pytest.mark.usefixtures("whole_second", "setup_entry")


@pytest.fixture
def whole_second(freezer: FrozenDateTimeFactory) -> None:
    """Start on a whole second; run times are stored without microseconds."""
    freezer.move_to("2026-10-17T12:00:00+00:00")


async def _call(
    hass: HomeAssistant, service: str, target: str = PUMP, **data: Any
) -> None:
    await hass.services.async_call(
        DOMAIN, service, {ATTR_ENTITY_ID: target, **data}, blocking=True
    )


async def _turn(hass: HomeAssistant, service: str) -> None:
    """Switch the pump from outside Switch Timer."""
    await hass.services.async_call(
        "input_boolean", service, {ATTR_ENTITY_ID: PUMP}, blocking=True
    )


async def _advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, delta: timedelta
) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _pump(hass: HomeAssistant) -> str:
    return hass.states.get(PUMP).state


def _ends_at(hass: HomeAssistant) -> datetime | None:
    return dt_util.parse_datetime(hass.states.get(ENDS_AT).state)


def _attrs(hass: HomeAssistant) -> dict[str, Any]:
    return dict(hass.states.get(ENDS_AT).attributes)


# --- Run started via card / switch_timer.start --------------------------------


@pytest.mark.parametrize("target", [PUMP, ENDS_AT, RUN_TIME])
async def test_start_with_minutes(hass: HomeAssistant, target: str) -> None:
    """Start turns the entity on and starts a timed run of the given length."""
    now = dt_util.utcnow().replace(microsecond=0)
    await _call(hass, "start", target, minutes=10)

    assert _pump(hass) == STATE_ON
    assert _ends_at(hass) == now + timedelta(minutes=10)
    attrs = _attrs(hass)
    assert attrs["mode"] == "timed"
    assert attrs["duration"] == 600
    assert dt_util.parse_datetime(attrs["started_at"]) == now


async def test_sensor_links_controlled_entity(hass: HomeAssistant) -> None:
    """The card finds the sensor through its controlled_entity_id attribute."""
    assert _attrs(hass)["controlled_entity_id"] == PUMP


async def test_start_uses_run_time_number(hass: HomeAssistant) -> None:
    """Without minutes, the run lasts as long as the run-time number says."""
    await hass.services.async_call(
        "number", "set_value", {ATTR_ENTITY_ID: RUN_TIME, "value": 7}, blocking=True
    )
    now = dt_util.utcnow().replace(microsecond=0)
    await _call(hass, "start")

    assert _ends_at(hass) == now + timedelta(minutes=7)
    assert _attrs(hass)["duration"] == 420


async def test_start_while_manual_starts_timer(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Starting while the entity is already on manually adds a timer."""
    await _turn(hass, "turn_on")
    await _call(hass, "start", minutes=5)

    assert _attrs(hass)["mode"] == "timed"
    await _advance(hass, freezer, timedelta(minutes=5))
    assert _pump(hass) == STATE_OFF


async def test_start_failure_rolls_back(hass: HomeAssistant) -> None:
    """If turning on fails, no timed run is left behind."""
    with (
        patch.object(
            SwitchTimerManager, "_async_call", side_effect=HomeAssistantError("boom")
        ),
        pytest.raises(HomeAssistantError),
    ):
        await _call(hass, "start", minutes=5)

    assert _ends_at(hass) is None


async def test_unknown_target(hass: HomeAssistant) -> None:
    """Entities without a Switch Timer are rejected."""
    with pytest.raises(ServiceValidationError):
        await _call(hass, "start", "switch.unknown")


# --- Entity turned on anywhere else -------------------------------------------


async def test_turned_on_elsewhere_has_no_timer(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Turning on elsewhere means manual mode: no end time, never turned off."""
    await _turn(hass, "turn_on")

    assert _ends_at(hass) is None
    assert _attrs(hass)["mode"] == "manual"
    await _advance(hass, freezer, timedelta(hours=5))
    assert _pump(hass) == STATE_ON


# --- Entity turned off anywhere during a timed run ----------------------------


async def test_turned_off_elsewhere_cancels_run(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Turning off elsewhere clears the run; its old end time does nothing."""
    await _call(hass, "start", minutes=10)
    await _turn(hass, "turn_off")

    assert _ends_at(hass) is None
    attrs = _attrs(hass)
    assert (attrs["mode"], attrs["duration"], attrs["started_at"]) == (
        "off",
        None,
        None,
    )

    await _turn(hass, "turn_on")
    await _advance(hass, freezer, timedelta(minutes=15))
    assert _pump(hass) == STATE_ON
    assert _attrs(hass)["mode"] == "manual"


async def test_unavailable_transitions_are_ignored(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """on → unavailable → on keeps the run running."""
    await _call(hass, "start", minutes=10)
    ends_at = _ends_at(hass)

    hass.states.async_set(PUMP, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    hass.states.async_set(PUMP, STATE_ON)
    await hass.async_block_till_done()

    assert _ends_at(hass) == ends_at
    await _advance(hass, freezer, timedelta(minutes=10))
    assert _pump(hass) == STATE_OFF


# --- switch_timer.extend -------------------------------------------------------


async def test_extend_active_run(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Extend adds the default 15 minutes, or the given minutes."""
    now = dt_util.utcnow().replace(microsecond=0)
    await _call(hass, "start", minutes=10)
    await _call(hass, "extend")
    await _call(hass, "extend", ENDS_AT, minutes=5)

    assert _ends_at(hass) == now + timedelta(minutes=30)
    assert _attrs(hass)["duration"] == 30 * 60

    await _advance(hass, freezer, timedelta(minutes=29))
    assert _pump(hass) == STATE_ON
    await _advance(hass, freezer, timedelta(minutes=1))
    assert _pump(hass) == STATE_OFF


@pytest.mark.parametrize("pump_on", [False, True])
async def test_extend_without_run_does_nothing(
    hass: HomeAssistant, pump_on: bool
) -> None:
    """Extend needs an active timed run."""
    if pump_on:
        await _turn(hass, "turn_on")
    await _call(hass, "extend", minutes=5)

    assert _ends_at(hass) is None
    assert _pump(hass) == (STATE_ON if pump_on else STATE_OFF)


# --- switch_timer.stop ---------------------------------------------------------


async def test_stop_timed_run(hass: HomeAssistant) -> None:
    """Stop turns the entity off and clears the run."""
    await _call(hass, "start", minutes=10)
    await _call(hass, "stop", ENDS_AT)

    assert _pump(hass) == STATE_OFF
    assert _ends_at(hass) is None
    assert _attrs(hass)["mode"] == "off"


async def test_stop_manual(hass: HomeAssistant) -> None:
    """Stop also turns off an entity that was turned on manually."""
    await _turn(hass, "turn_on")
    await _call(hass, "stop")

    assert _pump(hass) == STATE_OFF


# --- Timed run reaches end time ------------------------------------------------


async def test_run_ends(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """At the end time the entity turns off and the run is cleared."""
    await _call(hass, "start", minutes=10)

    await _advance(hass, freezer, timedelta(minutes=9, seconds=59))
    assert _pump(hass) == STATE_ON

    await _advance(hass, freezer, timedelta(seconds=1))
    assert _pump(hass) == STATE_OFF
    assert _ends_at(hass) is None
    assert _attrs(hass)["mode"] == "off"


async def test_run_ends_while_unavailable(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """If the entity is unavailable at the end time, it is turned off on return."""
    await _call(hass, "start", minutes=10)
    hass.states.async_set(PUMP, STATE_UNAVAILABLE)
    await _advance(hass, freezer, timedelta(minutes=11))
    assert _ends_at(hass) is not None

    hass.states.async_set(PUMP, STATE_ON)
    await hass.async_block_till_done()

    assert _pump(hass) == STATE_OFF
    assert _ends_at(hass) is None


# --- Lifecycle -----------------------------------------------------------------


async def test_unload_cancels_timer(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_entry: MockConfigEntry
) -> None:
    """An unloaded entry no longer turns the entity off."""
    await _call(hass, "start", minutes=10)
    assert await hass.config_entries.async_unload(setup_entry.entry_id)

    await _advance(hass, freezer, timedelta(minutes=10))
    assert _pump(hass) == STATE_ON


async def test_remove_deletes_saved_run(
    hass: HomeAssistant, hass_storage: dict[str, Any], setup_entry: MockConfigEntry
) -> None:
    """Removing the entry deletes its storage file."""
    await _call(hass, "start", minutes=10)
    await hass.async_block_till_done()
    assert hass_storage[f"{DOMAIN}.{ENTRY_ID}"]["data"]["run"] is not None

    await hass.config_entries.async_remove(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.{ENTRY_ID}" not in hass_storage


async def test_diagnostics(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    """Diagnostics include the options and the current run."""
    await _call(hass, "start", minutes=10)
    diag = await async_get_config_entry_diagnostics(hass, setup_entry)

    assert diag["entry"]["data"] == {ATTR_ENTITY_ID: PUMP}
    assert diag["manager"]["mode"] == "timed"
    assert diag["manager"]["run"]["duration"] == 600
