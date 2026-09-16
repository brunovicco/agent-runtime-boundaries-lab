# ADR 0002 — Application-owned canonical identities

- Status: Accepted
- Date: 2026-09-15

## Decision

The application owns `conversation_id`, `execution_id` and `delegation_id`.

Adapters map them as follows:

- `conversation_id` -> LangGraph `thread_id`
- `conversation_id` -> Agno `session_id`
- `delegation_id` -> Agno `run_id`

Framework-generated identifiers are never the only key used to correlate a business execution.

## Consequences

Logs, traces, checkpoints, retries and cross-runtime requests can be correlated without coupling the
domain model to a framework-specific ID type.
