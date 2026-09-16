"""Real OpenAI SDK requests through both frameworks without credentials or infrastructure."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from agno.models.message import Message as AgnoMessage
from crewai.utilities.types import LLMMessage
from pydantic import SecretStr

from agent_runtime_boundaries.adapters.agno_specialist import AgnoRiskSpecialist
from agent_runtime_boundaries.adapters.agno_text_model import AgnoTextModel
from agent_runtime_boundaries.adapters.crewai_specialist import CrewAIRiskSpecialist
from agent_runtime_boundaries.adapters.crewai_text_llm import CrewAITextLLM
from agent_runtime_boundaries.adapters.openai_text import OpenAITextClient, OpenAITextConfig
from agent_runtime_boundaries.adapters.text_generation import TextModelError, text_message
from agent_runtime_boundaries.domain.contracts import SpecialistRequest
from agent_runtime_boundaries.domain.identity import ExecutionIdentity


def response_payload(*, outcome: str = "success") -> dict[str, Any]:
    message: dict[str, Any] = {
        "type": "message",
        "id": "msg-test",
        "role": "assistant",
        "status": "completed",
        "content": [
            {
                "type": "output_text",
                "text": "Final Answer: Material risk needs review.",
                "annotations": [],
            }
        ],
    }
    payload: dict[str, Any] = {
        "id": "resp-test",
        "created_at": 0,
        "model": "test-model",
        "object": "response",
        "output": [message],
        "parallel_tool_calls": False,
        "tool_choice": "none",
        "tools": [],
        "status": "completed",
        "error": None,
        "incomplete_details": None,
    }
    if outcome == "incomplete":
        payload.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
    elif outcome == "failed":
        payload.update(status="failed", error={"code": "server_error", "message": "private error"})
    elif outcome == "message_incomplete":
        message["status"] = "incomplete"
    elif outcome == "empty":
        payload["output"] = []
    elif outcome == "refusal":
        message["content"] = [{"type": "refusal", "refusal": "private error"}]
    elif outcome == "tool_output":
        payload["output"].append(
            {"type": "function_call", "call_id": "call-test", "name": "tool", "arguments": "{}"}
        )
    elif outcome == "reasoning":
        payload["output"].insert(
            0, {"type": "reasoning", "id": "reason-test", "summary": [], "status": "completed"}
        )
    return payload


def openai_client(handler: Callable[[httpx.Request], httpx.Response]) -> OpenAITextClient:
    return OpenAITextClient(
        OpenAITextConfig(api_key=SecretStr("test-openai-key"), model="test-model"),
        transport=httpx.MockTransport(handler),
    )


def specialist_request() -> SpecialistRequest:
    identity = ExecutionIdentity(
        conversation_id="conversation-openai",
        execution_id="exec:openai",
        delegation_id="deleg:openai",
    )
    return SpecialistRequest(
        identity=identity,
        prompt="Review merchant risk",
        payload={"synthetic": True, "merchant_tier": "growth"},
        idempotency_key=identity.idempotency_key("specialist-risk-review"),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime", ["agno", "crewai"])
async def test_direct_openai_specialists_keep_canonical_identity_and_use_stateless_responses(
    runtime: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "wrong-environment-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://untrusted.invalid/v1")
    monkeypatch.setenv("HTTPS_PROXY", "http://untrusted.invalid:8080")
    monkeypatch.setenv("GOVERNED_LLM_GATEWAY_API_KEY", "test-gateway-key")
    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["authorization"] == "Bearer test-openai-key"
        assert "X-Gateway-API-Key" not in request.headers
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["model"] == "test-model"
        assert payload["max_output_tokens"] == 2000
        assert payload["store"] is False
        assert payload["stream"] is False
        assert payload["input"]
        assert all(item["role"] in {"user", "system", "assistant"} for item in payload["input"])
        assert not {"tools", "conversation", "previous_response_id", "metadata", "temperature"} & (
            payload.keys()
        )
        assert "test-gateway-key" not in request.content.decode()
        return httpx.Response(200, json=response_payload())

    client = openai_client(handler)
    specialist = (
        AgnoRiskSpecialist(client=client, db_file=str(tmp_path / "agno.db"))
        if runtime == "agno"
        else CrewAIRiskSpecialist(client=client)
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
@pytest.mark.parametrize(
    "failure",
    [
        "transport",
        "timeout",
        "unauthorized",
        "rate_limit",
        "server_error",
        "redirect",
        "malformed",
        "invalid_json",
        "null_response",
        "incomplete",
        "failed",
        "message_incomplete",
        "empty",
        "refusal",
        "tool_output",
    ],
)
async def test_direct_openai_failures_never_retry_fall_back_or_return_partial_success(
    runtime: str, failure: str, tmp_path: Path
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "api.openai.com"
        if failure == "transport":
            raise httpx.ConnectError("private error", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private error", request=request)
        status = {"unauthorized": 401, "rate_limit": 429, "server_error": 500}.get(failure)
        if status:
            return httpx.Response(status, json={"error": {"message": "private error"}})
        if failure == "redirect":
            return httpx.Response(307, headers={"location": "https://untrusted.invalid"})
        if failure == "malformed":
            return httpx.Response(200, json={"status": "completed", "debug": "private error"})
        if failure == "invalid_json":
            return httpx.Response(
                200, headers={"content-type": "application/json"}, content="private error"
            )
        if failure == "null_response":
            return httpx.Response(200, headers={"content-type": "application/json"}, content="null")
        return httpx.Response(200, json=response_payload(outcome=failure))

    client = openai_client(handler)
    specialist = (
        AgnoRiskSpecialist(client=client, db_file=str(tmp_path / "agno.db"))
        if runtime == "agno"
        else CrewAIRiskSpecialist(client=client)
    )
    with pytest.raises(TextModelError) as caught:
        await specialist.analyze(specialist_request())
    assert len(calls) == 1
    assert "private error" not in str(caught.value)
    assert "test-openai-key" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("runtime", ["agno", "crewai"])
async def test_direct_backend_rejects_tool_history_before_provider_call(runtime: str) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=response_payload())

    client = openai_client(handler)
    with pytest.raises(TextModelError):
        if runtime == "agno":
            await AgnoTextModel(client).ainvoke(
                [AgnoMessage(role="tool", content="result", tool_call_id="call-test")]
            )
        else:
            messages: list[LLMMessage] = [
                {"role": "tool", "content": "result", "tool_call_id": "call-test"}
            ]
            await CrewAITextLLM(client).acall(messages)
    assert calls == []


def test_framework_serialization_never_contains_provider_key() -> None:
    client = openai_client(lambda request: httpx.Response(200, json=response_payload()))
    agno_model = AgnoTextModel(client)
    crewai_model = CrewAITextLLM(client)
    assert "test-openai-key" not in repr(agno_model)
    assert "test-openai-key" not in json.dumps(agno_model.to_dict())
    assert "test-openai-key" not in repr(crewai_model)
    assert "test-openai-key" not in crewai_model.model_dump_json()


@pytest.mark.asyncio
async def test_direct_call_closes_transport_and_discards_reasoning_state() -> None:
    class ClosingTransport(httpx.MockTransport):
        closed = False

        async def aclose(self) -> None:
            self.closed = True

    transport = ClosingTransport(
        lambda request: httpx.Response(200, json=response_payload(outcome="reasoning"))
    )
    client = OpenAITextClient(
        OpenAITextConfig(api_key=SecretStr("test-openai-key")), transport=transport
    )
    assert "Material risk" in await client.generate((text_message("user", "hello"),))
    assert transport.closed


@pytest.mark.asyncio
async def test_empty_direct_input_fails_before_transport() -> None:
    client = openai_client(lambda request: httpx.Response(200, json=response_payload()))
    with pytest.raises(TextModelError, match="non-empty messages"):
        await client.generate(())
