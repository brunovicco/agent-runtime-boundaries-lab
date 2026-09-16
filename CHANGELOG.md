# Changelog

## Unreleased

- Added explicit `LLM_BACKEND=openai` with `OPENAI_API_KEY` for Agno and CrewAI, shared text bridges,
  credential-free Responses API contracts and ADR 0007. Gateway remains the default, without
  automatic backend fallback. Added direct-mode configuration and real-inference commands.
- Aligned Agno and CrewAI model access with Governed LLM Gateway SDK/contracts 1.1.0 at the current
  inspected commit, using native `/v1/generate` rather than assumed OpenAI ingress options.
- Replaced model-alias configuration with authorized workload intent and explicit risk/classification.
- Disabled framework inference retries and rejected failed/partial/empty output and unsupported features.
- Added credential-free SDK/SSE contracts through both frameworks, a dependency lock and ADR 0006.
- Corrected pre-existing lint/docstring issues to run the complete quality gate.

## 0.2.0 - 2026-09-15

- Added CrewAI as a third comparative specialist experiment.
- Added a two-role CrewAI Crew behind the same A2A / `SpecialistPort` boundary.
- Added a LangGraph + CrewAI Flow dual-ownership anti-pattern simulation.
- Added comparative experiments documentation and ADR 0005.
- Narrowed Python support to 3.13 because CrewAI 1.15.21 currently requires Python <3.14.

## 0.1.0 - 2026-09-15

- Initial reference architecture.
- LangGraph as the authoritative global workflow runtime.
- Agno as a specialist-local agent runtime.
- Canonical execution identities and framework-neutral contracts.
- Separate replay/effect ledger.
- A2A message boundary with a2a-otel-kit W3C trace propagation.
- Governed LLM Gateway as the model/provider boundary.
- Credential-free deterministic demo and PostgreSQL crash/retry integration proof.
