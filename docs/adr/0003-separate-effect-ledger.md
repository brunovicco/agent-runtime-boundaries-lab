# ADR 0003 — Separate effect ledger from checkpoints

- Status: Accepted
- Date: 2026-09-15

## Decision

Remote delegations and irreversible effects use a durable idempotency ledger separate from LangGraph
checkpoints.

## Rationale

A checkpoint answers "where was the workflow?". The ledger answers "did this operation already
complete, and with what result?". Conflating the two makes crash recovery ambiguous.
