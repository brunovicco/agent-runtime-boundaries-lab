"""Contracts that cross runtime and process boundaries."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from .identity import ExecutionIdentity


class WorkflowPhase(StrEnum):
    """Global workflow phases owned by the orchestrator."""

    RECEIVED = "received"
    DELEGATING = "delegating"
    SPECIALIST_COMPLETED = "specialist_completed"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class SpecialistRequest(BaseModel):
    """Framework-neutral request sent to a specialist runtime."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    identity: ExecutionIdentity
    specialist: str = "risk-review"
    prompt: str = Field(min_length=1, max_length=8_000)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str


class SpecialistResponse(BaseModel):
    """Result returned by a specialist without controlling global workflow state."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    identity: ExecutionIdentity
    specialist: str
    status: Literal["completed"] = "completed"
    summary: str = Field(min_length=1, max_length=16_000)
    facts: dict[str, Any] = Field(default_factory=dict)
    local_state_version: str | None = None


class ReviewCommand(BaseModel):
    """API command for one workflow execution."""

    conversation_id: str
    prompt: str = Field(min_length=1, max_length=8_000)
    payload: dict[str, Any] = Field(default_factory=dict)
    execution_id: str | None = None
    delegation_id: str | None = None


class ReviewResult(BaseModel):
    """API response for one workflow execution."""

    conversation_id: str
    execution_id: str
    delegation_id: str
    phase: WorkflowPhase
    summary: str
    specialist_reused: bool


class GraphState(TypedDict, total=False):
    """LangGraph state schema. Only the LangGraph adapter owns its lifecycle."""

    conversation_id: str
    execution_id: str
    delegation_id: str
    prompt: str
    payload: dict[str, Any]
    phase: str
    specialist_result: dict[str, Any]
    specialist_reused: bool
    final_summary: str
    error: str
