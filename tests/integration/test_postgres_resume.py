"""Integration proof for checkpoint recovery versus completed-effect replay."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection

from agent_runtime_boundaries.adapters.fake_specialist import FakeSpecialist
from agent_runtime_boundaries.adapters.langgraph_runtime import build_graph, run_review
from agent_runtime_boundaries.adapters.postgres_ledger import PostgresEffectLedger
from agent_runtime_boundaries.domain.contracts import GraphState, ReviewCommand

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_crash_after_specialist_reuses_completed_delegation_on_retry() -> None:
    database_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:5432/agent_runtime_boundaries",
    )
    suffix = uuid4().hex
    command = ReviewCommand(
        conversation_id=f"conversation-{suffix}",
        execution_id=f"exec:{suffix}",
        delegation_id=f"deleg:{suffix}",
        prompt="Analyze risk",
        payload={"risk": "low"},
    )
    specialist = FakeSpecialist()
    failed = False

    async def fail_once(_state: GraphState) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("crash after completed specialist delegation")

    ledger_connection = await AsyncConnection.connect(database_url, autocommit=False)
    try:
        async with AsyncPostgresSaver.from_conn_string(database_url) as checkpointer:
            await checkpointer.setup()
            ledger = PostgresEffectLedger(ledger_connection)
            await ledger.setup()
            graph = build_graph(
                specialist=specialist,
                ledger=ledger,
                checkpointer=checkpointer,
                after_specialist_hook=fail_once,
            )

            with pytest.raises(RuntimeError, match="crash after completed"):
                await run_review(graph, command)
            assert specialist.calls == 1

            result = await run_review(graph, command)
            assert result.specialist_reused is True
            assert specialist.calls == 1
            assert result.summary == f"Deterministic review for conversation-{suffix}"
    finally:
        await ledger_connection.close()
