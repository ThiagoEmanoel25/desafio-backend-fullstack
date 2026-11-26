"""Task schemas.

Pydantic v2 models for task CRUD and for the AI agent tool validation.
`TaskStatus` and `TaskPriority` are defined once here; the ORM model, the API
and the agent tools all reuse them. `TaskCreate` is also built from the data
extracted by the LLM, so its length limits apply to both entry points.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(StrEnum):
    """Lifecycle state of a task."""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class TaskPriority(StrEnum):
    """Urgency of a task."""

    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskCreate(BaseModel):
    """Payload to create a task (from the API or from the agent tool)."""

    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority = TaskPriority.medium
    department: str = Field(min_length=2, max_length=100)


class TaskUpdate(BaseModel):
    """Partial update payload: only the fields that are sent are changed."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    department: str | None = Field(default=None, min_length=2, max_length=100)


class TaskResponse(BaseModel):
    """A task as returned by the API. The owner (`user_id`) is not exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    department: str
    created_at: datetime
    updated_at: datetime
