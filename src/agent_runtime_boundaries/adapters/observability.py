"""a2a-otel-kit observability bootstrap."""

from __future__ import annotations

from a2a_otel_kit import Observability, ObservabilitySettings


def configure_observability(
    *,
    service_name: str,
    enabled: bool,
    otlp_endpoint: str,
) -> Observability:
    """Configure one process-local observability lifecycle."""
    return Observability.configure(
        ObservabilitySettings(
            service_name=service_name,
            service_version="0.2.0",
            environment="local",
            enabled=enabled,
            otlp_endpoint=otlp_endpoint,
        )
    )
