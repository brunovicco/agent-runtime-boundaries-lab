# ADR 0004 — Model access goes through Governed LLM Gateway

- Status: Accepted
- Date: 2026-09-15
- Amended: 2026-09-16 by [ADR 0006](0006-native-gateway-sdk.md).
- Direct OpenAI exception: 2026-09-16 by [ADR 0007](0007-optional-direct-openai.md).

## Decision

Specialist frameworks access Governed LLM Gateway instead of provider SDKs or provider API keys.
Both the Agno and CrewAI experiments now use the native SDK as specified in ADR 0006.

## Consequences

- Provider credentials stay outside the agent runtime.
- Provider selection and fallback policy stay centralized.
- The specialist remains focused on its bounded role.
- Gateway SDK compatibility must be verified for the framework features enabled by each specialist service.
