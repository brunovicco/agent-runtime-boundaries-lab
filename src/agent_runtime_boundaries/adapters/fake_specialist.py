"""Credential-free specialist used by the deterministic demo and unit tests."""

from agent_runtime_boundaries.domain.contracts import SpecialistRequest, SpecialistResponse


class FakeSpecialist:
    """Return deterministic output while exposing invocation count."""

    def __init__(self) -> None:
        """Start with no recorded specialist calls."""
        self.calls = 0

    async def analyze(self, request: SpecialistRequest) -> SpecialistResponse:
        """Return one deterministic specialist result."""
        self.calls += 1
        return SpecialistResponse(
            identity=request.identity,
            specialist=request.specialist,
            summary=f"Deterministic review for {request.identity.conversation_id}",
            facts={"payload_keys": sorted(request.payload)},
            local_state_version=f"fake:{self.calls}",
        )
