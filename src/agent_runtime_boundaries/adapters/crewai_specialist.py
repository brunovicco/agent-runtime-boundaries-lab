"""CrewAI specialist crew kept behind the same framework-neutral boundary as Agno."""

from __future__ import annotations

import asyncio
from typing import Any

from crewai import Agent, Crew, Process, Task

from agent_runtime_boundaries.adapters.crewai_text_llm import CrewAITextLLM
from agent_runtime_boundaries.adapters.text_generation import TextGenerationClient
from agent_runtime_boundaries.domain.contracts import SpecialistRequest, SpecialistResponse


class CrewAIRiskSpecialist:
    """Use a CrewAI Crew for bounded specialist collaboration, not global orchestration."""

    def __init__(
        self,
        *,
        client: TextGenerationClient,
    ) -> None:
        """Build a CrewAI model bridge for one explicitly selected backend."""
        self._llm = CrewAITextLLM(client)

    async def analyze(self, request: SpecialistRequest) -> SpecialistResponse:
        """Run one isolated CrewAI crew for a canonical delegation."""
        summary = await asyncio.to_thread(self._run_crew, request)
        return SpecialistResponse(
            identity=request.identity,
            specialist=request.specialist,
            summary=summary,
            facts={
                "runtime": "crewai",
                "composition": "crew",
                "global_state_owned": False,
                "memory_enabled": False,
            },
            local_state_version=request.identity.delegation_id,
        )

    def _run_crew(self, request: SpecialistRequest) -> str:
        crew = self._build_crew(request)
        output: Any = crew.kickoff()
        raw = getattr(output, "raw", None)
        if isinstance(raw, str) and raw.strip():
            return raw
        rendered = str(output).strip()
        return rendered or "CrewAI specialist returned no text."

    def _build_crew(self, request: SpecialistRequest) -> Crew:
        """Build an isolated CrewAI team for one delegation without executing it."""
        risk_analyst = Agent(
            role="Risk Analyst",
            goal="Identify material risk factors in the supplied request and evidence.",
            backstory=(
                "You are a bounded specialist inside a larger governed workflow. "
                "You analyze evidence but never approve, execute, or change workflow state."
            ),
            llm=self._llm,
            allow_delegation=False,
            max_retry_limit=0,
            respect_context_window=False,
            verbose=False,
        )
        compliance_reviewer = Agent(
            role="Compliance Reviewer",
            goal=(
                "Challenge the risk analysis for missing evidence, uncertainty, "
                "and policy concerns."
            ),
            backstory=(
                "You review another specialist's analysis. You may identify concerns "
                "and uncertainty, "
                "but you cannot change global workflow status or execute side effects."
            ),
            llm=self._llm,
            allow_delegation=False,
            max_retry_limit=0,
            respect_context_window=False,
            verbose=False,
        )

        risk_task = Task(
            description=(
                f"Canonical delegation: {request.identity.delegation_id}\n"
                f"User task: {request.prompt}\n"
                f"Evidence payload: {request.payload}\n"
                "Produce a concise risk analysis. Separate observed facts from inference."
            ),
            expected_output="A concise risk analysis with facts, risks, and explicit uncertainty.",
            agent=risk_analyst,
        )
        review_task = Task(
            description=(
                "Review the preceding risk analysis. Identify unsupported claims, missing "
                "evidence, "
                "and compliance concerns. Return a final concise specialist summary. Do not claim "
                "approval, workflow completion, or execution of any external action."
            ),
            expected_output=(
                "A final specialist summary containing material findings, uncertainty, and any "
                "issues that require the authoritative workflow to decide."
            ),
            agent=compliance_reviewer,
            context=[risk_task],
        )
        return Crew(
            agents=[risk_analyst, compliance_reviewer],
            tasks=[risk_task, review_task],
            process=Process.sequential,
            memory=False,
            cache=False,
            tracing=False,
            share_crew=False,
            verbose=False,
        )
