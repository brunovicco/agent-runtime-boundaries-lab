# Engineering harness baseline

This repository follows the **service** shape and engineering constraints of
`brunovicco/codex-python-engineering-harness` rather than copying framework code into the lab.

Baseline inspected while this lab was created:

- repository: `brunovicco/codex-python-engineering-harness`
- commit: `e9e297456573d216f070a41a7cdaa108dd599c5b`
- release commit message identifies the baseline as `1.3.0`
- profile intent: deployable service with `src/`, container/runtime boundaries, typed configuration,
  tests, architecture checks and a single quality entry point

Equivalent bootstrap intent for a fresh empty directory is:

```bash
python /path/to/codex-python-engineering-harness/bootstrap.py \
  --name agent-runtime-boundaries-lab \
  --package agent_runtime_boundaries \
  --target /path/to/agent-runtime-boundaries-lab \
  --profile service \
  --governance-profile agentic
```

The domain-specific files in this lab then replace/extend the generated placeholders. The repository
keeps the same broad discipline: `src/` layout, strict typing, Pydantic settings, credential-free core
tests, Ruff/Mypy/Pytest, an architecture guard, ADRs, CI and explicit runtime boundaries.

## Why the harness is not vendored

The harness is a repository generator and policy baseline, not a runtime dependency. Vendoring it
would couple this example to generator internals and make upgrades harder. The source commit above is
recorded so the initial engineering assumptions are reproducible.
