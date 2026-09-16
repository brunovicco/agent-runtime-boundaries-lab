"""Framework-neutral workflow policies."""

from __future__ import annotations

from agent_runtime_boundaries.domain.contracts import ReviewCommand, SpecialistRequest
from agent_runtime_boundaries.domain.identity import ExecutionIdentity


def build_identity(command: ReviewCommand) -> ExecutionIdentity:
    """Create canonical execution identity from an API command."""
    kwargs: dict[str, str] = {"conversation_id": command.conversation_id}
    if command.execution_id is not None:
        kwargs["execution_id"] = command.execution_id
    if command.delegation_id is not None:
        kwargs["delegation_id"] = command.delegation_id
    return ExecutionIdentity(**kwargs)


def build_specialist_request(
    command: ReviewCommand, identity: ExecutionIdentity
) -> SpecialistRequest:
    """Create the only payload allowed to cross into the specialist runtime."""
    return SpecialistRequest(
        identity=identity,
        prompt=command.prompt,
        payload=command.payload,
        idempotency_key=identity.idempotency_key("specialist-risk-review"),
    )
