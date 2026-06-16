"""Shared fixtures for chores coordinator tests."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_TRACK_PATCH = "custom_components.chores.coordinator.async_track_point_in_time"


@pytest.fixture(autouse=True)
def patch_track():
    with patch(_TRACK_PATCH) as mock_track:
        yield mock_track


@pytest.fixture
def fake_track(patch_track: MagicMock) -> dict[str, Any]:
    """Override the autouse timer patch to capture the scheduled callback."""
    captured: dict[str, Any] = {}

    def _side_effect(hass_: Any, cb: Any, point_in_time: Any) -> MagicMock:
        captured["cb"] = cb.target
        return MagicMock()

    patch_track.side_effect = _side_effect
    return captured
