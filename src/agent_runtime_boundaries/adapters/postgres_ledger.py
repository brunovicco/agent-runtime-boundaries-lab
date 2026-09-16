"""PostgreSQL effect ledger for replay-safe remote delegations."""

from __future__ import annotations

import json
from typing import Any

from psycopg import AsyncConnection


class PostgresEffectLedger:
    """Persist completed effects separately from LangGraph checkpoints."""

    def __init__(self, connection: AsyncConnection[Any]) -> None:
        """Use the application's dedicated effect-ledger connection."""
        self._connection = connection

    async def setup(self) -> None:
        """Create the minimal ledger table."""
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_effect_ledger (
                idempotency_key TEXT PRIMARY KEY,
                payload JSONB NOT NULL,
                completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        await self._connection.commit()

    async def get_completed(self, key: str) -> dict[str, Any] | None:
        """Return one completed payload."""
        cursor = await self._connection.execute(
            "SELECT payload FROM agent_effect_ledger WHERE idempotency_key = %s",
            (key,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        payload = row[0]
        if isinstance(payload, str):
            return dict(json.loads(payload))
        return dict(payload)

    async def complete(self, key: str, payload: dict[str, Any]) -> None:
        """Insert once and reject conflicting duplicate completions."""
        await self._connection.execute(
            """
            INSERT INTO agent_effect_ledger (idempotency_key, payload)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (idempotency_key) DO NOTHING
            """,
            (key, json.dumps(payload, sort_keys=True)),
        )
        await self._connection.commit()
        stored = await self.get_completed(key)
        if stored != payload:
            raise RuntimeError("conflicting payload for completed idempotency key")
