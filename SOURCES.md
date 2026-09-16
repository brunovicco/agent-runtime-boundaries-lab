# Source references

Primary projects inspected for this implementation:

| Project | Baseline inspected | How the lab uses it |
| --- | --- | --- |
| `brunovicco/codex-python-engineering-harness` | `e9e297456573d216f070a41a7cdaa108dd599c5b` | service-repository engineering baseline |
| `brunovicco/a2a-otel-kit` | `ccd3afc4a00dc089557c9fc51d09cf0962a5473f` | OTLP/W3C observability lifecycle and A2A-oriented trace boundary |
| `brunovicco/governed-llm-gateway` | `7d7e2e3840719acd257b1c25c19f8ce4a84592d8` (1.1.0) | native async client/contracts / governed SSE execution boundary |
| `crewAIInc/crewAI` | `66ef97c73e5459059274c5117e48e2e5ba50a871` | Crew/role-task comparison and current 1.15.21 API surface |

Repository URLs:

- https://github.com/brunovicco/codex-python-engineering-harness
- https://github.com/brunovicco/a2a-otel-kit
- https://github.com/brunovicco/governed-llm-gateway
- https://github.com/crewAIInc/crewAI

Framework documentation consulted for the September 2026 baseline:

- LangGraph persistence/checkpointing: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph PostgreSQL checkpointer: https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-postgres
- Agno sessions: https://docs.agno.com/sessions/overview
- Agno session state: https://docs.agno.com/state/agent/overview
- Agno model interface: https://docs.agno.com/reference/models/model
- CrewAI custom LLM interface: https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/llms/base_llm.py
- A2A protocol: https://a2a-protocol.org/latest/
- CrewAI concepts (Crews vs. Flows): https://docs.crewai.com/core-concepts/Agents
- CrewAI documentation index: https://docs.crewai.com/
- CrewAI package baseline: https://pypi.org/project/crewai/1.15.21/
- OpenAI Responses API (Python): https://developers.openai.com/api/reference/python/resources/responses/methods/create
- Direct-mode default model: https://developers.openai.com/api/docs/models/gpt-4.1-mini

The real SDK/native SSE integration is tested without credentials through both frameworks.
Full-stack provider proof remains opt-in because it requires a running Gateway profile and PostgreSQL.
CrewAI 1.15.21 requires Python >=3.10,<3.14, so
this repository deliberately targets Python 3.13. Credential-free tests prove the application-owned
identity and idempotency invariants without pretending to prove external services.
