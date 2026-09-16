import pytest

from agent_runtime_boundaries.adapters.fake_specialist import FakeSpecialist
from agent_runtime_boundaries.adapters.memory_ledger import InMemoryEffectLedger
from agent_runtime_boundaries.domain.contracts import ReviewCommand
from agent_runtime_boundaries.entrypoints.demo import execute_once


@pytest.mark.asyncio
async def test_retry_does_not_call_specialist_twice() -> None:
    specialist = FakeSpecialist()
    ledger = InMemoryEffectLedger()
    command = ReviewCommand(
        conversation_id="conversation-1",
        execution_id="exec:1",
        delegation_id="deleg:1",
        prompt="Analyze risk",
        payload={"a": 1},
    )

    _, reused_first, _ = await execute_once(command, specialist, ledger)
    _, reused_second, _ = await execute_once(command, specialist, ledger)

    assert reused_first is False
    assert reused_second is True
    assert specialist.calls == 1
