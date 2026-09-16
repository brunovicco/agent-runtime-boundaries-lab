"""Exercise both specialist frameworks against the real SDK with credential-free SSE."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from agno.models.message import Message as AgnoMessage
from crewai.utilities.types import LLMMessage
from governed_llm_gateway_client import (
    GatewayClientConfig,
    GatewayHTTPError,
    GatewayProtocolError,
    GatewayTransportError,
)
from governed_llm_gateway_contracts import DataClassification, RiskLevel

from agent_runtime_boundaries.adapters.agno_specialist import AgnoRiskSpecialist
from agent_runtime_boundaries.adapters.agno_text_model import AgnoTextModel
from agent_runtime_boundaries.adapters.crewai_specialist import CrewAIRiskSpecialist
from agent_runtime_boundaries.adapters.crewai_text_llm import CrewAITextLLM
from agent_runtime_boundaries.adapters.gateway_text import (
    GatewayTextClient,
    GatewayTextConfig,
)
from agent_runtime_boundaries.adapters.text_generation import TextModelError, text_message
from agent_runtime_boundaries.domain.contracts import SpecialistRequest
from agent_runtime_boundaries.domain.identity import ExecutionIdentity


def routing_payload() -> dict[str, object]:
    return {
        "routing_decision_id": "sha256:" + "1" * 64,
        "policy": {
            "decision_id": "policy-1",
            "policy_id": "gateway-policy",
            "policy_version": "1.0",
            "policy_digest": "sha256:" + "2" * 64,
        },
        "authorized_model_group": "agentic-strong",
        "model_registry_digest": "sha256:" + "3" * 64,
        "ranking_policy_version": "ranking-1",
        "ranking_policy_digest": "sha256:" + "4" * 64,
        "score_snapshot_id": "snapshot-1",
        "provider": "test-provider",
        "model": "test-model",
        "deployment": "test-deployment",
        "fallback_sequence": ["test-deployment"],
    }


def sse_response(request: httpx.Request, *, outcome: str = "success") -> httpx.Response:
    payload = json.loads(request.content)
    request_id = payload["request_id"]
    routing = routing_payload()
    events: list[tuple[str, dict[str, object]]] = [("response.started", {"routing": routing})]
    if outcome != "empty":
        events.append(("content.delta", {"delta": "Final Answer: Material risk needs review."}))
    if outcome == "partial":
        events.append(
            (
                "response.failed",
                {
                    "routing": routing,
                    "partial": True,
                    "error": {
                        "code": "provider_timeout",
                        "message": "raw private error",
                        "retryable": False,
                    },
                },
            )
        )
    elif outcome != "truncated":
        usage = {"input_tokens": 100, "output_tokens": 10, "total_cost_usd": "0.01"}
        events.extend(
            [
                ("usage.completed", {"usage": usage}),
                (
                    "response.completed",
                    {
                        "routing": routing,
                        "finish_reason": "stop",
                        "execution": {
                            "provider": "test-provider",
                            "model": "test-model",
                            "deployment": "test-deployment",
                            "status": "succeeded",
                            "latency_ms": 10,
                            "usage": usage,
                        },
                    },
                ),
            ]
        )
    body = ""
    for sequence, (event_type, extra) in enumerate(events, start=1):
        event = {
            "event_type": event_type,
            "request_id": request_id,
            "sequence_number": sequence,
            **extra,
        }
        body += f"event: {event_type}\nid: {sequence}\ndata: {json.dumps(event)}\n\n"
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)


def gateway_client(handler: Callable[[httpx.Request], httpx.Response]) -> GatewayTextClient:
    return GatewayTextClient(
        GatewayTextConfig(
            connection=GatewayClientConfig(
                base_url="https://gateway.invalid", api_key="test-gateway-key"
            ),
            workload="agent.orchestration",
            risk_level=RiskLevel.HIGH,
            data_classification=DataClassification.CONFIDENTIAL,
        ),
        transport=httpx.MockTransport(handler),
    )


def specialist_request() -> SpecialistRequest:
    identity = ExecutionIdentity(
        conversation_id="conversation-1", execution_id="exec:1", delegation_id="deleg:1"
    )
    return SpecialistRequest(
        identity=identity,
        prompt="Review merchant risk",
        payload={"merchant_tier": "growth"},
        idempotency_key=identity.idempotency_key("specialist-risk-review"),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime", ["agno", "crewai"])
async def test_specialists_use_native_sdk_and_keep_canonical_identity(
    runtime: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNO_TELEMETRY", "false")
    monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "true")
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "false")
    calls: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://gateway.invalid/v1/generate"
        assert request.headers["X-Gateway-API-Key"] == "test-gateway-key"
        assert "authorization" not in request.headers
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["workload"] == "agent.orchestration"
        assert payload["risk_level"] == "high"
        assert payload["data_classification"] == "confidential"
        assert payload["stream"] is True
        assert payload["context_tokens_estimated"] > 0
        assert payload["max_output_tokens"] == 2000
        assert not {"provider", "model", "deployment", "temperature", "stop"} & payload.keys()
        return sse_response(request)

    gateway = gateway_client(handler)
    specialist = (
        AgnoRiskSpecialist(client=gateway, db_file=str(tmp_path / "agno.db"))
        if runtime == "agno"
        else CrewAIRiskSpecialist(client=gateway)
    )
    request = specialist_request()
    result = await specialist.analyze(request)
    assert result.identity == request.identity
    assert result.specialist == request.specialist
    assert result.facts["global_state_owned"] is False
    assert "Material risk" in result.summary
    assert len(calls) == (1 if runtime == "agno" else 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime", ["agno", "crewai"])
@pytest.mark.parametrize("failure", ["transport", "denied", "partial", "truncated", "empty"])
async def test_specialist_failures_are_not_retried_or_reported_as_success(
    runtime: str, failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNO_TELEMETRY", "false")
    monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "true")
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "false")
    calls: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if failure == "transport":
            raise httpx.ConnectError("raw private error", request=request)
        if failure == "denied":
            return httpx.Response(
                403, json={"detail": {"code": "policy_denied", "debug": "raw private error"}}
            )
        return sse_response(request, outcome=failure)

    gateway = gateway_client(handler)
    specialist = (
        AgnoRiskSpecialist(client=gateway, db_file=str(tmp_path / "agno.db"))
        if runtime == "agno"
        else CrewAIRiskSpecialist(client=gateway)
    )
    errors = {
        "transport": GatewayTransportError,
        "denied": GatewayHTTPError,
        "truncated": GatewayProtocolError,
    }
    expected_error = errors.get(failure, TextModelError) if runtime == "crewai" else TextModelError
    with pytest.raises(expected_error) as caught:
        await specialist.analyze(specialist_request())
    assert len(calls) == 1
    assert "raw private error" not in str(caught.value)
    assert "test-gateway-key" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime", ["agno", "crewai"])
@pytest.mark.parametrize("feature", ["media", "tool_history", "tools", "structured"])
async def test_unsupported_features_fail_before_gateway_call(runtime: str, feature: str) -> None:
    calls: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return sse_response(request)

    gateway = gateway_client(handler)
    kwargs: dict[str, Any] = {}
    if runtime == "agno":
        model = AgnoTextModel(gateway)
        messages = [AgnoMessage(role="user", content="hello")]
        if feature == "media":
            messages = [
                AgnoMessage(
                    role="user",
                    content=[{"type": "image_url", "image_url": "https://image.invalid"}],
                )
            ]
        elif feature == "tool_history":
            messages = [AgnoMessage(role="tool", content="tool result", tool_call_id="call-1")]
        elif feature == "tools":
            kwargs = {"tools": [{"type": "function"}]}
        else:
            kwargs = {"response_format": {"type": "json_object"}}
        with pytest.raises(TextModelError):
            await model.ainvoke(messages, **kwargs)
    else:
        crewai_model = CrewAITextLLM(gateway)
        crewai_messages: list[LLMMessage] = [{"role": "user", "content": "hello"}]
        if feature == "media":
            crewai_messages[0]["content"] = [{"type": "image_url"}]
        elif feature == "tool_history":
            crewai_messages = [{"role": "tool", "content": "tool result", "tool_call_id": "call-1"}]
        elif feature == "tools":
            kwargs = {"tools": [{"type": "function"}]}
        else:
            kwargs = {"response_model": object}
        with pytest.raises(TextModelError):
            await crewai_model.acall(crewai_messages, **kwargs)
    assert calls == []


def test_crewai_model_serialization_contains_no_gateway_credential() -> None:
    llm = CrewAITextLLM(gateway_client(lambda request: sse_response(request)))
    assert "test-gateway-key" not in repr(llm)
    assert "test-gateway-key" not in llm.model_dump_json()


@pytest.mark.asyncio
async def test_gateway_call_closes_transport() -> None:
    class ClosingTransport(httpx.MockTransport):
        closed = False

        async def aclose(self) -> None:
            self.closed = True

    transport = ClosingTransport(lambda request: sse_response(request))
    gateway = gateway_client(lambda request: sse_response(request))
    gateway = GatewayTextClient(gateway.config, transport=transport)
    await gateway.generate((text_message("user", "hello"),))
    assert transport.closed is True
