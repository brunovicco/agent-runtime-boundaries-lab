"""Explicit backend selection must not leak secrets or require the other backend."""

from __future__ import annotations

import os
from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from agent_runtime_boundaries.adapters.gateway_text import GatewayTextClient
from agent_runtime_boundaries.adapters.openai_text import OpenAITextClient, OpenAITextConfig
from agent_runtime_boundaries.config import Settings


@pytest.fixture(autouse=True)
def clear_backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(("OPENAI_", "GOVERNED_LLM_GATEWAY_")) or name == "LLM_BACKEND":
            monkeypatch.delenv(name)


def test_openai_mode_reads_environment_without_gateway_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_MAX_OUTPUT_TOKENS", "256")
    monkeypatch.setenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "15")
    settings = Settings()
    client = settings.text_client()
    assert isinstance(client, OpenAITextClient)
    assert client.backend == "openai"
    assert client.model_id == "test-model"
    assert client.config.max_output_tokens == 256
    assert client.config.request_timeout_seconds == 15
    assert settings.governed_llm_gateway_api_key.get_secret_value() == ""
    assert "test-openai-key" not in repr(settings)
    assert "test-openai-key" not in settings.model_dump_json()
    assert "test-openai-key" not in repr(client.config)


def test_gateway_is_default_even_when_openai_key_is_present() -> None:
    settings = Settings(openai_api_key=SecretStr("test-openai-key"))
    assert settings.llm_backend == "gateway"
    with pytest.raises(ValueError, match="GOVERNED_LLM_GATEWAY_API_KEY"):
        settings.text_client()


def test_gateway_selection_ignores_missing_openai_key() -> None:
    settings = Settings(
        governed_llm_gateway_api_key=SecretStr("test-gateway-key"),
        governed_llm_gateway_risk_level="high",
        governed_llm_gateway_data_classification="internal",
    )
    client = settings.text_client()
    assert isinstance(client, GatewayTextClient)
    assert client.backend == "gateway"
    assert client.model_id == "agent.orchestration"


@pytest.mark.parametrize("api_key", ["", " ", "replace-me"])
def test_openai_selection_does_not_fall_back_to_configured_gateway(api_key: str) -> None:
    settings = Settings(
        llm_backend="openai",
        openai_api_key=SecretStr(api_key),
        governed_llm_gateway_api_key=SecretStr("test-gateway-key"),
        governed_llm_gateway_risk_level="high",
        governed_llm_gateway_data_classification="internal",
    )
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        settings.text_client()


@pytest.mark.parametrize("model", ["", " ", " test-model "])
def test_invalid_openai_model_fails_before_transport(model: str) -> None:
    with pytest.raises(ValueError, match="OPENAI_MODEL"):
        Settings(
            llm_backend="openai", openai_api_key=SecretStr("test-openai-key"), openai_model=model
        ).text_client()


@pytest.mark.parametrize(
    "overrides",
    [
        {"llm_backend": "auto"},
        {"openai_max_output_tokens": 15},
        {"openai_request_timeout_seconds": 0},
        {"openai_request_timeout_seconds": 301},
    ],
)
def test_invalid_backend_or_openai_limits_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(overrides)


@pytest.mark.parametrize(
    "overrides",
    [{"max_output_tokens": 15}, {"request_timeout_seconds": 0}, {"request_timeout_seconds": 301}],
)
def test_direct_adapter_configuration_enforces_limits(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        OpenAITextConfig(api_key=SecretStr("test-openai-key"), **overrides)
