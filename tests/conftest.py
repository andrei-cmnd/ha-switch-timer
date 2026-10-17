"""Fixtures for Switch Timer tests."""

from __future__ import annotations

from collections.abc import Generator

from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.switch_timer.const import DEFAULT_OPTIONS, DOMAIN

PUMP = "input_boolean.pump"
RUN_TIME = "number.pump_run_time"
ENDS_AT = "sensor.pump_ends_at"
ENTRY_ID = "pump_entry"


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


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return the Switch Timer entry for the pump."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Pump",
        entry_id=ENTRY_ID,
        unique_id=PUMP,
        data={CONF_ENTITY_ID: PUMP},
        options=dict(DEFAULT_OPTIONS),
    )


@pytest.fixture
async def setup_entry(
    hass: HomeAssistant, pump: str, config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the pump and its Switch Timer entry."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
