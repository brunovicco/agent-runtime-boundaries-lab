# ADR 0005 — CrewAI is a bounded specialist capability, not a second workflow authority

## Status

Accepted.

## Context

CrewAI provides both Crews for collaborative agent work and Flows for stateful, event-driven
orchestration. This makes it useful for comparison with both the Agno specialist model and the
LangGraph orchestration model.

The lab already defines LangGraph as the single global workflow authority. Allowing a CrewAI Flow to
persist the same workflow phase would reintroduce dual ownership and ambiguous crash recovery.

## Decision

Add CrewAI as a third comparative experiment using a **Crew** behind the existing `SpecialistPort`
and A2A boundary.

- The Crew may coordinate specialist roles and tasks.
- The Crew may not write global workflow phase.
- The application keeps canonical IDs and idempotency keys.
- The application effect ledger remains authoritative for completed remote effects.
- Governed LLM Gateway remains authoritative for model/provider execution policy.
- CrewAI Flow is demonstrated only as an ownership anti-pattern when paired with authoritative
  LangGraph state for the same business workflow.

## Consequences

The same orchestration can swap Agno for CrewAI without changing domain contracts. The repository
also demonstrates that the ownership principle is framework-independent rather than an Agno-specific
workaround.
