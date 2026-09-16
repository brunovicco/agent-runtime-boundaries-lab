# ADR 0007 — Optional direct OpenAI backend

- Status: Accepted
- Date: 2026-09-16
- Amends: [ADR 0004](0004-governed-model-boundary.md) and [ADR 0006](0006-native-gateway-sdk.md)

## Context

Users may want to run the agent boundary experiments with their own OpenAI key without deploying
Governed LLM Gateway and its PDP. The user explicitly requested this option. The gateway-only
credential rule therefore needs a narrow exception rather than an implicit fallback.

## Decision

- Select `LLM_BACKEND=gateway|openai` in specialist environment configuration. Default to `gateway`.
- In gateway mode, preserve native SDK 1.1.0 workload/risk/classification and gateway-owned routing,
  authentication and inference resilience. An OpenAI key cannot activate or rescue this mode.
- In direct mode, require `OPENAI_API_KEY`; use `OPENAI_MODEL` (default `gpt-4.1-mini`),
  `OPENAI_MAX_OUTPUT_TOKENS` and `OPENAI_REQUEST_TIMEOUT_SECONDS`. No gateway credential or policy
  context is required. The specialist now selects the model and holds the provider credential.
- Use one framework-neutral text client interface behind Agno `Model` and CrewAI `BaseLLM` bridges.
  Gateway contracts are translated only inside the gateway adapter. Domain/application contracts
  do not acquire any provider/framework imports.
- Use the official OpenAI Python SDK's Responses API at the fixed HTTPS OpenAI endpoint, with
  `store=false`, no provider conversation/continuation identifiers, no tools and no SDK retries.
  Close each call's HTTP client, including calls from CrewAI's worker thread. Ignore endpoint/proxy
  environment overrides and reject redirects.
- Keep provider keys in `SecretStr` configuration and private bridge state. Do not add keys or raw
  content to framework serialization, HTTP metadata or telemetry.
- Retain text-only feature restrictions and fail on transport/API errors, invalid responses,
  incomplete/empty output, refusals and unexpected tool output. Discard reasoning items; do not
  persist or resend them as provider state. Never fall back between inference backends.

## Ownership and replay

Model execution responsibility changes only when direct mode is explicitly selected: gateway/PDP
policy, routing, audit and retry/fallback controls are absent. The specialist performs one provider
request per model call. CrewAI still has two sequential model calls for its two tasks.

LangGraph remains the sole workflow phase/checkpoint owner. A2A identity/contracts and the separate
effect ledger retain the same behavior. Backend selection is not part of the delegation identity:
repeating completed IDs reuses the stored result even after switching backend/model. Use new
conversation/execution/delegation IDs to compare actual inference. The pre-ledger crash window
remains; this option does not promise provider inference idempotency.

## Validation

Credential-free tests execute the real OpenAI SDK through actual Agno Agent and CrewAI Crew using
mock HTTP. They check request shape, identity, secret isolation, fixed destination, transport closure,
unsupported features and failure handling with no extra inference request. Settings tests verify
independent backend configuration, the gateway default and rejection of implicit fallback.

Live OpenAI inference requires the user's key and remains an explicit integration exercise.
See the [Portuguese runbook](../REAL_INFERENCE.pt-BR.md).
