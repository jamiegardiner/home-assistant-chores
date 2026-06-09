"""Coordinator for the Chores integration.

Holds and persists per-chore runtime state, derives status/next_due,
schedules overdue-transition timers, and exposes async_complete.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import CONF_CHORES, DOMAIN
from .models import ChoreConfig

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


def _unique_slug(name: str, existing: set[str]) -> str:
    """Return a slug for name that does not collide with existing slugs."""
    base = slugify(name)
    candidate = base
    index = 1
    while candidate in existing:
        candidate = f"{base}_{index}"
        index += 1
    return candidate


def _interval_to_timedelta(config: ChoreConfig) -> timedelta:
    """Convert a ChoreConfig interval to a timedelta."""
    days = config.interval_value
    if config.interval_unit == "weeks":
        days = config.interval_value * 7
    return timedelta(days=days)


@dataclass
class ChoreRuntime:
    """Runtime state for a single chore."""

    chore_id: str
    config: ChoreConfig
    last_completed: date
    status: str = "done"
    next_due: datetime = field(default_factory=dt_util.now)
    _cancel_timer: Callable[[], None] | None = field(default=None, repr=False)


class ChoresCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that manages chore state and timers."""

    def __init__(self, hass: HomeAssistant, entry: Any) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self._entry = entry
        self.store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._chores: dict[str, ChoreRuntime] = {}
        # Map entity_id -> chore_id (populated by sensor platform)
        self._entity_to_chore: dict[str, str] = {}

    async def async_initialize(self) -> None:
        """Load chores from config entry, hydrate from store, compute state."""
        stored: dict[str, str] = await self.store.async_load() or {}

        chore_dicts: list[dict[str, Any]] = self._entry.data.get(CONF_CHORES, [])

        used_slugs: set[str] = set()
        self._chores = {}

        for chore_dict in chore_dicts:
            config = ChoreConfig.from_dict(chore_dict)
            chore_id = _unique_slug(config.name, used_slugs)
            used_slugs.add(chore_id)

            # Hydrate last_completed from store (as ISO date string) or config
            stored_iso = stored.get(chore_id)
            if stored_iso:
                try:
                    last_completed = date.fromisoformat(stored_iso)
                except ValueError:
                    last_completed = config.last_completed
            else:
                last_completed = config.last_completed

            rt = ChoreRuntime(
                chore_id=chore_id,
                config=config,
                last_completed=last_completed,
            )
            self._chores[chore_id] = rt
            self._recompute(rt)
            self._schedule(rt)

        self.async_set_updated_data(self._snapshot())

    def _recompute(self, rt: ChoreRuntime) -> None:
        """Recompute status and next_due for a chore runtime."""
        delta = _interval_to_timedelta(rt.config)
        # next_due is the local start-of-day of (last_completed + interval)
        due_date = rt.last_completed + delta
        rt.next_due = dt_util.start_of_local_day(due_date)
        now = dt_util.now()
        rt.status = "overdue" if now >= rt.next_due else "done"

    def _schedule(self, rt: ChoreRuntime) -> None:
        """Schedule a timer to fire the overdue transition at next_due."""
        # Cancel any existing timer for this chore
        if rt._cancel_timer is not None:
            rt._cancel_timer()
            rt._cancel_timer = None

        now = dt_util.now()
        if rt.next_due <= now:
            # Already overdue; no future timer needed
            return

        chore_id = rt.chore_id

        @callback
        def _overdue_callback(_now: datetime) -> None:
            """Fire when the chore becomes overdue."""
            if chore_id not in self._chores:
                return
            runtime = self._chores[chore_id]
            self._recompute(runtime)
            self.async_set_updated_data(self._snapshot())

        cancel = async_track_point_in_time(self.hass, _overdue_callback, rt.next_due)
        rt._cancel_timer = cancel

    async def async_complete(self, chore_id: str) -> None:
        """Mark a chore as completed now, recompute state, and persist."""
        if chore_id not in self._chores:
            _LOGGER.warning("async_complete called for unknown chore_id: %s", chore_id)
            return

        rt = self._chores[chore_id]
        rt.last_completed = dt_util.now().date()
        self._recompute(rt)
        self._schedule(rt)
        await self._persist()
        self.async_set_updated_data(self._snapshot())

    async def _persist(self) -> None:
        """Persist last_completed for all chores to the store."""
        payload = {
            chore_id: rt.last_completed.isoformat()
            for chore_id, rt in self._chores.items()
        }
        await self.store.async_save(payload)

    @callback
    def async_shutdown_timers(self) -> None:
        """Cancel all scheduled overdue timers. Called on entry unload."""
        for rt in self._chores.values():
            if rt._cancel_timer is not None:
                rt._cancel_timer()
                rt._cancel_timer = None

    def _snapshot(self) -> dict[str, Any]:
        """Return a snapshot of current chore state (consumed by sensor platform)."""
        return {
            chore_id: {
                "chore_id": rt.chore_id,
                "name": rt.config.name,
                "last_completed": rt.last_completed,
                "status": rt.status,
                "next_due": rt.next_due,
            }
            for chore_id, rt in self._chores.items()
        }

    @property
    def chore_ids(self) -> list[str]:
        """Return all chore ids."""
        return list(self._chores.keys())

    def chore_state(self, chore_id: str) -> dict[str, Any]:
        """Return the current snapshot state dict for a single chore.

        Consumed by the sensor platform. Keys: ``chore_id``, ``name``,
        ``last_completed``, ``status``, ``next_due``.
        """
        data: dict[str, Any] = self.data or {}
        if chore_id in data:
            return data[chore_id]
        rt = self._chores.get(chore_id)
        if rt is None:
            return {}
        return {
            "chore_id": rt.chore_id,
            "name": rt.config.name,
            "last_completed": rt.last_completed,
            "status": rt.status,
            "next_due": rt.next_due,
        }

    def get_chore_runtime(self, chore_id: str) -> ChoreRuntime | None:
        """Return the runtime for a given chore_id."""
        return self._chores.get(chore_id)

    def register_entity(self, entity_id: str, chore_id: str) -> None:
        """Register a sensor entity_id -> chore_id mapping."""
        self._entity_to_chore[entity_id] = chore_id

    def chore_id_for_entity(self, entity_id: str) -> str | None:
        """Resolve an entity_id to a chore_id."""
        return self._entity_to_chore.get(entity_id)
