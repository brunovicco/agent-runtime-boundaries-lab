# ADR 0008 — Effect ledger records a pending reservation before delegating

- Status: Accepted
- Date: 2026-09-16
- Amends: [ADR 0003](0003-separate-effect-ledger.md)

## Context

The delegation sequence was "check ledger → call specialist → complete ledger". If the process
crashed between the specialist call returning and the ledger write, there was no durable record
that an attempt had ever been made. A retry saw a plain cache miss and delegated again with no
forensic trail of the earlier attempt.

## Decision

`EffectLedger` gains a third operation, `reserve(key) -> bool`, called before the specialist is
invoked. It durably records a `pending` row for the idempotency key. `complete(key, payload)` now
promotes `pending` to `completed`; a `completed` row is never overwritten. The
`agent_effect_ledger` table adds a `status` column and makes `payload` nullable while pending.

The duplicated "check ledger → delegate → complete" policy in `langgraph_runtime.py::delegate` and
`entrypoints/demo.py::execute_once` is consolidated into one framework-neutral
`application/service.py::execute_delegation` helper.

## Consequences

- The crash window becomes durable and auditable: a `pending` row without a matching `completed`
  row is visible evidence that an attempt was made and its remote outcome is unknown.
- This is **not** exactly-once delegation. A retry after such a crash still invokes the specialist
  again — the ledger cannot know whether the earlier remote call actually succeeded. At-least-once
  remains the guarantee, proven by
  `tests/integration/test_postgres_resume.py::test_crash_before_ledger_complete_reattempts_specialist_on_retry`.
- The `agent_effect_ledger` schema changes in a backward-incompatible way. There is no migration;
  an existing local table (from before this change) must be dropped and recreated.
