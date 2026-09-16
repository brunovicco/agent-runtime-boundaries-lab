"""FastAPI entrypoint for the Agno specialist service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent_runtime_boundaries.adapters.a2a_server import build_a2a_router
from agent_runtime_boundaries.adapters.agno_specialist import AgnoRiskSpecialist
from agent_runtime_boundaries.adapters.observability import configure_observability
from agent_runtime_boundaries.config import Settings

settings = Settings()
observability = configure_observability(
    service_name="agno-risk-specialist",
    enabled=settings.otel_enabled,
    otlp_endpoint=settings.otel_exporter_otlp_endpoint,
)
specialist = AgnoRiskSpecialist(
    client=settings.text_client(),
    db_file=settings.agno_db_file,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Flush and close specialist observability on shutdown."""
    del app
    try:
        yield
    finally:
        observability.flush()
        observability.shutdown()


app = FastAPI(title="Agno Risk Specialist", version="0.2.0", lifespan=lifespan)
app.include_router(build_a2a_router(specialist=specialist, observability=observability))


@app.get("/health")
async def health() -> dict[str, str]:
    """Describe the local specialist boundary without credentials."""
    return {
        "status": "ok",
        "runtime": "agno",
        "state_scope": "specialist-local",
        "llm_backend": settings.llm_backend,
    }
