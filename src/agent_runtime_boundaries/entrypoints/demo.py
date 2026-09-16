"""Credential-free demonstration of state ownership and replay protection."""

from __future__ import annotations

import asyncio

from agent_runtime_boundaries.adapters.fake_specialist import FakeSpecialist
from agent_runtime_boundaries.adapters.memory_ledger import InMemoryEffectLedger
from agent_runtime_boundaries.application.service import build_identity, build_specialist_request
from agent_runtime_boundaries.domain.contracts import (
    ReviewCommand,
    SpecialistResponse,
    WorkflowPhase,
)


async def execute_once(
    command: ReviewCommand,
    specialist: FakeSpecialist,
    ledger: InMemoryEffectLedger,
) -> tuple[WorkflowPhase, bool, str]:
    """Exercise the same delegation/idempotency policy without LangGraph dependencies."""
    identity = build_identity(command)
    request = build_specialist_request(command, identity)
    cached = await ledger.get_completed(request.idempotency_key)
    reused = cached is not None
    if cached is None:
        response = await specialist.analyze(request)
        cached = response.model_dump(mode="json")
        await ledger.complete(request.idempotency_key, cached)
    response = SpecialistResponse.model_validate(cached)
    return WorkflowPhase.COMPLETED, reused, response.summary


async def main() -> None:
    """Show that replay reuses the completed specialist result."""
    specialist = FakeSpecialist()
    ledger = InMemoryEffectLedger()
    command = ReviewCommand(
        conversation_id="merchant-123",
        execution_id="exec:demo-1",
        delegation_id="deleg:demo-1",
        prompt="Review merchant risk.",
        payload={"merchant_tier": "growth", "chargeback_ratio": 0.012},
    )

    phase1, reused1, _ = await execute_once(command, specialist, ledger)
    print(
        f"first execution: specialist_calls={specialist.calls} "
        f"phase={phase1.value} reused={reused1}"
    )

    phase2, reused2, _ = await execute_once(command, specialist, ledger)
    print(
        f"retry:           specialist_calls={specialist.calls} "
        f"phase={phase2.value} reused={reused2}"
    )


if __name__ == "__main__":
    asyncio.run(main())
