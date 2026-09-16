import pytest

from agent_runtime_boundaries.adapters.fake_specialist import FakeSpecialist
from agent_runtime_boundaries.application.service import build_identity, build_specialist_request
from agent_runtime_boundaries.domain.contracts import ReviewCommand


@pytest.mark.asyncio
async def test_fake_specialist_is_deterministic_and_counts_calls() -> None:
    command = ReviewCommand(
        conversation_id="conversation-1",
        execution_id="exec:1",
        delegation_id="deleg:1",
        prompt="Analyze",
        payload={"b": 2, "a": 1},
    )
    request = build_specialist_request(command, build_identity(command))
    specialist = FakeSpecialist()

    response = await specialist.analyze(request)

    assert response.summary == "Deterministic review for conversation-1"
    assert response.facts == {"payload_keys": ["a", "b"]}
    assert response.local_state_version == "fake:1"
    assert specialist.calls == 1
