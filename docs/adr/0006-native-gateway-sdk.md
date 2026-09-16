# ADR 0006 — Specialist models use the native gateway SDK

- Status: Accepted
- Date: 2026-09-16
- Amends: [ADR 0004](0004-governed-model-boundary.md)
- Optional direct backend: [ADR 0007](0007-optional-direct-openai.md)

## Context

The current gateway checkout is version 1.1.0 at
`7d7e2e3840719acd257b1c25c19f8ce4a84592d8`. Its thin asynchronous `GatewayClient`
aggregates validated SSE from `POST /v1/generate` into a provider-neutral `GatewayResponse`.
The native contract requires workload, risk level and data classification. Authentication uses
`X-Gateway-API-Key`; the server reconciles caller declarations with its authenticated client binding.

The previous lab used Agno `OpenAILike` and CrewAI `LLM` with an assumed model alias and `/v1`
base URL. The gateway's current `/v1/chat/completions` ingress is text-only, interprets `model`
as a workload, and rejects unknown fields, including the lab's CrewAI `temperature=0`.
Its risk/classification minimums come from the authenticated binding rather than per-request input.
Provider SDK and framework retry defaults can also replay a failed governed generation.

## Decision

- Depend only on the gateway's `client` and `contracts` packages, pinned to the inspected commit.
- Translate Agno `Model` and CrewAI `BaseLLM` text messages through one adapter using `GatewayClient`.
- Configure the gateway base URL without `/v1`, an authorized workload (default intent:
  `agent.orchestration`), explicit risk/classification, and bounded output/timeout settings.
- Open and close an SDK client for each model call. CrewAI's synchronous call runs the async SDK
  in its existing worker thread; no HTTP pool is shared between event loops.
- Disable Agno model/run retries, guidance retries and CrewAI agent retries. Neither adapter
  selects a provider/model/deployment or performs fallback.
- Reject tool histories, media, structured output and framework streaming before inference.
  The SDK uses streaming internally even when a framework receives one complete text result.
- Fail on rejected/failed generations, including partial output, and on empty successful output.
  Never convert those failures into a completed specialist response.
- Keep gateway credentials in secret configuration/private bridge state, outside serializable
  framework model fields. Disable Agno telemetry and CrewAI content tracing/sharing;
  application observability remains with a2a-otel-kit. Add no prompt/payload telemetry.

## Ownership and replay

LangGraph still owns global phase/checkpoints. Specialist state stays local. A2A messages still use
`domain/contracts.py` and retain canonical delegation identity/idempotency keys. The application
effect ledger still records completed specialist responses before workflow replay.

Gateway request UUIDs correlate SDK requests and SSE; they do not grant inference idempotency.
This change does not close the existing crash window before a specialist result reaches the ledger.
Retry/fallback inside an individual inference remains gateway-owned.

## Validation and limits

Credential-free contracts exercise the real SDK's SSE parser with `httpx.MockTransport` through
actual Agno Agent and CrewAI Crew execution. They verify request shape, identity preservation,
policy denial, transport failure, partial/empty output, malformed lifecycle, absence of local replay,
unsupported-feature rejection and transport closure.

Live provider inference and PostgreSQL recovery remain opt-in integration proofs. Tool and
multimodal capabilities present in the gateway do not imply support in these bounded lab adapters.
