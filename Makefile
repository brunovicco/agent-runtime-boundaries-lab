.PHONY: quality test integration demo anti-pattern anti-pattern-crewai agno-specialist crewai-specialist infra-up infra-down

quality:
	uv run python scripts/quality_gate.py

test:
	uv run pytest -m 'not integration'

integration:
	uv run pytest -m integration -q

demo:
	uv run python -m agent_runtime_boundaries.entrypoints.demo

anti-pattern:
	uv run python examples/dual_ownership_failure.py

anti-pattern-crewai:
	uv run python examples/dual_ownership_crewai_failure.py

agno-specialist:
	uv run uvicorn agent_runtime_boundaries.entrypoints.specialist:app --host 0.0.0.0 --port 8101

crewai-specialist:
	uv run uvicorn agent_runtime_boundaries.entrypoints.crewai_specialist:app --host 0.0.0.0 --port 8102

infra-up:
	docker compose up -d postgres otel-collector tempo grafana

infra-down:
	docker compose down -v
