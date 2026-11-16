"""Config flow for the Switch Timer integration.

The only thing a user sets up is the hub (no fields, just Submit). Timers are config
subentries created by the card; no subentry flow is offered, so there is no manual
"Add" button. The hub's options flow edits one timer's settings.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)
import voluptuous as vol

from .const import (
    CONF_DEFAULT_RUN_TIME,
    CONF_EXTEND_MINUTES,
    CONF_RUN_TIME_MAX,
    CONF_RUN_TIME_MIN,
    CONF_RUN_TIME_STEP,
    DEFAULT_OPTIONS,
    DOMAIN,
    SUBENTRY_TYPE_TIMER,
)

CONF_TIMER = "timer"
SETTINGS = (
    CONF_RUN_TIME_MIN,
    CONF_RUN_TIME_MAX,
    CONF_RUN_TIME_STEP,
    CONF_DEFAULT_RUN_TIME,
    CONF_EXTEND_MINUTES,
)


def _minutes(max_value: float = 1440) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=1,
            max=max_value,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="min",
        )
    )


TIMER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_RUN_TIME_MIN): _minutes(),
        vol.Required(CONF_RUN_TIME_MAX): _minutes(),
        vol.Required(CONF_RUN_TIME_STEP): _minutes(max_value=60),
        vol.Required(CONF_DEFAULT_RUN_TIME): _minutes(),
        vol.Required(CONF_EXTEND_MINUTES): _minutes(max_value=240),
    }
)


class SwitchTimerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the Switch Timer hub (single entry, see manifest)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm; nothing to fill in."""
        if user_input is not None:
            return self.async_create_entry(title="Switch Timer", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SwitchTimerOptionsFlow:
        """Return the options flow."""
        return SwitchTimerOptionsFlow()


class SwitchTimerOptionsFlow(OptionsFlow):
    """Edit the settings of one timer."""

    def __init__(self) -> None:
        """Initialize the flow."""
        self._timer_id: str | None = None

    def _timers(self) -> dict[str, Any]:
        return {
            subentry_id: subentry
            for subentry_id, subentry in self.config_entry.subentries.items()
            if subentry.subentry_type == SUBENTRY_TYPE_TIMER
        }

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the timer to edit."""
        timers = self._timers()
        if not timers:
            return self.async_abort(reason="no_timers")
        if user_input is not None:
            self._timer_id = user_input[CONF_TIMER]
            return await self.async_step_timer()
        options = sorted(
            (
                SelectOptionDict(value=subentry_id, label=subentry.title)
                for subentry_id, subentry in timers.items()
            ),
            key=lambda option: option["label"].lower(),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TIMER): SelectSelector(
                        SelectSelectorConfig(options=options)
                    )
                }
            ),
        )

    async def async_step_timer(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit run-time range, default run time and extend step."""
        subentry = self._timers().get(self._timer_id or "")
        if subentry is None:
            return self.async_abort(reason="no_timers")
        errors: dict[str, str] = {}
        if user_input is not None:
            values = {key: int(user_input[key]) for key in SETTINGS}
            if values[CONF_RUN_TIME_MIN] >= values[CONF_RUN_TIME_MAX]:
                errors[CONF_RUN_TIME_MAX] = "max_not_above_min"
            elif not (
                values[CONF_RUN_TIME_MIN]
                <= values[CONF_DEFAULT_RUN_TIME]
                <= values[CONF_RUN_TIME_MAX]
            ):
                errors[CONF_DEFAULT_RUN_TIME] = "default_out_of_range"
            else:
                self.hass.config_entries.async_update_subentry(
                    self.config_entry, subentry, data={**subentry.data, **values}
                )
                return self.async_create_entry(data=dict(self.config_entry.options))
        current = {
            **DEFAULT_OPTIONS,
            **{k: subentry.data[k] for k in SETTINGS if k in subentry.data},
        }
        return self.async_show_form(
            step_id="timer",
            data_schema=self.add_suggested_values_to_schema(
                TIMER_SCHEMA, user_input or current
            ),
            description_placeholders={"name": subentry.title},
            errors=errors,
        )
