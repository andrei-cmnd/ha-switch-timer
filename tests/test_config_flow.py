"""Tests for the Switch Timer config and options flows."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.switch_timer.const import (
    CONF_DEFAULT_RUN_TIME,
    CONF_EXTEND_MINUTES,
    CONF_RUN_TIME_MAX,
    CONF_RUN_TIME_MIN,
    CONF_RUN_TIME_STEP,
    DEFAULT_OPTIONS,
    DOMAIN,
)

from .conftest import PUMP, RUN_TIME


async def test_user_flow_uses_friendly_name(hass: HomeAssistant, pump: str) -> None:
    """An empty name falls back to the entity's friendly name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITY_ID: PUMP, CONF_DEFAULT_RUN_TIME: 45}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Pump"
    assert result["data"] == {CONF_ENTITY_ID: PUMP}
    assert result["options"] == {**DEFAULT_OPTIONS, CONF_DEFAULT_RUN_TIME: 45}
    assert result["result"].unique_id == PUMP
    assert hass.states.get(RUN_TIME).state == "45"


async def test_user_flow_custom_name(hass: HomeAssistant, pump: str) -> None:
    """A given name becomes the entry title and entity id prefix."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ENTITY_ID: PUMP, CONF_NAME: "Garden", CONF_DEFAULT_RUN_TIME: 30},
    )
    await hass.async_block_till_done()

    assert result["title"] == "Garden"
    assert hass.states.get("number.garden_run_time") is not None
    assert hass.states.get("sensor.garden_ends_at") is not None


async def test_user_flow_already_configured(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """The same entity cannot be added twice."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITY_ID: PUMP, CONF_DEFAULT_RUN_TIME: 30}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    """Options are saved and the entry reloads with the new range."""
    new_options = {
        CONF_RUN_TIME_MIN: 5,
        CONF_RUN_TIME_MAX: 90,
        CONF_RUN_TIME_STEP: 5,
        CONF_DEFAULT_RUN_TIME: 20,
        CONF_EXTEND_MINUTES: 10,
    }
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], new_options
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_entry.options == new_options
    attrs = hass.states.get(RUN_TIME).attributes
    assert (attrs["min"], attrs["max"], attrs["step"]) == (5, 90, 5)
    assert setup_entry.runtime_data.extend_minutes == 10


async def test_options_flow_validation(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """Max must exceed min, and the default must lie in between."""
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {**DEFAULT_OPTIONS, CONF_RUN_TIME_MIN: 60, CONF_RUN_TIME_MAX: 60},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_RUN_TIME_MAX: "max_not_above_min"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**DEFAULT_OPTIONS, CONF_DEFAULT_RUN_TIME: 300}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_DEFAULT_RUN_TIME: "default_out_of_range"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], dict(DEFAULT_OPTIONS)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


# --- One-click creation from the card (same HTTP calls as frontend/src/setup.ts) ---

FLOW_URL = "/api/config/config_entries/flow"


async def test_card_quick_setup_over_http(
    hass: HomeAssistant, pump: str, hass_client: ClientSessionGenerator
) -> None:
    """Start the flow and submit only entity + run time 30: defaults fill the rest."""
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()

    resp = await client.post(
        FLOW_URL, json={"handler": DOMAIN, "show_advanced_options": False}
    )
    assert resp.status == 200
    flow = await resp.json()
    assert (flow["type"], flow["step_id"]) == ("form", "user")

    resp = await client.post(
        f"{FLOW_URL}/{flow['flow_id']}",
        json={CONF_ENTITY_ID: PUMP, CONF_DEFAULT_RUN_TIME: 30},
    )
    assert resp.status == 200
    result = await resp.json()
    assert result["type"] == "create_entry"
    assert result["title"] == "Pump"
    await hass.async_block_till_done()

    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.unique_id == PUMP
    assert entry.options == {
        CONF_RUN_TIME_MIN: 1,
        CONF_RUN_TIME_MAX: 240,
        CONF_RUN_TIME_STEP: 1,
        CONF_DEFAULT_RUN_TIME: 30,
        CONF_EXTEND_MINUTES: 15,
    }
    assert hass.states.get(RUN_TIME).state == "30"


async def test_card_quick_setup_already_configured_over_http(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
) -> None:
    """A second Switch Timer for the same entity aborts with already_configured."""
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()

    flow = await (await client.post(FLOW_URL, json={"handler": DOMAIN})).json()
    resp = await client.post(
        f"{FLOW_URL}/{flow['flow_id']}",
        json={CONF_ENTITY_ID: PUMP, CONF_DEFAULT_RUN_TIME: 30},
    )
    result = await resp.json()

    assert (result["type"], result["reason"]) == ("abort", "already_configured")
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_card_quick_setup_needs_admin(
    hass: HomeAssistant,
    pump: str,
    hass_client: ClientSessionGenerator,
    hass_read_only_access_token: str,
) -> None:
    """Non-admins cannot start the flow (the card shows "Ask an admin…" instead)."""
    assert await async_setup_component(hass, "config", {})
    client = await hass_client(hass_read_only_access_token)

    resp = await client.post(FLOW_URL, json={"handler": DOMAIN})

    assert resp.status == 401
    assert hass.config_entries.async_entries(DOMAIN) == []
