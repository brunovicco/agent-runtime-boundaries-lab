"""Credential-free illustration of why sequential dual writes split runtime truth."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeState:
    """Tiny stand-in for one framework-owned durable state."""

    phase: str = "received"


def broken_dual_write() -> tuple[RuntimeState, RuntimeState]:
    """Simulate a crash between two framework-owned writes."""
    langgraph = RuntimeState()
    agno = RuntimeState()

    langgraph.phase = "specialist_completed"
    # Process dies here, before the second framework persists the same global fact.
    return langgraph, agno


def single_owner() -> RuntimeState:
    """Keep the global workflow phase in exactly one authority."""
    canonical = RuntimeState()
    canonical.phase = "specialist_completed"
    return canonical


def main() -> None:
    """Print the divergent and single-owner outcomes side by side."""
    langgraph, agno = broken_dual_write()
    print("BROKEN: dual ownership")
    print(f"  LangGraph global phase: {langgraph.phase}")
    print(f"  Agno global phase:      {agno.phase}")
    print(f"  divergent:              {langgraph.phase != agno.phase}")
    print()
    canonical = single_owner()
    print("REFERENCE: one global owner")
    print(f"  canonical phase:        {canonical.phase}")
    print("  Agno keeps specialist-local state only")


if __name__ == "__main__":
    main()
