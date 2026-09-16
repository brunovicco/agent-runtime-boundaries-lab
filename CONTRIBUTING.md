# Contributing

Keep changes aligned with the repository's purpose: make cross-runtime ownership explicit rather
than hiding it behind framework-specific convenience APIs.

Before opening a pull request:

```bash
uv sync --all-groups
make quality
```

If PostgreSQL is available, also run:

```bash
docker compose up -d postgres
make integration
```

Changes to state ownership, identity mapping, replay semantics, remote contracts or model-governance
boundaries require an ADR under `docs/adr/`.
