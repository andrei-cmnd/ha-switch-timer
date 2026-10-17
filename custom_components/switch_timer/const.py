"""Constants for the Switch Timer integration."""

from typing import Final

DOMAIN: Final = "switch_timer"

SUPPORTED_DOMAINS: Final = ["switch", "light", "fan", "input_boolean"]

# Options
CONF_DEFAULT_RUN_TIME: Final = "default_run_time"
CONF_EXTEND_MINUTES: Final = "extend_minutes"
CONF_RUN_TIME_MAX: Final = "run_time_max"
CONF_RUN_TIME_MIN: Final = "run_time_min"
CONF_RUN_TIME_STEP: Final = "run_time_step"

DEFAULT_RUN_TIME: Final = 30
DEFAULT_EXTEND_MINUTES: Final = 15
DEFAULT_RUN_TIME_MAX: Final = 240
DEFAULT_RUN_TIME_MIN: Final = 1
DEFAULT_RUN_TIME_STEP: Final = 1

DEFAULT_OPTIONS: Final = {
    CONF_RUN_TIME_MIN: DEFAULT_RUN_TIME_MIN,
    CONF_RUN_TIME_MAX: DEFAULT_RUN_TIME_MAX,
    CONF_RUN_TIME_STEP: DEFAULT_RUN_TIME_STEP,
    CONF_DEFAULT_RUN_TIME: DEFAULT_RUN_TIME,
    CONF_EXTEND_MINUTES: DEFAULT_EXTEND_MINUTES,
}

# Actions
ATTR_MINUTES: Final = "minutes"
SERVICE_START: Final = "start"
SERVICE_EXTEND: Final = "extend"
SERVICE_STOP: Final = "stop"

# Sensor attributes
ATTR_DURATION: Final = "duration"
ATTR_MODE: Final = "mode"
ATTR_STARTED_AT: Final = "started_at"

MODE_OFF: Final = "off"
MODE_TIMED: Final = "timed"
MODE_MANUAL: Final = "manual"

STORAGE_VERSION: Final = 1
