# ADR 0001 — LangGraph owns the global workflow

- Status: Accepted
- Date: 2026-09-15

## Context

The application intentionally uses both LangGraph and Agno. Both can persist execution-related state.
Allowing both to define global progress would require reconciliation after partial failures.

## Decision

LangGraph is the authoritative workflow runtime. Its `thread_id` is derived from the application's
canonical `conversation_id`. Agno is used only behind the specialist boundary.

## Consequences

- Global workflow phase is inspectable in one place.
- Agno remains replaceable.
- Specialist-local state may diverge without redefining workflow progress.
- The orchestrator must own an explicit remote-call retry/idempotency policy.
