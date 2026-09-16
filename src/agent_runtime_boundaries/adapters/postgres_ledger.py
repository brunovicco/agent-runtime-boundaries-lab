"""PostgreSQL effect ledger for replay-safe remote delegations."""

import json
from typing import Any

from psycopg_pool import AsyncConnectionPool


class PostgresEffectLedger:
    """Persist completed effects separately from LangGraph checkpoints.

    Each key moves through at most two durable states: `pending` (reserved
    before the remote effect runs) and `completed` (the effect's result).
    A crash between those states leaves the `pending` row in place, so the
    attempt is auditable even though it is not exactly-once: a retry can
    still invoke the remote effect again for the same key.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        """Use a pooled connection so concurrent requests never share one session."""
        self._pool = pool

    async def setup(self) -> None:
        """Create the minimal ledger table."""
        async with self._pool.connection() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_effect_ledger (
                    idempotency_key TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    payload JSONB,
                    reserved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    completed_at TIMESTAMPTZ
                )
                """
            )
            await connection.commit()

    async def get_completed(self, key: str) -> dict[str, Any] | None:
        """Return one completed payload."""
        async with self._pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT payload FROM agent_effect_ledger "
                "WHERE idempotency_key = %s AND status = 'completed'",
                (key,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        payload = row[0]
        if isinstance(payload, str):
            return dict(json.loads(payload))
        return dict(payload)

    async def reserve(self, key: str) -> bool:
        """Durably mark one key as pending before its effect runs."""
        async with self._pool.connection() as connection:
            cursor = await connection.execute(
                """
                INSERT INTO agent_effect_ledger (idempotency_key, status)
                VALUES (%s, 'pending')
                ON CONFLICT (idempotency_key) DO NOTHING
                """,
                (key,),
            )
            await connection.commit()
            return cursor.rowcount == 1

    async def complete(self, key: str, payload: dict[str, Any]) -> None:
        """Promote a pending (or absent) key to completed exactly once."""
        encoded = json.dumps(payload, sort_keys=True)
        async with self._pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO agent_effect_ledger (idempotency_key, status, payload, completed_at)
                VALUES (%s, 'completed', %s::jsonb, now())
                ON CONFLICT (idempotency_key) DO UPDATE
                    SET status = 'completed', payload = EXCLUDED.payload, completed_at = now()
                    WHERE agent_effect_ledger.status = 'pending'
                """,
                (key, encoded),
            )
            await connection.commit()
        stored = await self.get_completed(key)
        if stored != payload:
            raise RuntimeError("conflicting payload for completed idempotency key")
