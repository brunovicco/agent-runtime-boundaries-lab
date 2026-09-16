from agent_runtime_boundaries.application.service import build_identity, build_specialist_request
from agent_runtime_boundaries.domain.contracts import ReviewCommand


def test_build_identity_preserves_caller_supplied_ids() -> None:
    command = ReviewCommand(
        conversation_id="conversation-1",
        execution_id="exec:1",
        delegation_id="deleg:1",
        prompt="Analyze",
    )
    identity = build_identity(command)
    assert identity.execution_id == "exec:1"
    assert identity.delegation_id == "deleg:1"


def test_build_identity_generates_missing_ids() -> None:
    identity = build_identity(ReviewCommand(conversation_id="conversation-1", prompt="Analyze"))
    assert identity.execution_id.startswith("exec:")
    assert identity.delegation_id.startswith("deleg:")


def test_build_specialist_request_uses_canonical_identity() -> None:
    command = ReviewCommand(
        conversation_id="conversation-1",
        execution_id="exec:1",
        delegation_id="deleg:1",
        prompt="Analyze",
        payload={"risk": "low"},
    )
    identity = build_identity(command)
    request = build_specialist_request(command, identity)
    assert request.identity == identity
    assert request.payload == {"risk": "low"}
    assert request.idempotency_key == "exec:1:deleg:1:specialist-risk-review"
