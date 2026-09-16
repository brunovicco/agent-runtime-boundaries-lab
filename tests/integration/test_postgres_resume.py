"""Integration proof for checkpoint recovery versus completed-effect replay."""

import os
from uuid import uuid4

import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from agent_runtime_boundaries.adapters.fake_specialist import FakeSpecialist
from agent_runtime_boundaries.adapters.langgraph_runtime import build_graph, run_review
from agent_runtime_boundaries.adapters.postgres_ledger import PostgresEffectLedger
from agent_runtime_boundaries.domain.contracts import GraphState, ReviewCommand
from agent_runtime_boundaries.domain.identity import ExecutionIdentity

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5432/agent_runtime_boundaries",
)


def _command(suffix: str) -> ReviewCommand:
    return ReviewCommand(
        conversation_id=f"conversation-{suffix}",
        execution_id=f"exec:{suffix}",
        delegation_id=f"deleg:{suffix}",
        prompt="Analyze risk",
        payload={"risk": "low"},
    )


@pytest.mark.asyncio
async def test_crash_after_specialist_reuses_completed_delegation_on_retry() -> None:
    suffix = uuid4().hex
    command = _command(suffix)
    specialist = FakeSpecialist()
    failed = False

    async def fail_once(_state: GraphState) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("crash after completed specialist delegation")

    async with (
        AsyncConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=False) as pool,
        AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer,
    ):
        await checkpointer.setup()
        ledger = PostgresEffectLedger(pool)
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


@pytest.mark.asyncio
async def test_crash_before_ledger_complete_reattempts_specialist_on_retry() -> None:
    """A crash between the specialist call and the ledger write is at-least-once, not exactly-once.

    The pending reservation survives the crash (auditable), but the retry still
    invokes the specialist again because the effect was never durably completed.
    """
    suffix = uuid4().hex
    command = _command(suffix)
    specialist = FakeSpecialist()
    crashed = False

    async def crash_before_complete(_state: GraphState) -> None:
        nonlocal crashed
        if not crashed:
            crashed = True
            raise RuntimeError("crash before ledger completion")

    async with (
        AsyncConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=False) as pool,
        AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer,
    ):
        await checkpointer.setup()
        ledger = PostgresEffectLedger(pool)
        await ledger.setup()
        graph = build_graph(
            specialist=specialist,
            ledger=ledger,
            checkpointer=checkpointer,
            before_complete_hook=crash_before_complete,
        )

        identity = ExecutionIdentity(
            conversation_id=command.conversation_id,
            execution_id=command.execution_id or "",
            delegation_id=command.delegation_id or "",
        )
        idempotency_key = identity.idempotency_key("specialist-risk-review")

        with pytest.raises(RuntimeError, match="crash before ledger completion"):
            await run_review(graph, command)
        assert specialist.calls == 1
        assert await ledger.get_completed(idempotency_key) is None
        assert await ledger.reserve(idempotency_key) is False

        result = await run_review(graph, command)
        assert result.specialist_reused is False
        assert specialist.calls == 2
        assert result.summary == f"Deterministic review for conversation-{suffix}"
