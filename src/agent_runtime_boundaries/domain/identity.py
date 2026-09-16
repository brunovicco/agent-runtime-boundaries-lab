"""Framework-neutral execution identity."""

from __future__ import annotations

import re
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")


class ExecutionIdentity(BaseModel):
    """Canonical IDs owned by the application, not by an agent framework."""

    model_config = ConfigDict(frozen=True)

    conversation_id: str = Field(description="Long-lived application conversation identifier")
    execution_id: str = Field(default_factory=lambda: f"exec:{uuid4()}")
    delegation_id: str = Field(default_factory=lambda: f"deleg:{uuid4()}")
    parent_execution_id: str | None = None

    @field_validator("conversation_id", "execution_id", "delegation_id", "parent_execution_id")
    @classmethod
    def validate_identifier(cls, value: str | None) -> str | None:
        """Reject identifiers that are unsafe for logs, headers or checkpoint keys."""
        if value is None:
            return value
        if not _ID_RE.fullmatch(value):
            raise ValueError("identifier must be 1-160 safe ASCII characters")
        return value

    @property
    def langgraph_thread_id(self) -> str:
        """Map canonical conversation identity into the LangGraph adapter."""
        return self.conversation_id

    @property
    def agno_session_id(self) -> str:
        """Map canonical conversation identity into the specialist-local session."""
        return self.conversation_id

    @property
    def agno_run_id(self) -> str:
        """Map one delegation into one Agno run."""
        return self.delegation_id

    def idempotency_key(self, operation: str) -> str:
        """Create a stable replay-protection key for one operation."""
        normalized = operation.strip().lower().replace(" ", "-")
        if not normalized or not _ID_RE.fullmatch(normalized):
            raise ValueError("operation is not safe for an idempotency key")
        return f"{self.execution_id}:{self.delegation_id}:{normalized}"
