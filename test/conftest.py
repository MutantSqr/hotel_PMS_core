from datetime import datetime

import pytest

import app.assist as assist_module


class FrozenDateTime(datetime):
    """Stable clock for legacy PMS tests that omit current_datetime."""

    @classmethod
    def now(cls, tz=None):
        return cls(2026, 8, 12, 15, 5)


@pytest.fixture(autouse=True)
def freeze_assistant_clock(monkeypatch):
    """Keep lifecycle tests deterministic as real calendar time advances."""
    monkeypatch.setattr(assist_module, "datetime", FrozenDateTime)
