"""Timed-run logic for one controlled entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEFAULT_RUN_TIME,
    CONF_EXTEND_MINUTES,
    DEFAULT_EXTEND_MINUTES,
    DEFAULT_RUN_TIME,
    DOMAIN,
    MODE_MANUAL,
    MODE_OFF,
    MODE_TIMED,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

_NOT_AVAILABLE = (None, STATE_UNAVAILABLE, STATE_UNKNOWN)


@dataclass(frozen=True, slots=True)
class TimedRun:
    """A run started from the card or the start action."""

    started_at: datetime
    ends_at: datetime
    duration: int  # seconds, grows when the run is extended

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""
        return {
            "started_at": self.started_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimedRun | None:
        """Parse a stored run; return None if it is malformed."""
        started_at = dt_util.parse_datetime(str(data.get("started_at")))
        ends_at = dt_util.parse_datetime(str(data.get("ends_at")))
        duration = data.get("duration")
        if started_at is None or ends_at is None or not isinstance(duration, int):
            return None
        return cls(started_at, ends_at, duration)


def storage_key(entry_id: str) -> str:
    """Return the storage key for a config entry."""
    return f"{DOMAIN}.{entry_id}"


class SwitchTimerManager:
    """Own the timed run of one controlled entity."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        self.entity_id: str = entry.data[ATTR_ENTITY_ID]
        self.run: TimedRun | None = None
        self.run_minutes: float = entry.options.get(
            CONF_DEFAULT_RUN_TIME, DEFAULT_RUN_TIME
        )
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, storage_key(entry.entry_id)
        )
        self._listeners: list[CALLBACK_TYPE] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._unsub_timer: CALLBACK_TYPE | None = None
        self._restoring = False

    @property
    def mode(self) -> str:
        """Return off, timed or manual."""
        state = self.hass.states.get(self.entity_id)
        if state is None or state.state != STATE_ON:
            return MODE_OFF
        return MODE_TIMED if self.run else MODE_MANUAL

    @property
    def extend_minutes(self) -> int:
        """Return the default number of minutes added by extend."""
        return self.entry.options.get(CONF_EXTEND_MINUTES, DEFAULT_EXTEND_MINUTES)

    async def async_setup(self) -> None:
        """Restore a saved run and start listening to the controlled entity."""
        if (data := await self._store.async_load()) and data.get("run"):
            self.run = TimedRun.from_dict(data["run"])
        self._unsubs.append(
            async_track_state_change_event(
                self.hass, self.entity_id, self._async_state_changed
            )
        )
        if self.run is not None:
            _LOGGER.debug(
                "%s: restored run ending %s", self.entity_id, self.run.ends_at
            )
            self._restoring = True
            self._async_schedule()
            self._unsubs.append(async_at_started(self.hass, self._async_started))

    @callback
    def async_unload(self) -> None:
        """Stop timers and listeners; the saved run is kept for the next setup."""
        self._async_unschedule()
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def async_add_listener(self, update: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Call update whenever the run or the mode changes."""
        self._listeners.append(update)
        return lambda: self._listeners.remove(update)

    @callback
    def async_set_run_minutes(self, minutes: float) -> None:
        """Set the run time used when start is called without minutes."""
        self.run_minutes = minutes
        self._async_notify()

    async def async_start(self, minutes: float | None = None) -> None:
        """Turn the entity on and start a timed run."""
        minutes = minutes or self.run_minutes
        now = dt_util.utcnow().replace(microsecond=0)
        self._async_set_run(
            TimedRun(now, now + timedelta(minutes=minutes), round(minutes * 60))
        )
        _LOGGER.debug("%s: timed run of %s min started", self.entity_id, minutes)
        try:
            await self._async_call(SERVICE_TURN_ON)
        except HomeAssistantError:
            self._async_set_run(None)
            raise

    async def async_extend(self, minutes: float | None = None) -> None:
        """Add minutes to the active timed run; do nothing without one."""
        if (run := self.run) is None:
            _LOGGER.debug("%s: extend ignored, no timed run", self.entity_id)
            return
        minutes = minutes or self.extend_minutes
        self._async_set_run(
            TimedRun(
                run.started_at,
                run.ends_at + timedelta(minutes=minutes),
                run.duration + round(minutes * 60),
            )
        )
        _LOGGER.debug("%s: timed run extended by %s min", self.entity_id, minutes)

    async def async_stop(self) -> None:
        """Clear the run and turn the entity off."""
        self._async_set_run(None)
        await self._async_call(SERVICE_TURN_OFF)

    async def _async_call(self, service: str) -> None:
        await self.hass.services.async_call(
            "homeassistant",
            service,
            {ATTR_ENTITY_ID: self.entity_id},
            blocking=True,
        )

    @callback
    def _async_set_run(self, run: TimedRun | None) -> None:
        """Replace the run, persist it and (re)schedule its end."""
        self.run = run
        self._restoring = False
        self.hass.async_create_task(
            self._store.async_save(self._data_to_save()),
            f"{DOMAIN} save {self.entity_id}",
        )
        self._async_schedule()
        self._async_notify()

    def _data_to_save(self) -> dict[str, Any]:
        return {"run": self.run.as_dict() if self.run else None}

    @callback
    def _async_schedule(self) -> None:
        self._async_unschedule()
        if self.run is not None:
            self._unsub_timer = async_track_point_in_utc_time(
                self.hass, self._async_time_up, self.run.ends_at
            )

    @callback
    def _async_unschedule(self) -> None:
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _async_time_up(self, _now: datetime) -> None:
        self._unsub_timer = None
        if not self._restoring:  # a restored run is settled once HA has started
            self._async_finish_if_due()

    @callback
    def _async_started(self, _hass: HomeAssistant) -> None:
        self._async_check_restored_run()

    @callback
    def _async_check_restored_run(self) -> None:
        """Settle a run restored from storage once the entity is available."""
        state = self.hass.states.get(self.entity_id)
        if not self._restoring or self.run is None or _unavailable(state):
            return
        if state is not None and state.state == STATE_OFF:
            # Turned off while Home Assistant was down.
            _LOGGER.debug("%s: restored run dropped, entity is off", self.entity_id)
            self._async_set_run(None)
            return
        self._restoring = False
        self._async_finish_if_due()

    @callback
    def _async_finish_if_due(self) -> None:
        """End the run if its time is up; wait if the entity is unavailable."""
        if self.run is None or self.run.ends_at > dt_util.utcnow():
            return
        state = self.hass.states.get(self.entity_id)
        if _unavailable(state):
            _LOGGER.debug("%s: run over, waiting for entity", self.entity_id)
            return
        _LOGGER.debug("%s: timed run finished", self.entity_id)
        self._async_set_run(None)
        if state is not None and state.state == STATE_ON:
            self.entry.async_create_background_task(
                self.hass, self._async_turn_off(), f"{DOMAIN} turn off {self.entity_id}"
            )

    async def _async_turn_off(self) -> None:
        try:
            await self._async_call(SERVICE_TURN_OFF)
        except HomeAssistantError as err:
            _LOGGER.error("Could not turn off %s: %s", self.entity_id, err)

    @callback
    def _async_state_changed(self, event: Event[EventStateChangedData]) -> None:
        old, new = event.data["old_state"], event.data["new_state"]
        if _unavailable(new):
            self._async_notify()
            return
        if _unavailable(old):
            # Became available: settle a restored or overdue run.
            if self._restoring:
                self._async_check_restored_run()
            else:
                self._async_finish_if_due()
        elif (
            self.run is not None
            and old is not None
            and new is not None
            and old.state == STATE_ON
            and new.state == STATE_OFF
        ):
            _LOGGER.debug("%s: turned off, timed run cancelled", self.entity_id)
            self._async_set_run(None)
            return
        self._async_notify()

    @callback
    def _async_notify(self) -> None:
        for update in list(self._listeners):
            update()

    def as_diagnostics(self) -> dict[str, Any]:
        """Return the current state for diagnostics."""
        state = self.hass.states.get(self.entity_id)
        return {
            "mode": self.mode,
            "run": self.run.as_dict() if self.run else None,
            "run_minutes": self.run_minutes,
            "restoring": self._restoring,
            "entity_state": state.as_dict() if state else None,
        }


def _unavailable(state: State | None) -> bool:
    return state is None or state.state in _NOT_AVAILABLE
