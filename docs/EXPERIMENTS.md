# Comparative experiments

This repository is intentionally a **runtime-boundary lab**, not a benchmark claiming one framework
is universally better. The experiments hold the application-owned identity and replay rules constant
and vary the specialist runtime behind the same `SpecialistPort` / A2A contract.

## Experiment 1 — LangGraph + framework-neutral deterministic specialist

Purpose: prove the core ownership and replay invariants without any model, agent framework, network
service, or credentials.

```bash
make demo
```

What it isolates:

- LangGraph owns global workflow phase and checkpoint progression.
- The application owns canonical IDs and the effect ledger.
- A retry after a completed specialist effect does not invoke that effect twice.

This is the control experiment. If the invariant cannot be proved here, adding another agent runtime
only makes the failure harder to diagnose.

## Experiment 2 — LangGraph + Agno specialist

Purpose: show a framework with useful **agent/session continuity** operating as a bounded specialist.

```text
LangGraph thread_id      <- conversation_id
Agno session_id          <- conversation_id
Agno run_id              <- delegation_id
```

Agno may keep specialist-local session state, but its contract cannot change the global workflow
phase. The orchestration boundary remains A2A. Model execution uses Governed LLM Gateway by default,
or the explicit direct OpenAI backend.

Run the Agno service on port 8101 and point `SPECIALIST_A2A_URL` at it.

## Experiment 3 — LangGraph + CrewAI Crew specialist

Purpose: show a **role/task-oriented team of specialists** without introducing a second global
workflow owner.

The CrewAI implementation creates two bounded roles for each canonical delegation:

```text
Risk Analyst
    -> Compliance Reviewer
    -> SpecialistResponse
```

The `Crew` uses `Process.sequential`, with memory and cache disabled in this experiment. It receives
the same `SpecialistRequest` and returns the same `SpecialistResponse` as the Agno implementation.
It does not own approval state, workflow phase, replay or external business side effects. In gateway
mode, model routing is gateway-owned; direct OpenAI uses the specialist's configured model.

Start it on port 8102:

```bash
set -a; source .env; set +a
uv run uvicorn agent_runtime_boundaries.entrypoints.crewai_specialist:app \
  --host 0.0.0.0 --port 8102
```

Then point the unchanged LangGraph orchestrator at it:

```bash
export SPECIALIST_A2A_URL=http://127.0.0.1:8102/a2a
uv run uvicorn agent_runtime_boundaries.entrypoints.api:app \
  --host 0.0.0.0 --port 8000
```

By default, CrewAI uses a custom `BaseLLM` bridge over `GatewayClient.generate()`. The bridge declares a
workload and explicit risk/data classification and accepts text messages only. Each model call closes
its SDK client. Agent retries are disabled; provider selection and inference resilience remain behind
Governed LLM Gateway. See [ADR 0006](adr/0006-native-gateway-sdk.md).

For either framework, `LLM_BACKEND=openai` instead selects the direct Responses API adapter with
`OPENAI_API_KEY` and `OPENAI_MODEL`. Gateway/PDP services are not required. SDK/framework retries
and backend fallback remain disabled; policy/audit/routing controls from the gateway are absent.
Use new IDs when changing backend/model so the ledger does not reuse an earlier completed result.
See [ADR 0007](adr/0007-optional-direct-openai.md) and the
[live inference runbook](REAL_INFERENCE.pt-BR.md#alternativa-sem-gateway-openai-direto).

## Anti-pattern — LangGraph + CrewAI Flow both own the workflow

CrewAI Flows are capable of stateful, event-driven orchestration. That is exactly why combining a
Flow with LangGraph requires an explicit authority decision.

```bash
make anti-pattern-crewai
```

The simulation intentionally crashes after LangGraph advances the global phase but before a second
CrewAI Flow state write. The two runtimes now disagree about the same business fact.

The lesson is not “do not use CrewAI Flows.” It is:

> If CrewAI Flow is the authoritative workflow runtime, let it own that responsibility. If LangGraph
> is authoritative, use CrewAI behind a capability boundary instead of mirroring the same state
> machine in both frameworks.

## What is deliberately held constant

| Concern | Experiment 1 | Experiment 2: Agno | Experiment 3: CrewAI |
| --- | --- | --- | --- |
| global workflow owner | LangGraph | LangGraph | LangGraph |
| canonical IDs | application | application | application |
| replay/effect ledger | application | application | application |
| specialist boundary | in-process port | A2A | A2A |
| specialist abstraction | fake capability | Agno Agent | CrewAI Crew |
| specialist local state | none | Agno session DB | disabled for isolation |
| model execution | none | gateway or explicit direct OpenAI | gateway or explicit direct OpenAI |
| provider selection | none | gateway policy or direct model config | gateway policy or direct model config |
| global phase writable by specialist | no | no | no |

This makes the comparison architectural rather than cosmetic: the external contract remains stable
while the internal specialist model changes.
