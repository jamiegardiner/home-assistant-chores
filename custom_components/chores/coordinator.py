"""Coordinator for the Chores integration.

Manages the runtime state for a single chore, derives status/next_due,
schedules overdue-transition timers, and persists state to entry.options.
"""

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HassJob, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    REPAIR_ISSUE_CORRUPT_CONFIG,
    REPAIR_ISSUE_CORRUPT_LAST_COMPLETED,
    REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL,
    STATUS_DONE,
    STATUS_OVERDUE,
    STATUS_SNOOZED,
)
from .models import ChoreConfig

_LOGGER = logging.getLogger(__name__)


class ChoreRuntime:
    """Runtime state for the single chore managed by this coordinator."""

    def __init__(
        self,
        config: ChoreConfig,
        last_completed: datetime | None,
        snooze_until: datetime | None = None,
    ) -> None:
        """Initialize runtime state for a chore."""
        self.config = config
        self.last_completed = last_completed
        self.status: str = STATUS_DONE
        self.next_due: datetime | None = None
        self.snooze_until = snooze_until
        self._unsubscribe_overdue_timer: Callable[[], None] | None = None
        self._unsubscribe_snooze_timer: Callable[[], None] | None = None

    def cancel_overdue_timer(self) -> None:
        """Cancel the overdue transition timer if one is scheduled."""
        if self._unsubscribe_overdue_timer is not None:
            self._unsubscribe_overdue_timer()
            self._unsubscribe_overdue_timer = None

    def cancel_snooze_timer(self) -> None:
        """Cancel the snooze-expiry timer if one is scheduled."""
        if self._unsubscribe_snooze_timer is not None:
            self._unsubscribe_snooze_timer()
            self._unsubscribe_snooze_timer = None

    def recompute(self) -> None:
        """Recompute status and next_due from current field values."""
        if self.last_completed is None:
            self.next_due = None
            if self.snooze_until is not None and dt_util.now() < self.snooze_until:
                self.status = STATUS_SNOOZED
                return
            self.snooze_until = None
            self.status = STATUS_OVERDUE
            return

        due_date = dt_util.as_local(self.last_completed).date() + timedelta(
            days=self.config.interval_in_days
        )
        self.next_due = _time_on_local_date(due_date, self.config.notification_time)
        now = dt_util.now()

        if self.snooze_until is not None:
            if now < self.snooze_until:
                self.status = STATUS_SNOOZED
                return
            self.snooze_until = None

        self.status = STATUS_OVERDUE if now >= self.next_due else STATUS_DONE


type ChoresConfigEntry = ConfigEntry[ChoresCoordinator]


class ChoresCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that manages a single chore's state and timers."""

    config_entry: ChoresConfigEntry

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

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    async def async_initialize(self) -> None:
        """Load chore from entry.options and schedule timers."""
        opts = dict(self.config_entry.options)
        entry_id = self.config_entry.entry_id

        try:
            config = ChoreConfig.from_dict(opts)
        except ValueError as exc:
            _LOGGER.error(
                "Chore entry %s has invalid configuration and cannot load: %s",
                entry_id,
                exc,
            )
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"{REPAIR_ISSUE_CORRUPT_CONFIG}_{entry_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key=REPAIR_ISSUE_CORRUPT_CONFIG,
                translation_placeholders={
                    "name": str(opts.get("name", entry_id)),
                    "error": str(exc),
                },
            )
            raise ConfigEntryError(str(exc)) from exc

        ir.async_delete_issue(
            self.hass, DOMAIN, f"{REPAIR_ISSUE_CORRUPT_CONFIG}_{entry_id}"
        )

        last_completed = self._resolve_datetime_field(
            opts,
            "last_completed",
            REPAIR_ISSUE_CORRUPT_LAST_COMPLETED,
            entry_id,
            config.name,
        )
        snooze_until = self._resolve_datetime_field(
            opts,
            "snooze_until",
            REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL,
            entry_id,
            config.name,
        )

        rt = ChoreRuntime(
            config=config, last_completed=last_completed, snooze_until=snooze_until
        )
        rt.recompute()
        self._runtime = rt

        self._commit()

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
        rt.recompute()
        self._commit()

    @callback
    def async_shutdown_timers(self) -> None:
        """Cancel all scheduled timers. Called on entry unload."""
        if self._runtime is not None:
            self._cancel_timers(self._runtime)

    # ------------------------------------------------------------------
    # Public commands
    # ------------------------------------------------------------------

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
                translation_domain=DOMAIN,
                translation_key="completed_at_in_future",
            )

        rt = self._runtime

        if rt.snooze_until is not None:
            rt.cancel_snooze_timer()
            rt.snooze_until = None

        rt.last_completed = completed_at
        rt.recompute()
        self._commit()

    async def async_snooze_default(self) -> None:
        """Snooze by default_snooze_value + default_snooze_unit from now."""
        assert self._runtime is not None
        cfg = self._runtime.config
        await self.async_snooze(
            _snooze_target(cfg.default_snooze_value, cfg.default_snooze_unit)
        )

    async def async_snooze(self, snooze_until: datetime) -> None:
        """Snooze the chore until snooze_until."""
        assert self._runtime is not None
        if snooze_until <= dt_util.now():
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="snooze_until_in_past",
            )

        rt = self._runtime
        rt.snooze_until = snooze_until
        rt.status = STATUS_SNOOZED

        rt.cancel_overdue_timer()

        self._commit()

    async def async_unsnooze(self) -> None:
        """Cancel an active snooze, returning the chore to done or overdue."""
        assert self._runtime is not None
        rt = self._runtime
        if rt.snooze_until is None:
            return

        rt.cancel_snooze_timer()
        rt.snooze_until = None
        rt.recompute()
        self._commit()

    def set_option(self, key: str, value: Any) -> None:
        """Persist a single option field. Public interface for entity setters."""
        self._persist({key: value})

    # ------------------------------------------------------------------
    # Private state
    # ------------------------------------------------------------------

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
            "interval_value": rt.config.interval_value,
            "interval_unit": rt.config.interval_unit,
            "default_snooze_value": rt.config.default_snooze_value,
            "default_snooze_unit": rt.config.default_snooze_unit,
            "notification_time": rt.config.notification_time,
        }

    # ------------------------------------------------------------------
    # Private timers
    # ------------------------------------------------------------------

    @callback
    def _schedule_timers(self) -> None:
        """Schedule overdue and/or snooze timer based on current runtime state."""
        assert self._runtime is not None
        rt = self._runtime
        if rt.status == STATUS_SNOOZED:
            self._schedule_snooze(rt)
        else:
            self._schedule(rt)

    @callback
    def _schedule(self, rt: ChoreRuntime) -> None:
        """Schedule a timer to fire the overdue transition at next_due."""
        rt.cancel_overdue_timer()

        if rt.next_due is None or rt.next_due <= dt_util.now():
            return

        @callback
        def _overdue_callback(_now: datetime) -> None:
            if self._runtime is None:
                return
            self._runtime._unsubscribe_overdue_timer = None
            self._runtime.recompute()
            self.async_set_updated_data(self._snapshot())

        rt._unsubscribe_overdue_timer = async_track_point_in_time(
            self.hass, HassJob(_overdue_callback), rt.next_due
        )

    @callback
    def _schedule_snooze(self, rt: ChoreRuntime) -> None:
        """Schedule a snooze-expiry timer at snooze_until."""
        rt.cancel_snooze_timer()

        if rt.snooze_until is None:
            return

        if rt.snooze_until <= dt_util.now():
            return

        @callback
        def _snooze_expiry_callback(_now: datetime) -> None:
            if self._runtime is None:
                return
            self._runtime.snooze_until = None
            self._runtime._unsubscribe_snooze_timer = None
            self._runtime.recompute()
            self._persist({"snooze_until": None})
            self._schedule(self._runtime)
            self.async_set_updated_data(self._snapshot())

        rt._unsubscribe_snooze_timer = async_track_point_in_time(
            self.hass, HassJob(_snooze_expiry_callback), rt.snooze_until
        )

    @callback
    def _cancel_timers(self, rt: ChoreRuntime) -> None:
        """Cancel all timers on a runtime."""
        rt.cancel_overdue_timer()
        rt.cancel_snooze_timer()

    # ------------------------------------------------------------------
    # Private persistence
    # ------------------------------------------------------------------

    def _persist(self, fields: dict[str, Any]) -> None:
        """Write updated runtime fields back to entry.options for persistence."""
        new_opts = {**self.config_entry.options, **fields}
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_opts)

    def _commit(self) -> None:
        """Schedule timers, persist runtime fields, and push a snapshot update."""
        assert self._runtime is not None
        rt = self._runtime
        self._schedule_timers()
        self._persist(
            {
                "last_completed": rt.last_completed.isoformat()
                if rt.last_completed
                else None,
                "snooze_until": rt.snooze_until.isoformat()
                if rt.snooze_until
                else None,
            }
        )
        self.async_set_updated_data(self._snapshot())

    def _resolve_datetime_field(
        self,
        opts: dict[str, Any],
        field_name: str,
        issue_key: str,
        entry_id: str,
        chore_name: str,
    ) -> datetime | None:
        """Parse a datetime option field; create or delete a repair issue accordingly."""
        raw = opts.get(field_name)
        parsed: datetime | None = None
        if raw:
            try:
                parsed = _parse_aware_datetime(raw)
            except ValueError:
                parsed = None
        if raw and parsed is None:
            _LOGGER.warning(
                "Chore entry %s has a corrupt %r field (%r); clearing to None",
                entry_id,
                field_name,
                raw,
            )
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"{issue_key}_{entry_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=issue_key,
                translation_placeholders={"name": chore_name},
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, f"{issue_key}_{entry_id}")
        return parsed


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


def _snooze_target(value: int, unit: str) -> datetime:
    """Return the snooze expiry datetime: now + value units."""
    return dt_util.now() + timedelta(**{unit: value})


def _time_on_local_date(local_date: date, notification_time: str) -> datetime:
    """Return a tz-aware datetime at notification_time on local_date."""
    hour, minute = map(int, notification_time.split(":"))
    return dt_util.start_of_local_day(local_date).replace(hour=hour, minute=minute)
