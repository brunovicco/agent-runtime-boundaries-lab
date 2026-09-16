"""CrewAI experiment contract tests that require no model call."""

from crewai import Agent, Process
from governed_llm_gateway_client import GatewayClientConfig
from governed_llm_gateway_contracts import DataClassification, RiskLevel

from agent_runtime_boundaries.adapters.crewai_specialist import CrewAIRiskSpecialist
from agent_runtime_boundaries.adapters.gateway_text import GatewayTextClient, GatewayTextConfig
from agent_runtime_boundaries.domain.contracts import SpecialistRequest
from agent_runtime_boundaries.domain.identity import ExecutionIdentity


def test_crewai_experiment_builds_bounded_two_role_crew() -> None:
    specialist = CrewAIRiskSpecialist(
        client=GatewayTextClient(
            GatewayTextConfig(
                connection=GatewayClientConfig(
                    base_url="https://gateway.invalid", api_key="test-key"
                ),
                workload="agent.orchestration",
                risk_level=RiskLevel.HIGH,
                data_classification=DataClassification.INTERNAL,
            )
        ),
    )
    identity = ExecutionIdentity(
        conversation_id="conversation-1",
        execution_id="exec:1",
        delegation_id="deleg:1",
    )
    request = SpecialistRequest(
        identity=identity,
        prompt="Review merchant risk",
        payload={"merchant_tier": "growth"},
        idempotency_key=identity.idempotency_key("specialist-risk-review"),
    )

    crew = specialist._build_crew(request)

    assert crew.process == Process.sequential
    assert crew.memory is False
    assert crew.cache is False
    assert crew.tracing is False
    assert crew.share_crew is False
    assert len(crew.agents) == 2
    assert len(crew.tasks) == 2
    for agent in crew.agents:
        assert isinstance(agent, Agent)
        assert agent.max_retry_limit == 0
        assert agent.respect_context_window is False
