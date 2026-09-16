"""Single local/CI quality entry point."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    """Run one command from the repository root and fail fast."""
    subprocess.run(args, cwd=ROOT, check=True)  # noqa: S603


def main() -> None:
    """Execute deterministic checks first; integration tests remain explicit."""
    run("uv", "run", "ruff", "check", ".")
    run("uv", "run", "ruff", "format", "--check", ".")
    run("uv", "run", "mypy", "src", "tests")
    run(
        "uv",
        "run",
        "pytest",
        "tests/unit",
        "tests/contract",
        "--cov=agent_runtime_boundaries.domain",
        "--cov=agent_runtime_boundaries.application.service",
        "--cov=agent_runtime_boundaries.adapters.memory_ledger",
        "--cov=agent_runtime_boundaries.adapters.fake_specialist",
        "--cov=agent_runtime_boundaries.adapters.gateway_text",
        "--cov=agent_runtime_boundaries.adapters.openai_text",
        "--cov=agent_runtime_boundaries.adapters.text_generation",
        "--cov=agent_runtime_boundaries.config",
        "--cov=agent_runtime_boundaries.adapters.agno_text_model",
        "--cov=agent_runtime_boundaries.adapters.crewai_text_llm",
        "--cov=agent_runtime_boundaries.adapters.agno_specialist",
        "--cov=agent_runtime_boundaries.adapters.crewai_specialist",
        "--cov-report=term-missing",
    )
    run("uv", "run", "python", "scripts/check_architecture.py")


if __name__ == "__main__":
    main()
