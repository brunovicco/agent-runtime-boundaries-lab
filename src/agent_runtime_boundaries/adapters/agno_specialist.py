"""Agno specialist whose state is explicitly local to the specialist boundary."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.run.base import RunStatus

from agent_runtime_boundaries.adapters.agno_text_model import AgnoTextModel
from agent_runtime_boundaries.adapters.text_generation import TextGenerationClient, TextModelError
from agent_runtime_boundaries.domain.contracts import SpecialistRequest, SpecialistResponse


class AgnoRiskSpecialist:
    """Use Agno for specialist reasoning without owning the global workflow."""

    def __init__(
        self,
        *,
        client: TextGenerationClient,
        db_file: str,
    ) -> None:
        """Build a specialist-local agent with one explicitly selected model backend."""
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
        model = AgnoTextModel(client)
        self._agent = Agent(
            name="risk-review-specialist",
            model=model,
            db=SqliteDb(db_file=db_file),
            add_history_to_context=False,
            retries=0,
            telemetry=False,
            session_state={"scope": "specialist-local-only"},
            instructions=(
                "You are a bounded risk-analysis specialist. Analyze only the supplied request. "
                "Do not claim to change workflow status, approve transactions, "
                "or execute side effects. "
                "Return a concise factual summary."
            ),
        )

    async def analyze(self, request: SpecialistRequest) -> SpecialistResponse:
        """Run one Agno execution mapped from canonical application identity."""
        prompt = (
            f"Task: {request.prompt}\n"
            f"Payload: {request.payload}\n"
            "Return a concise risk-analysis summary and explicitly call out uncertainty."
        )
        output = await self._agent.arun(
            prompt,
            session_id=request.identity.agno_session_id,
            run_id=request.identity.agno_run_id,
            session_state={
                "scope": "specialist-local-only",
                "delegation_id": request.identity.delegation_id,
                "idempotency_key": request.idempotency_key,
            },
        )
        if output.status is not RunStatus.completed:
            raise TextModelError("Agno specialist generation did not complete")
        content: Any = getattr(output, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise TextModelError("Agno specialist returned no text")
        summary = content
        return SpecialistResponse(
            identity=request.identity,
            specialist=request.specialist,
            summary=summary,
            facts={"runtime": "agno", "global_state_owned": False},
            local_state_version=request.identity.agno_run_id,
        )
