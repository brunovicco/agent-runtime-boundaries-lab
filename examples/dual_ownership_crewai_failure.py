"""Credential-free simulation of LangGraph + CrewAI Flow competing for global state."""

from dataclasses import dataclass


@dataclass
class RuntimeState:
    """Tiny stand-in for one runtime's persisted global phase."""

    phase: str


def broken_dual_ownership() -> tuple[RuntimeState, RuntimeState]:
    """Simulate a crash between two writes to the same conceptual global state."""
    langgraph = RuntimeState(phase="received")
    crewai_flow = RuntimeState(phase="received")

    # The specialist effect completed and LangGraph checkpointed that fact first.
    langgraph.phase = "specialist_completed"

    # Process dies before the second runtime persists the corresponding Flow state.
    return langgraph, crewai_flow


def reference_boundary() -> RuntimeState:
    """Keep one global owner; CrewAI Crew returns capability output only."""
    return RuntimeState(phase="specialist_completed")


def main() -> None:
    """Print the ownership failure and the reference alternative."""
    langgraph, crewai_flow = broken_dual_ownership()
    print("BROKEN: LangGraph + CrewAI Flow dual ownership")
    print(f"  LangGraph global phase: {langgraph.phase}")
    print(f"  CrewAI Flow phase:      {crewai_flow.phase}")
    print(f"  divergent:              {langgraph.phase != crewai_flow.phase}")
    print()
    reference = reference_boundary()
    print("REFERENCE: LangGraph + CrewAI Crew capability boundary")
    print(f"  canonical phase:        {reference.phase}")
    print("  CrewAI Crew returns specialist output only")


if __name__ == "__main__":
    main()
