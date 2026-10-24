"""Config flow for the Switch Timer integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
import voluptuous as vol

from .const import (
    CONF_DEFAULT_RUN_TIME,
    CONF_EXTEND_MINUTES,
    CONF_RUN_TIME_MAX,
    CONF_RUN_TIME_MIN,
    CONF_RUN_TIME_STEP,
    DEFAULT_OPTIONS,
    DEFAULT_RUN_TIME,
    DEFAULT_RUN_TIME_MAX,
    DEFAULT_RUN_TIME_MIN,
    DOMAIN,
    SUPPORTED_DOMAINS,
)


def _minutes(min_value: float = 1, max_value: float = 1440) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="min",
        )
    )


USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): EntitySelector(
            EntitySelectorConfig(domain=SUPPORTED_DOMAINS)
        ),
        vol.Optional(CONF_NAME): TextSelector(),
        vol.Required(CONF_DEFAULT_RUN_TIME, default=DEFAULT_RUN_TIME): _minutes(
            DEFAULT_RUN_TIME_MIN, DEFAULT_RUN_TIME_MAX
        ),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_RUN_TIME_MIN): _minutes(),
        vol.Required(CONF_RUN_TIME_MAX): _minutes(),
        vol.Required(CONF_RUN_TIME_STEP): _minutes(max_value=60),
        vol.Required(CONF_DEFAULT_RUN_TIME): _minutes(),
        vol.Required(CONF_EXTEND_MINUTES): _minutes(max_value=240),
    }
)


class SwitchTimerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a Switch Timer for one entity."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the entity, a name and the default run time."""
        if user_input is not None:
            entity_id: str = user_input[CONF_ENTITY_ID]
            await self.async_set_unique_id(entity_id)
            self._abort_if_unique_id_configured()
            name = user_input.get(CONF_NAME, "").strip()
            if not name and (state := self.hass.states.get(entity_id)):
                name = state.attributes.get(ATTR_FRIENDLY_NAME, "")
            return self.async_create_entry(
                title=name or entity_id,
                data={CONF_ENTITY_ID: entity_id},
                options={
                    **DEFAULT_OPTIONS,
                    CONF_DEFAULT_RUN_TIME: int(user_input[CONF_DEFAULT_RUN_TIME]),
                },
            )
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SwitchTimerOptionsFlow:
        """Return the options flow."""
        return SwitchTimerOptionsFlow()


class SwitchTimerOptionsFlow(OptionsFlowWithReload):
    """Edit the run-time range, default run time and extend step."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            options = {key: int(value) for key, value in user_input.items()}
            if options[CONF_RUN_TIME_MIN] >= options[CONF_RUN_TIME_MAX]:
                errors[CONF_RUN_TIME_MAX] = "max_not_above_min"
            elif not (
                options[CONF_RUN_TIME_MIN]
                <= options[CONF_DEFAULT_RUN_TIME]
                <= options[CONF_RUN_TIME_MAX]
            ):
                errors[CONF_DEFAULT_RUN_TIME] = "default_out_of_range"
            else:
                return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                user_input or {**DEFAULT_OPTIONS, **self.config_entry.options},
            ),
            errors=errors,
        )
