"""Task schemas.

Pydantic v2 models for task CRUD and for the AI agent tool validation.
`TaskStatus` and `TaskPriority` are defined once here; the ORM model, the API
and the agent tools all reuse them. `TaskCreate` is also built from the data
extracted by the LLM, so its length limits apply to both entry points.
"""

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


TITLE_MIN, TITLE_MAX = 3, 200
DESCRIPTION_MAX = 2000
DEPARTMENT_MIN, DEPARTMENT_MAX = 2, 100


class TaskCreate(BaseModel):
    """Payload to create a task (from the API or from the agent tool)."""

    title: str = Field(min_length=TITLE_MIN, max_length=TITLE_MAX)
    due_date: date | None = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    priority: TaskPriority = TaskPriority.medium
    department: str = Field(min_length=DEPARTMENT_MIN, max_length=DEPARTMENT_MAX)


class TaskUpdate(BaseModel):
    """Partial update payload: only the fields that are sent are changed."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    due_date: date | None = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    department: str | None = Field(default=None, min_length=2, max_length=100)

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self) -> "TaskUpdate":
        """Omit a required column to keep it; an explicit null would hit NOT NULL."""
        for name in ("title", "status", "priority", "department"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class TaskResponse(BaseModel):
    """A task as returned by the API. The owner (`user_id`) is not exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    due_date: date | None = None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    department: str
    created_at: datetime
    updated_at: datetime
