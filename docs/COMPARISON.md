# What we take from each framework — and what we deliberately do not take

The purpose of a hybrid architecture is to compose **capabilities**, not duplicate authorities.

| Concern | Selected capability | Owner in this lab | Deliberately not shared |
| --- | --- | --- | --- |
| durable workflow / resume | LangGraph checkpoints | LangGraph | specialists do not set global phase |
| specialist reasoning | Agno Agent | Agno service | Agno does not own workflow resume |
| specialist-local continuity | Agno `session_id` + DB | Agno | not canonical workflow state |
| role/task collaboration | CrewAI Crew | CrewAI service | no CrewAI Flow owns the same global workflow |
| model/provider execution | Gateway by default, optional direct OpenAI | Gateway or explicitly selected specialist backend | no implicit fallback; keys stay outside serializable framework state |
| agent-to-agent boundary | A2A | protocol adapter | A2A is not a state database |
| distributed tracing | a2a-otel-kit + W3C context | telemetry layer | `trace_id` is not business identity |
| replay protection | effect ledger | application/Postgres | not inferred from framework memory/history |

## LangGraph vs. Agno vs. CrewAI in this lab

| Dimension | LangGraph | Agno | CrewAI |
| --- | --- | --- | --- |
| abstraction used here | stateful graph | bounded Agent | bounded Crew |
| responsibility | global orchestration | specialist reasoning/session | role/task collaboration |
| persistent global state | yes | no | no |
| specialist-local state | n/a | allowed | disabled in comparison experiment |
| canonical replay authority | application ledger | no | no |
| can replace another specialist without domain changes | n/a | yes | yes |
| Flow/workflow capability intentionally used as global owner | yes | no | no |

CrewAI also provides **Flows**, which can manage state transitions and resumable workflows. That is
not a limitation; it is exactly why ownership must be explicit. In this repository LangGraph already
owns that responsibility, so the CrewAI experiment uses a Crew rather than mirroring the same state
machine in a Flow.

## The hidden cost of “best of each”

Adding another runtime can introduce another session model, run model, persistence lifecycle, retry
policy, streaming lifecycle, exception hierarchy and reconstruction algorithm. This is not a reason
to avoid composition. It is a reason to make the boundary explicit and testable.

A practical test is:

> If two frameworks disagree about the same global fact after a crash, which one wins without a
> reconciliation job?

If the answer is ambiguous, the architecture still has two owners.
