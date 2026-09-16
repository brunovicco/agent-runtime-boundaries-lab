"""Keep credential-free framework tests within repository-local storage."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Prevent framework imports from writing to user storage or enabling telemetry."""
    monkeypatch = pytest.MonkeyPatch()
    config.add_cleanup(monkeypatch.undo)
    monkeypatch.setenv("CREWAI_STORAGE_DIR", str(config.rootpath / ".data" / "tests-crewai"))
    monkeypatch.setenv("AGNO_TELEMETRY", "false")
    monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "true")
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "false")
    monkeypatch.setenv("CREWAI_DISABLE_VERSION_CHECK", "true")
