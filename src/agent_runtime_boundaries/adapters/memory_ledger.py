"""In-memory ledger used by tests and deterministic demo mode."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any


class InMemoryEffectLedger:
    """Concurrency-safe process-local effect ledger."""

    def __init__(self) -> None:
        """Create an empty ledger guarded by an asynchronous lock."""
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_completed(self, key: str) -> dict[str, Any] | None:
        """Return a copy so callers cannot mutate ledger state."""
        async with self._lock:
            item = self._items.get(key)
            return deepcopy(item) if item is not None else None

    async def complete(self, key: str, payload: dict[str, Any]) -> None:
        """Store a result once; conflicting completions fail closed."""
        async with self._lock:
            existing = self._items.get(key)
            if existing is not None and existing != payload:
                raise RuntimeError("idempotency key already completed with a different payload")
            self._items[key] = deepcopy(payload)
