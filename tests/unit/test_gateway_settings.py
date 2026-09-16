"""Gateway configuration must fail before credentials or inference are used."""

from __future__ import annotations

from typing import Any

import pytest
from governed_llm_gateway_client import GatewayConfigurationError
from governed_llm_gateway_contracts import DataClassification, RiskLevel
from pydantic import SecretStr, ValidationError

from agent_runtime_boundaries.config import Settings


@pytest.fixture(autouse=True)
def clear_gateway_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for name in list(os.environ):
        if name.startswith(("GOVERNED_LLM_GATEWAY_", "OPENAI_")) or name == "LLM_BACKEND":
            monkeypatch.delenv(name)


def test_gateway_settings_read_native_consumer_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOVERNED_LLM_GATEWAY_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv("GOVERNED_LLM_GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setenv("GOVERNED_LLM_GATEWAY_WORKLOAD", "agent.orchestration")
    monkeypatch.setenv("GOVERNED_LLM_GATEWAY_RISK_LEVEL", "high")
    monkeypatch.setenv("GOVERNED_LLM_GATEWAY_DATA_CLASSIFICATION", "confidential")
    settings = Settings()
    config = settings.gateway_text_config()
    assert config.workload == "agent.orchestration"
    assert config.risk_level is RiskLevel.HIGH
    assert config.data_classification is DataClassification.CONFIDENTIAL
    assert config.max_output_tokens == 2000
    assert config.connection.base_url == "http://127.0.0.1:8001"
    assert "test-gateway-key" not in repr(settings)
    assert "test-gateway-key" not in repr(config)
    assert "test-gateway-key" not in settings.model_dump_json()


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"governed_llm_gateway_api_key": SecretStr("")}, "API_KEY"),
        ({"governed_llm_gateway_api_key": SecretStr("replace-me")}, "API_KEY"),
        ({"governed_llm_gateway_risk_level": None}, "RISK_LEVEL"),
        ({"governed_llm_gateway_data_classification": None}, "DATA_CLASSIFICATION"),
        ({"governed_llm_gateway_url": "https://gateway.invalid/v1"}, "without /v1"),
        ({"governed_llm_gateway_workload": "provider/model"}, "WORKLOAD"),
    ],
)
def test_incomplete_or_obsolete_specialist_configuration_fails_closed(
    overrides: dict[str, Any], expected: str
) -> None:
    values = {
        "governed_llm_gateway_api_key": SecretStr("test-gateway-key"),
        "governed_llm_gateway_risk_level": "high",
        "governed_llm_gateway_data_classification": "internal",
        **overrides,
    }
    with pytest.raises(ValueError, match=expected):
        Settings.model_validate(values).gateway_text_config()


@pytest.mark.parametrize(
    "url",
    [
        "http://gateway.invalid",
        "https://user:password@gateway.invalid",
        "https://gateway.invalid?q=1",
    ],
)
def test_gateway_transport_security_is_retained(url: str) -> None:
    settings = Settings(
        governed_llm_gateway_url=url,
        governed_llm_gateway_api_key=SecretStr("test-gateway-key"),
        governed_llm_gateway_risk_level="high",
        governed_llm_gateway_data_classification="internal",
    )
    with pytest.raises(GatewayConfigurationError):
        settings.gateway_text_config()


def test_demo_and_orchestrator_settings_do_not_require_model_credentials() -> None:
    assert Settings().governed_llm_gateway_risk_level is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"governed_llm_gateway_risk_level": "unknown"},
        {"governed_llm_gateway_data_classification": "unknown"},
        {"governed_llm_gateway_max_output_tokens": 0},
        {"governed_llm_gateway_provider_timeout_seconds": 0},
        {"governed_llm_gateway_request_timeout_seconds": 301},
    ],
)
def test_invalid_policy_context_and_limits_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(overrides)
