"""FastAPI entrypoint for the authoritative LangGraph orchestrator."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from agent_runtime_boundaries.adapters.a2a_transport import A2ASpecialistClient
from agent_runtime_boundaries.adapters.langgraph_runtime import build_graph, run_review
from agent_runtime_boundaries.adapters.observability import configure_observability
from agent_runtime_boundaries.adapters.postgres_ledger import PostgresEffectLedger
from agent_runtime_boundaries.config import Settings
from agent_runtime_boundaries.domain.contracts import GraphState, ReviewCommand, ReviewResult

settings = Settings()
observability = configure_observability(
    service_name="langgraph-orchestrator",
    enabled=settings.otel_enabled,
    otlp_endpoint=settings.otel_exporter_otlp_endpoint,
)

_runtime: dict[str, Any] = {}
_fail_once_seen: set[str] = set()


async def _failure_hook(state: GraphState) -> None:
    """Inject one crash after the remote effect so replay behavior is observable."""
    if not settings.fail_after_specialist_once:
        return
    key = str(state["delegation_id"])
    if key not in _fail_once_seen:
        _fail_once_seen.add(key)
        raise RuntimeError("injected failure after specialist completion")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Own independent durable connections for checkpointing and the effect ledger."""
    del app
    specialist = A2ASpecialistClient(
        endpoint=settings.specialist_a2a_url,
        observability=observability,
    )
    ledger_pool = AsyncConnectionPool(
        settings.database_url,
        min_size=settings.effect_ledger_pool_min_size,
        max_size=settings.effect_ledger_pool_max_size,
        open=False,
    )
    try:
        async with (
            ledger_pool,
            AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer,
        ):
            await checkpointer.setup()
            ledger = PostgresEffectLedger(ledger_pool)
            await ledger.setup()
            _runtime["graph"] = build_graph(
                specialist=specialist,
                ledger=ledger,
                checkpointer=checkpointer,
                after_specialist_hook=_failure_hook,
            )
            yield
    finally:
        _runtime.clear()
        observability.flush()
        observability.shutdown()


app = FastAPI(title="Agent Runtime Boundaries Orchestrator", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Report the runtime role without exposing infrastructure details."""
    return {"status": "ok", "runtime": "langgraph", "state_scope": "global"}


@app.post("/v1/reviews", response_model=ReviewResult)
async def review(command: ReviewCommand) -> ReviewResult:
    """Execute or resume one review under the canonical conversation identity."""
    graph = _runtime.get("graph")
    if graph is None:
        raise HTTPException(status_code=503, detail="runtime not initialized")
    try:
        return await run_review(graph, command)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=type(exc).__name__) from None
