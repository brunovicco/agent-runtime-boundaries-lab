"""Ports implemented by infrastructure adapters."""

from __future__ import annotations

from typing import Any, Protocol

from agent_runtime_boundaries.domain.contracts import SpecialistRequest, SpecialistResponse


class SpecialistPort(Protocol):
    """Remote or local specialist capability."""

    async def analyze(self, request: SpecialistRequest) -> SpecialistResponse:
        """Return a specialist result for one canonical delegation."""
        ...


class EffectLedger(Protocol):
    """Durable replay-protection ledger."""

    async def get_completed(self, key: str) -> dict[str, Any] | None:
        """Return a previously completed payload if present."""
        ...

    async def complete(self, key: str, payload: dict[str, Any]) -> None:
        """Record a completed operation exactly once."""
        ...
