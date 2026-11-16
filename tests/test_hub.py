"""Hub tests: automatic timer creation, removal and renames."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.switch_timer.const import DEFAULT_OPTIONS, DOMAIN

from .conftest import ENTRY_ID, PUMP, RUN_TIME, TIMER_ID

FAN = "input_boolean.test_fan"


@pytest.fixture
async def devices(hass: HomeAssistant) -> None:
    """A pump and a fan (input_booleans) to control."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {"pump": {"name": "Pump"}, "test_fan": {"name": "Test fan"}}},
    )
    await hass.async_block_till_done()


@pytest.fixture
async def hub(hass: HomeAssistant, devices: None) -> MockConfigEntry:
    """The hub, set up with no timers (as right after Add integration → Submit)."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Switch Timer", entry_id=ENTRY_ID, data={}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _ensure(ws, entity_id: str) -> dict[str, Any]:
    await ws.send_json_auto_id(
        {"type": "switch_timer/ensure_timer", "entity_id": entity_id}
    )
    return await ws.receive_json()


# --- Automatic creation (switch_timer/ensure_timer) -----------------------------------


async def test_ensure_creates_timer_with_defaults(
    hass: HomeAssistant, hub: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Picking an entity creates its timer: defaults, name, entities, device."""
    ws = await hass_ws_client(hass)

    msg = await _ensure(ws, PUMP)
    await hass.async_block_till_done()

    assert msg["success"], msg
    assert msg["result"]["created"] is True
    subentry = hub.subentries[msg["result"]["subentry_id"]]
    assert subentry.title == "Pump"
    assert subentry.unique_id == PUMP
    assert dict(subentry.data) == {ATTR_ENTITY_ID: PUMP, **DEFAULT_OPTIONS}
    assert DEFAULT_OPTIONS == {
        "run_time_min": 1,
        "run_time_max": 240,
        "run_time_step": 1,
        "default_run_time": 30,
        "extend_minutes": 15,
    }
    assert hass.states.get(RUN_TIME).state == "30"
    ends_at = hass.states.get("sensor.pump_ends_at")
    assert ends_at.attributes["controlled_entity_id"] == PUMP
    entity = er.async_get(hass).async_get(RUN_TIME)
    assert entity.config_subentry_id == subentry.subentry_id
    device = dr.async_get(hass).async_get(entity.device_id)
    assert device.name == "Pump"


async def test_ensure_is_idempotent_and_serialized(
    hass: HomeAssistant, hub: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Concurrent and repeated picks create one timer."""
    ws = await hass_ws_client(hass)
    first, second = await asyncio.gather(
        hub.runtime_data.async_ensure_timer(PUMP),
        hub.runtime_data.async_ensure_timer(PUMP),
    )
    msg = await _ensure(ws, PUMP)

    assert first[0] == second[0] == msg["result"]["subentry_id"]
    assert [first[1], second[1], msg["result"]["created"]].count(True) == 1
    assert len(hub.subentries) == 1


@pytest.mark.parametrize(
    ("entity_id", "code"),
    [("sensor.temperature", "not_supported"), ("switch.missing", "not_found")],
)
async def test_ensure_rejects(
    hass: HomeAssistant,
    hub: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    entity_id: str,
    code: str,
) -> None:
    """Only existing switches, lights, fans and toggles get a timer."""
    hass.states.async_set("sensor.temperature", "21")
    ws = await hass_ws_client(hass)

    msg = await _ensure(ws, entity_id)

    assert not msg["success"]
    assert msg["error"]["code"] == code
    assert hub.subentries == {}


async def test_ensure_needs_admin(
    hass: HomeAssistant,
    hub: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """Non-admins cannot create timers (the card asks them to contact an admin)."""
    ws = await hass_ws_client(hass, hass_read_only_access_token)

    msg = await _ensure(ws, PUMP)

    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"
    assert hub.subentries == {}


async def test_ensure_without_hub(
    hass: HomeAssistant, devices: None, hass_ws_client: WebSocketGenerator
) -> None:
    """With the hub not loaded, the command explains what to do."""
    entry = MockConfigEntry(domain=DOMAIN, title="Switch Timer", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert await hass.config_entries.async_unload(entry.entry_id)
    ws = await hass_ws_client(hass)

    msg = await _ensure(ws, PUMP)

    assert msg["error"]["code"] == "not_loaded"


async def test_new_timer_does_not_disturb_running_one(
    hass: HomeAssistant,
    hub: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Adding a timer is incremental: other timers keep their runs."""
    await hub.runtime_data.async_ensure_timer(PUMP)
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, "start", {ATTR_ENTITY_ID: PUMP, "minutes": 10}, blocking=True
    )
    pump_manager = next(iter(hub.runtime_data.managers.values()))

    await hub.runtime_data.async_ensure_timer(FAN)
    await hass.async_block_till_done()

    assert next(iter(hub.runtime_data.managers.values())) is pump_manager
    assert hass.states.get("sensor.test_fan_ends_at").attributes["mode"] == "off"
    assert hass.states.get("sensor.pump_ends_at").attributes["mode"] == "timed"
    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(PUMP).state == STATE_OFF


# --- Removal -----------------------------------------------------------------------------


async def test_removing_a_timer_cleans_up(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Deleting a timer (its device) removes entities, manager and saved run."""
    await hass.services.async_call(
        DOMAIN, "start", {ATTR_ENTITY_ID: PUMP, "minutes": 10}, blocking=True
    )
    await hass.async_block_till_done()
    assert f"{DOMAIN}.{TIMER_ID}" in hass_storage

    hass.config_entries.async_remove_subentry(setup_entry, TIMER_ID)
    await hass.async_block_till_done()

    assert setup_entry.runtime_data.managers == {}
    assert hass.states.get(RUN_TIME) is None
    assert er.async_get(hass).async_get(RUN_TIME) is None
    assert f"{DOMAIN}.{TIMER_ID}" not in hass_storage
    assert hass.states.get(PUMP).state == STATE_ON  # left as it was


@pytest.fixture
async def garden(hass: HomeAssistant, hub: MockConfigEntry) -> str:
    """A registry entity (switch.garden) with a timer."""
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        "switch", "test", "garden-1", suggested_object_id="garden"
    )
    hass.states.async_set(entry.entity_id, STATE_OFF, {"friendly_name": "Garden"})
    await hub.runtime_data.async_ensure_timer(entry.entity_id)
    await hass.async_block_till_done()
    return entry.entity_id


async def test_timer_removed_with_its_entity(
    hass: HomeAssistant, hub: MockConfigEntry, garden: str
) -> None:
    """Deleting the controlled entity from HA removes its timer."""
    assert hass.states.get("sensor.garden_ends_at") is not None

    er.async_get(hass).async_remove(garden)
    await hass.async_block_till_done()

    assert hub.subentries == {}
    assert hub.runtime_data.managers == {}
    assert hass.states.get("sensor.garden_ends_at") is None


async def test_timer_follows_renamed_entity(
    hass: HomeAssistant, hub: MockConfigEntry, garden: str
) -> None:
    """Renaming the controlled entity's id keeps the timer, now on the new id."""
    er.async_get(hass).async_update_entity(garden, new_entity_id="switch.lawn")
    hass.states.async_set("switch.lawn", STATE_OFF, {"friendly_name": "Garden"})
    await hass.async_block_till_done()

    (subentry,) = hub.subentries.values()
    assert subentry.unique_id == "switch.lawn"
    assert subentry.data[ATTR_ENTITY_ID] == "switch.lawn"
    manager = hub.runtime_data.managers[subentry.subentry_id]
    assert manager.entity_id == "switch.lawn"
    sensor = hass.states.get("sensor.garden_ends_at")
    assert sensor.attributes["controlled_entity_id"] == "switch.lawn"

    # The manager now tracks the new id: on elsewhere → manual.
    hass.states.async_set("switch.lawn", STATE_ON)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.garden_ends_at").attributes["mode"] == "manual"
