import pytest
from pydantic import ValidationError

from agent_runtime_boundaries.domain.identity import ExecutionIdentity


def test_framework_id_mapping_is_adapter_friendly() -> None:
    identity = ExecutionIdentity(
        conversation_id="conversation-1",
        execution_id="exec:1",
        delegation_id="deleg:1",
    )
    assert identity.langgraph_thread_id == "conversation-1"
    assert identity.agno_session_id == "conversation-1"
    assert identity.agno_run_id == "deleg:1"
    assert identity.idempotency_key("specialist-risk-review") == (
        "exec:1:deleg:1:specialist-risk-review"
    )


def test_identity_generates_execution_and_delegation_ids() -> None:
    identity = ExecutionIdentity(conversation_id="conversation-1")
    assert identity.execution_id.startswith("exec:")
    assert identity.delegation_id.startswith("deleg:")


def test_identifier_validation_rejects_unsafe_values() -> None:
    with pytest.raises(ValidationError):
        ExecutionIdentity(conversation_id="contains a space")


def test_idempotency_operation_is_normalized() -> None:
    identity = ExecutionIdentity(
        conversation_id="conversation-1",
        execution_id="exec:1",
        delegation_id="deleg:1",
    )
    assert identity.idempotency_key(" Risk Review ") == "exec:1:deleg:1:risk-review"


def test_idempotency_operation_rejects_unsafe_value() -> None:
    identity = ExecutionIdentity(conversation_id="conversation-1")
    with pytest.raises(ValueError, match="operation"):
        identity.idempotency_key("risk/review")
