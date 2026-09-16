# Validation

## Real gateway inference with OTEL — 2026-09-16

- Real LangGraph → A2A → Agno → Governed LLM Gateway inference: **passed**, using synthetic
  merchant evidence, risk `high`, classification `public` and `OTEL_ENABLED=true` in both lab processes.
- First execution: HTTP **200**, phase **completed**, `specialist_reused=false`, **6.544756 s**.
- Repetition with identical IDs: HTTP **200**, phase **completed**, `specialist_reused=true`,
  **0.084811 s**, summary identical to the first result.
- Collector → Tempo export: **passed**. Grafana Explore displayed the same trace successfully.
- Trace `553921e6193daaaa264e37d077dba594`: **2 services, 2 spans** with matching trace IDs;
  `specialist.handle` references `specialist.delegate` as its parent.
- Span attributes: **metadata only** (`operation`), without prompts, A2A bodies, credentials or payloads.
- Screenshots captured from the real-response evidence report and Grafana and included in both READMEs.
- Normalized trace/request/results archived in [`docs/evidence/otel-live-run.json`](docs/evidence/otel-live-run.json).

This run used temporary lab ports 8201/8203, preserving existing services on 8101/8003. The trace
covers the A2A delegation boundary; it contains no gateway/provider or whole-workflow spans.
These timings describe one local run and do not establish a performance benchmark or exactly-once
provider inference before the effect ledger records the completed result.

## Optional direct OpenAI — 2026-09-16

- Complete `uv run python scripts/quality_gate.py`: **passed** (offline cached dependencies).
- Unit/contract suite: **110 passed**, with **93.71%** coverage against the **80%** minimum.
- Ruff lint/format, strict Mypy and architecture guard: **passed**.
- Real OpenAI SDK Responses calls through actual Agno Agent and CrewAI Crew with mock HTTP:
  **passed**, preserving canonical identity and specialist-local ownership.
- Gateway default, independent backend configuration, credential redaction, fixed OpenAI destination,
  stateless request shape and HTTP transport closure: **passed**.
- Transport/timeout, 401/429/500, redirects, invalid JSON/schema, failed/incomplete/empty responses,
  refusals and unexpected tool output: **passed**, with one request on failure and no fallback.
- `uv lock --check`: **passed**. Explicit OpenAI dependency added to the existing lock.
- **42** documented shell examples passed `bash -n`; local runbook/ADR/README links resolve.
- Real `.env` remains `0600`, selects gateway and has an empty optional `OPENAI_API_KEY`.

Live direct OpenAI inference requires the user's key and was not part of these credential-free tests.
Upstream CrewAI deprecation and SQLite resource warnings remain visible and do not fail the gate.
The direct-mode runbook documents service startup, paid inference and ledger reuse with stable IDs.

## Gateway 1.1.0 alignment — 2026-09-16

Validated against gateway commit `7d7e2e3840719acd257b1c25c19f8ce4a84592d8`:

- Dependency resolution and `uv sync --all-groups`: **passed**, with Python 3.13.15,
  Agno 3.0.9, CrewAI 1.15.21 and gateway SDK/contracts 1.1.0. `uv.lock` is included.
- Complete `uv run python scripts/quality_gate.py`: **passed**.
- Credential-free unit/contract suite: **57 passed**, no skips.
- Coverage, including the new gateway bridges and specialist adapters: **91.30%** against **80%**.
- Ruff lint/format, strict Mypy and architecture guard: **passed**.
- Native SDK/SSE execution through real Agno Agent and CrewAI Crew: **passed** with mock HTTP.
- Denial, transport failure, partial output, missing SSE terminal event, empty output and unsupported
  features: **passed**, with no local inference retry and no completed specialist result on failure.
- Gateway credential protection and SDK transport closure: **passed**.

The suite reports upstream CrewAI deprecation warnings and SQLite resource warnings. These do not
fail the gate. This validation does not establish live provider inference or PostgreSQL recovery.
Those remain explicit opt-in integration checks requiring the relevant running services and profile.

## Original artifact validation — 2026-09-15

Validation performed in the artifact-generation environment on 2026-09-15:

- Python syntax compilation: **passed** for `src/`, `tests/`, `scripts/` and `examples/`.
- Architecture import guard: **passed**.
- Credential-free unit/contract suite: **15 passed, 2 skipped** locally; the CrewAI construction contract runs in CI after dependency sync.
- Deterministic-core coverage: **100%** against an **80%** minimum.
- Agno dual-ownership failure demonstration: **passed** (divergence reproduced).
- CrewAI Flow dual-ownership simulation: **passed** (divergence reproduced).
- Replay demonstration: **passed** (`specialist_calls` remains `1` on retry).

Not executed during the original artifact generation:

- Dependency resolution / `uv lock`: outbound package-network access was disabled and
  `a2a-otel-kit` is not present in the local uv cache.
- PostgreSQL integration job: the test and GitHub Actions service job are included, but no Docker
  daemon/runtime proof was available here.
- Full Agno -> Governed LLM Gateway -> provider inference: requires a configured external gateway
  profile and model path.
- Full CrewAI -> Governed LLM Gateway -> provider inference: requires CrewAI dependencies plus the
  same configured gateway profile and model path.

Before publishing a release from a normal development environment:

```bash
uv lock
uv sync --all-groups
make quality
docker compose up -d postgres
make integration
```
