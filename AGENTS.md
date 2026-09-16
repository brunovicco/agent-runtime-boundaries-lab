# AGENTS.md

## Mission

Keep this repository a readable reference architecture for cross-runtime agent state boundaries.
Correctness of ownership, retries and contracts matters more than framework cleverness.

## Non-negotiable architecture rules

1. The domain and application packages must not import LangGraph, Agno, CrewAI, A2A SDK or FastAPI.
2. LangGraph is the only owner of global workflow phase/checkpoint progression.
3. Agno and CrewAI state are specialist-local. Never use Agno `session_state` or a CrewAI Flow as canonical state while LangGraph owns the same workflow.
4. Cross-process messages must use the canonical contracts under `domain/contracts.py`.
5. Every remote delegation must have a stable `delegation_id` and idempotency key.
6. Any externally visible side effect must be recorded in the effect ledger before replay can occur.
7. Do not put prompts, message bodies, credentials or raw business payloads into telemetry attributes.
8. Gateway is the default inference backend and keeps provider credentials behind Governed LLM
   Gateway. Explicit `LLM_BACKEND=openai` may receive `OPENAI_API_KEY` in specialist secret
   configuration (ADR 0007). Never hardcode or serialize credentials, or fall back between backends.
9. Unit tests must run without external infrastructure or model credentials.
10. Changes to ownership boundaries require an ADR.
11. CrewAI Crews may coordinate specialist roles; they must return framework-neutral contracts and may not change the global workflow phase.

## Quality gate

```bash
uv run python scripts/quality_gate.py
```

The quality gate runs formatting/linting, typing, tests and architecture checks.
