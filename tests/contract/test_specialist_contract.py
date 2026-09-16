from agent_runtime_boundaries.domain.contracts import SpecialistRequest, SpecialistResponse
from agent_runtime_boundaries.domain.identity import ExecutionIdentity


def test_specialist_response_does_not_expose_global_workflow_phase() -> None:
    identity = ExecutionIdentity(
        conversation_id="conversation-1",
        execution_id="exec:1",
        delegation_id="deleg:1",
    )
    request = SpecialistRequest(
        identity=identity,
        prompt="Analyze",
        payload={},
        idempotency_key=identity.idempotency_key("specialist-risk-review"),
    )
    response = SpecialistResponse(
        identity=request.identity,
        specialist=request.specialist,
        summary="Low observed risk.",
    )
    assert "phase" not in response.model_dump()
    assert "workflow_status" not in response.model_dump()
