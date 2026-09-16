# Security

This repository is a reference implementation, not production infrastructure.

- Do not commit provider keys or gateway credentials.
- In default `LLM_BACKEND=gateway` mode, the specialist receives only a gateway consumer credential.
  Opt-in `LLM_BACKEND=openai` accepts a provider key through `OPENAI_API_KEY` in secret configuration
  and calls the official OpenAI endpoint directly. This mode has no gateway/PDP authorization,
  routing, audit or resilience controls. Selection is explicit and never a failure fallback.
- Keep either credential outside serializable framework fields and telemetry. The direct adapter
  uses `store=false`, does not use provider conversation state, disables SDK retries and rejects
  redirects. `OPENAI_BASE_URL` and proxy environment variables do not change its destination.
- Telemetry must remain metadata-only. Do not add prompts, message bodies, credentials or raw business
  payloads to span attributes or structured events.
- A2A endpoints in this lab do not implement production authentication, TLS termination, rate limiting
  or tenant authorization. Put those controls in front of any real deployment.
- PostgreSQL credentials in `.env.example` and `docker-compose.yml` are local-demo credentials only.
