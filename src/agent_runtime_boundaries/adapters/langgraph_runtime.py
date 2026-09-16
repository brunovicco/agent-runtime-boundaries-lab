"""LangGraph adapter: the single authoritative workflow runtime."""

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from agent_runtime_boundaries.application.ports import EffectLedger, SpecialistPort
from agent_runtime_boundaries.application.service import execute_delegation
from agent_runtime_boundaries.domain.contracts import (
    GraphState,
    ReviewCommand,
    ReviewResult,
    SpecialistRequest,
    SpecialistResponse,
    WorkflowPhase,
)
from agent_runtime_boundaries.domain.identity import ExecutionIdentity

FailureHook = Callable[[GraphState], Awaitable[None]]


async def _noop_failure_hook(state: GraphState) -> None:
    del state


def build_graph(
    *,
    specialist: SpecialistPort,
    ledger: EffectLedger,
    checkpointer: Any,
    after_specialist_hook: FailureHook = _noop_failure_hook,
    before_complete_hook: FailureHook = _noop_failure_hook,
) -> Any:
    """Compile the authoritative graph around injected infrastructure ports."""

    async def intake(state: GraphState) -> GraphState:
        return {"phase": WorkflowPhase.DELEGATING.value}

    async def delegate(state: GraphState) -> GraphState:
        identity = ExecutionIdentity(
            conversation_id=state["conversation_id"],
            execution_id=state["execution_id"],
            delegation_id=state["delegation_id"],
        )
        request = SpecialistRequest(
            identity=identity,
            prompt=state["prompt"],
            payload=state.get("payload", {}),
            idempotency_key=identity.idempotency_key("specialist-risk-review"),
        )

        async def before_complete() -> None:
            await before_complete_hook(state)

        response, reused = await execute_delegation(
            ledger=ledger,
            specialist=specialist,
            request=request,
            before_complete=before_complete,
        )
        updates: GraphState = {
            "phase": WorkflowPhase.SPECIALIST_COMPLETED.value,
            "specialist_result": response.model_dump(mode="json"),
            "specialist_reused": reused,
        }
        await after_specialist_hook({**state, **updates})
        return updates

    async def finalize(state: GraphState) -> GraphState:
        response = SpecialistResponse.model_validate(state["specialist_result"])
        return {
            "phase": WorkflowPhase.COMPLETED.value,
            "final_summary": response.summary,
        }

    builder = StateGraph(GraphState)
    builder.add_node("intake", intake)
    builder.add_node("delegate", delegate)
    builder.add_node("finalize", finalize)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "delegate")
    builder.add_edge("delegate", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)


async def run_review(graph: Any, command: ReviewCommand) -> ReviewResult:
    """Invoke the graph using the canonical conversation as LangGraph thread identity."""
    identity = ExecutionIdentity(
        conversation_id=command.conversation_id,
        **({"execution_id": command.execution_id} if command.execution_id else {}),
        **({"delegation_id": command.delegation_id} if command.delegation_id else {}),
    )
    initial: GraphState = {
        "conversation_id": identity.conversation_id,
        "execution_id": identity.execution_id,
        "delegation_id": identity.delegation_id,
        "prompt": command.prompt,
        "payload": command.payload,
        "phase": WorkflowPhase.RECEIVED.value,
        "specialist_reused": False,
    }
    result = await graph.ainvoke(
        initial,
        {"configurable": {"thread_id": identity.langgraph_thread_id}},
    )
    return ReviewResult(
        conversation_id=identity.conversation_id,
        execution_id=identity.execution_id,
        delegation_id=identity.delegation_id,
        phase=WorkflowPhase(result["phase"]),
        summary=result["final_summary"],
        specialist_reused=bool(result.get("specialist_reused", False)),
    )
