"""Tests for the hub config flow (no fields) and the timer settings (options flow)."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations
from homeassistant.loader import async_get_integration
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.switch_timer.const import (
    CONF_DEFAULT_RUN_TIME,
    CONF_EXTEND_MINUTES,
    CONF_RUN_TIME_MAX,
    CONF_RUN_TIME_MIN,
    CONF_RUN_TIME_STEP,
    DEFAULT_OPTIONS,
    DOMAIN,
)

from .conftest import ENDS_AT, PUMP, RUN_TIME, TIMER_ID

NEW_SETTINGS = {
    CONF_RUN_TIME_MIN: 5,
    CONF_RUN_TIME_MAX: 90,
    CONF_RUN_TIME_STEP: 5,
    CONF_DEFAULT_RUN_TIME: 20,
    CONF_EXTEND_MINUTES: 10,
}


async def test_hub_setup_has_no_fields(hass: HomeAssistant) -> None:
    """Add integration → Switch Timer → Submit creates the hub, nothing else."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["data_schema"] is None or not result["data_schema"].schema

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Switch Timer"
    assert result["data"] == {}
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.subentries == {}
    assert entry.supported_subentry_types == {}  # no manual "Add" button


async def test_hub_is_single_instance(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """A second hub cannot be added."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_edit_one_timer(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """Configure → pick a timer → edit; applied without reloading the hub."""
    manager = setup_entry.runtime_data.managers[TIMER_ID]
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"timer": TIMER_ID}
    )
    assert result["step_id"] == "timer"
    assert result["description_placeholders"] == {"name": "Pump"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], NEW_SETTINGS
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert dict(setup_entry.subentries[TIMER_ID].data) == {
        "entity_id": PUMP,
        **NEW_SETTINGS,
    }
    assert setup_entry.runtime_data.managers[TIMER_ID] is manager  # not reloaded
    assert manager.extend_minutes == 10
    attrs = hass.states.get(RUN_TIME).attributes
    assert (attrs["min"], attrs["max"], attrs["step"]) == (5, 90, 5)
    assert hass.states.get(RUN_TIME).state == "30"  # still in range, kept


async def test_options_clamp_run_time_into_new_range(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """A run time outside the edited range is clamped."""
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"timer": TIMER_ID}
    )
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {**NEW_SETTINGS, CONF_RUN_TIME_MAX: 25, CONF_DEFAULT_RUN_TIME: 20},
    )
    await hass.async_block_till_done()

    assert hass.states.get(RUN_TIME).state == "25"


async def test_options_validation(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """Max must exceed min, and the default must lie in between."""
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"timer": TIMER_ID}
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {**DEFAULT_OPTIONS, CONF_RUN_TIME_MIN: 60, CONF_RUN_TIME_MAX: 60},
    )
    assert result["errors"] == {CONF_RUN_TIME_MAX: "max_not_above_min"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**DEFAULT_OPTIONS, CONF_DEFAULT_RUN_TIME: 300}
    )
    assert result["errors"] == {CONF_DEFAULT_RUN_TIME: "default_out_of_range"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], dict(DEFAULT_OPTIONS)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_options_without_timers(hass: HomeAssistant) -> None:
    """Configure on a hub without timers explains how to get one."""
    entry = MockConfigEntry(domain=DOMAIN, title="Switch Timer", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_timers"
    assert hass.states.get(ENDS_AT) is None


async def test_integration_lists_as_a_hub(hass: HomeAssistant) -> None:
    """A single-entry hub, not a helper: listed under Integrations, no "!" in Helpers.

    As a helper, the entity-less hub entry showed under Settings → Helpers with a
    red "!" icon.
    """
    integration = await async_get_integration(hass, DOMAIN)

    assert integration.integration_type == "hub"
    assert integration.single_config_entry is True


async def test_setup_success_message_says_to_reload(hass: HomeAssistant) -> None:
    """The open page only loads the card after a reload; the success dialog says so."""
    translations = await async_get_translations(hass, "en", "config", [DOMAIN])

    message = translations[f"component.{DOMAIN}.config.create_entry.default"]
    assert "Reload this page" in message
