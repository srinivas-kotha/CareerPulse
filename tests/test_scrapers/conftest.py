"""Parser fixtures make no real source requests; avoid cross-test wall-clock waits."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def isolated_source_limiter(monkeypatch):
    # Production rate limits are tested separately in test_rate_limiter.py.
    # Sharing that singleton across mocked parser tests needlessly consumes
    # real per-domain quotas and makes this suite take many minutes.
    limiter = SimpleNamespace(acquire=AsyncMock())
    monkeypatch.setattr("app.scrapers.base.get_limiter_for_url", lambda url: limiter)
