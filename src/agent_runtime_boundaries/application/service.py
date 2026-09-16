"""Framework-neutral workflow policies."""

from collections.abc import Awaitable, Callable

from agent_runtime_boundaries.application.ports import EffectLedger, SpecialistPort
from agent_runtime_boundaries.domain.contracts import (
    ReviewCommand,
    SpecialistRequest,
    SpecialistResponse,
)
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


async def execute_delegation(
    *,
    ledger: EffectLedger,
    specialist: SpecialistPort,
    request: SpecialistRequest,
    before_complete: Callable[[], Awaitable[None]] | None = None,
) -> tuple[SpecialistResponse, bool]:
    """Reuse a completed effect, or reserve, delegate and record a new one.

    A crash after `reserve` but before `complete` still leaves a durable pending
    record for this idempotency key, so a later retry is a visible re-attempt
    rather than a silent one. It is not exactly-once: the remote specialist can
    still be invoked more than once for the same key across such a crash.
    """
    cached = await ledger.get_completed(request.idempotency_key)
    if cached is not None:
        return SpecialistResponse.model_validate(cached), True
    await ledger.reserve(request.idempotency_key)
    response = await specialist.analyze(request)
    if before_complete is not None:
        await before_complete()
    payload = response.model_dump(mode="json")
    await ledger.complete(request.idempotency_key, payload)
    return SpecialistResponse.model_validate(payload), False
