"""Coordinator for the Chores integration.

Manages the runtime state for a single chore, derives status/next_due,
schedules overdue-transition timers, and persists state to entry.options.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STATUS_DONE, STATUS_OVERDUE, STATUS_SNOOZED
from .models import ChoreConfig

_LOGGER = logging.getLogger(__name__)


@dataclass
class ChoreRuntime:
    """Runtime state for the single chore managed by this coordinator."""

    config: ChoreConfig
    last_completed: datetime | None
    status: str = STATUS_DONE
    next_due: datetime | None = None
    snooze_until: datetime | None = None
    _cancel_timer: Callable[[], None] | None = field(default=None, repr=False)
    _cancel_snooze_timer: Callable[[], None] | None = field(default=None, repr=False)


class ChoresCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that manages a single chore's state and timers."""

    def __init__(self, hass: HomeAssistant, entry: ChoresConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=None,
        )
        self._runtime: ChoreRuntime | None = None

    async def async_initialize(self) -> None:
        """Load chore from entry.options and schedule timers."""
        assert self.config_entry is not None
        opts = dict(self.config_entry.options)
        self._runtime = self._build_runtime(opts)
        self._schedule_timers()
        self.async_set_updated_data(self._snapshot())

    async def async_update_config(self, new_options: dict[str, Any]) -> None:
        """Reconcile runtime state from new options. Called by the update listener."""
        assert self._runtime is not None
        rt = self._runtime
        new_config = ChoreConfig.from_dict(new_options)
        new_last_completed = (
            _parse_aware_datetime(new_options.get("last_completed"))
            or rt.last_completed
        )
        new_snooze_until = _parse_aware_datetime(new_options.get("snooze_until"))

        if (
            rt.config == new_config
            and rt.last_completed == new_last_completed
            and rt.snooze_until == new_snooze_until
        ):
            return

        self._cancel_timers(rt)
        rt.config = new_config
        rt.last_completed = new_last_completed
        rt.snooze_until = new_snooze_until
        self._recompute(rt)
        self._schedule_timers()
        self.async_set_updated_data(self._snapshot())

    def _build_runtime(self, opts: dict[str, Any]) -> ChoreRuntime:
        """Construct a ChoreRuntime from an options dict."""
        config = ChoreConfig.from_dict(opts)
        last_completed = _parse_aware_datetime(opts.get("last_completed"))
        snooze_until = _parse_aware_datetime(opts.get("snooze_until"))
        rt = ChoreRuntime(
            config=config, last_completed=last_completed, snooze_until=snooze_until
        )
        self._recompute(rt)
        return rt

    def _recompute(self, rt: ChoreRuntime) -> None:
        """Recompute status and next_due."""
        if rt.last_completed is None:
            rt.next_due = None
            if rt.snooze_until is not None and dt_util.now() < rt.snooze_until:
                rt.status = STATUS_SNOOZED
                return
            rt.snooze_until = None
            rt.status = STATUS_OVERDUE
            return

        due_date = dt_util.as_local(rt.last_completed).date() + timedelta(
            days=rt.config.interval_days
        )
        rt.next_due = self._time_on_local_date(due_date, rt.config.notification_time)
        now = dt_util.now()

        if rt.snooze_until is not None:
            if now < rt.snooze_until:
                rt.status = STATUS_SNOOZED
                return
            rt.snooze_until = None

        rt.status = STATUS_OVERDUE if now >= rt.next_due else STATUS_DONE

    def _time_on_local_date(self, local_date: date, notification_time: str) -> datetime:
        """Return a tz-aware datetime at notification_time on local_date."""
        hour, minute = map(int, notification_time.split(":"))
        return dt_util.start_of_local_day(local_date).replace(hour=hour, minute=minute)

    def _schedule_timers(self) -> None:
        """Schedule overdue and/or snooze timer based on current runtime state."""
        assert self._runtime is not None
        rt = self._runtime
        if rt.status == STATUS_SNOOZED:
            self._schedule_snooze(rt)
        else:
            self._schedule(rt)

    def _schedule(self, rt: ChoreRuntime) -> None:
        """Schedule a timer to fire the overdue transition at next_due."""
        if rt._cancel_timer is not None:
            rt._cancel_timer()
            rt._cancel_timer = None

        if rt.next_due is None or rt.next_due <= dt_util.now():
            return

        @callback
        def _overdue_callback(_now: datetime) -> None:
            if self._runtime is None:
                return
            self._recompute(self._runtime)
            self.async_set_updated_data(self._snapshot())

        rt._cancel_timer = async_track_point_in_time(
            self.hass, _overdue_callback, rt.next_due
        )

    def _schedule_snooze(self, rt: ChoreRuntime) -> None:
        """Schedule a snooze-expiry timer at snooze_until."""
        if rt._cancel_snooze_timer is not None:
            rt._cancel_snooze_timer()
            rt._cancel_snooze_timer = None

        if rt.snooze_until is None:
            return

        if rt.snooze_until <= dt_util.now():
            return

        @callback
        def _snooze_expiry_callback(_now: datetime) -> None:
            if self._runtime is None:
                return
            self._runtime.snooze_until = None
            self._runtime._cancel_snooze_timer = None
            self._recompute(self._runtime)
            self._schedule(self._runtime)
            self.async_set_updated_data(self._snapshot())

        rt._cancel_snooze_timer = async_track_point_in_time(
            self.hass, _snooze_expiry_callback, rt.snooze_until
        )

    @callback
    def _cancel_timers(self, rt: ChoreRuntime) -> None:
        """Cancel all timers on a runtime."""
        if rt._cancel_timer is not None:
            rt._cancel_timer()
            rt._cancel_timer = None
        if rt._cancel_snooze_timer is not None:
            rt._cancel_snooze_timer()
            rt._cancel_snooze_timer = None

    def _persist(self, fields: dict[str, Any]) -> None:
        """Write updated runtime fields back to entry.options for persistence."""
        assert self.config_entry is not None
        new_opts = {**self.config_entry.options, **fields}
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_opts)

    async def async_complete(self, completed_at: datetime | None = None) -> None:
        """Mark the chore as completed, recompute state, and persist.

        completed_at defaults to now; raises HomeAssistantError if in the future.
        """
        assert self._runtime is not None
        now = dt_util.now()
        if completed_at is None:
            completed_at = now
        elif completed_at > now:
            raise HomeAssistantError(
                f"completed_at must not be in the future, got {completed_at}"
            )

        rt = self._runtime

        if rt.snooze_until is not None:
            if rt._cancel_snooze_timer is not None:
                rt._cancel_snooze_timer()
                rt._cancel_snooze_timer = None
            rt.snooze_until = None

        rt.last_completed = completed_at
        self._recompute(rt)
        self._schedule(rt)
        self._persist(
            {"last_completed": rt.last_completed.isoformat(), "snooze_until": None}
        )
        self.async_set_updated_data(self._snapshot())

    async def async_snooze_default(self) -> None:
        """Snooze by default_snooze_value + default_snooze_unit from now."""
        assert self._runtime is not None
        cfg = self._runtime.config
        delta_kwargs: dict[str, int] = {
            cfg.default_snooze_unit: cfg.default_snooze_value
        }
        snooze_until = dt_util.now() + timedelta(**delta_kwargs)
        await self.async_snooze(snooze_until)

    async def async_snooze(self, snooze_until: datetime) -> None:
        """Snooze the chore until snooze_until."""
        assert self._runtime is not None
        if snooze_until <= dt_util.now():
            raise HomeAssistantError(
                f"snooze_until must be a future datetime, got {snooze_until}"
            )

        rt = self._runtime
        rt.snooze_until = snooze_until

        if rt._cancel_timer is not None:
            rt._cancel_timer()
            rt._cancel_timer = None

        self._schedule_snooze(rt)
        rt.status = STATUS_SNOOZED
        self._persist({"snooze_until": snooze_until.isoformat()})
        self.async_set_updated_data(self._snapshot())

    async def async_unsnooze(self) -> None:
        """Cancel an active snooze, returning the chore to done or overdue."""
        assert self._runtime is not None
        rt = self._runtime
        if rt.snooze_until is None:
            return

        if rt._cancel_snooze_timer is not None:
            rt._cancel_snooze_timer()
            rt._cancel_snooze_timer = None
        rt.snooze_until = None
        self._recompute(rt)
        self._schedule(rt)
        self._persist({"snooze_until": None})
        self.async_set_updated_data(self._snapshot())

    @callback
    def async_shutdown_timers(self) -> None:
        """Cancel all scheduled timers. Called on entry unload."""
        if self._runtime is not None:
            self._cancel_timers(self._runtime)

    def _snapshot(self) -> dict[str, Any]:
        """Return a snapshot of current chore state (consumed by sensor platform)."""
        assert self._runtime is not None
        rt = self._runtime
        return {
            "name": rt.config.name,
            "last_completed": rt.last_completed,
            "status": rt.status,
            "next_due": rt.next_due,
            "snooze_until": rt.snooze_until,
            "interval_days": rt.config.interval_days,
            "default_snooze_value": rt.config.default_snooze_value,
            "default_snooze_unit": rt.config.default_snooze_unit,
            "notification_time": rt.config.notification_time,
        }


class _ChoreDeviceMixin:
    """Shared device_info property for chore sensor and button entities."""

    _entry_id: str
    coordinator: ChoresCoordinator

    @property
    def device_info(self) -> DeviceInfo:
        name = (self.coordinator.data or {}).get("name", "Chore")
        return DeviceInfo(identifiers={(DOMAIN, self._entry_id)}, name=name)


def _parse_aware_datetime(value: str | None) -> datetime | None:
    """Parse an ISO datetime string; return None if absent or malformed; raise on naive."""
    if not value:
        return None
    try:
        candidate = datetime.fromisoformat(value)
    except TypeError, ValueError:
        return None
    if candidate.tzinfo is None:
        raise ValueError(f"Expected a tz-aware datetime string, got naive: {value!r}")
    return candidate


type ChoresConfigEntry = ConfigEntry[ChoresCoordinator]
