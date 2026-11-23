"""Fixtures for Switch Timer tests."""

from __future__ import annotations

from collections.abc import Generator

from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.switch_timer.const import (
    DEFAULT_OPTIONS,
    DOMAIN,
    SUBENTRY_TYPE_TIMER,
)

PUMP = "input_boolean.pump"
RUN_TIME = "number.pump_run_time"
ENDS_AT = "sensor.pump_ends_at"
ENTRY_ID = "hub_entry"
TIMER_ID = "pump_timer"  # timer subentry id; also the storage key suffix


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Load custom_components in every test."""
    yield


@pytest.fixture
async def pump(hass: HomeAssistant) -> str:
    """Set up the controlled entity: a real input_boolean."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"pump": {"name": "Pump"}}}
    )
    await hass.async_block_till_done()
    return PUMP


def timer_subentry_data(
    entity_id: str = PUMP, subentry_id: str = TIMER_ID, title: str = "Pump"
):
    """Subentry data as created by switch_timer/ensure_timer."""
    return {
        "data": {CONF_ENTITY_ID: entity_id, **DEFAULT_OPTIONS},
        "subentry_id": subentry_id,
        "subentry_type": SUBENTRY_TYPE_TIMER,
        "title": title,
        "unique_id": entity_id,
    }


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return the Switch Timer hub with one timer, for the pump."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Switch Timer",
        entry_id=ENTRY_ID,
        data={},
        subentries_data=[timer_subentry_data()],
    )


@pytest.fixture
async def setup_entry(
    hass: HomeAssistant, pump: str, config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the pump and the hub with the pump's timer."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
