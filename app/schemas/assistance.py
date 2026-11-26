"""Structured output of the task assistant and response of `POST /v1/tasks/{id}/assist`.

PydanticAI sends this schema, descriptions included, to the model, so the
descriptions are prompt surface and the constraints reject (and retry) bad output.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.task import TaskPriority

Item = Annotated[str, Field(min_length=3, max_length=200)]


class Complexity(StrEnum):
    """Rough difficulty of a task."""

    low = "low"
    medium = "medium"
    high = "high"


class TaskAssistance(BaseModel):
    """The assistant's evaluation of one task and a plan to execute it."""

    summary: str = Field(
        min_length=10,
        max_length=400,
        description="What the task is about, in one or two sentences.",
    )
    complexity: Complexity = Field(
        description="How hard the task is: low, medium or high."
    )
    estimated_hours: float = Field(
        gt=0, le=200, description="Rough effort estimate in hours."
    )
    suggested_priority: TaskPriority = Field(
        description="The priority the task should have: low, medium, high or urgent."
    )
    priority_reason: str = Field(
        min_length=10,
        max_length=300,
        description="Why that priority, referring to the task's current priority.",
    )
    steps: list[Item] = Field(
        min_length=1,
        max_length=7,
        description="Concrete, ordered actions to execute the task, not generic tips.",
    )
    risks: list[Item] = Field(
        max_length=5, description="What could go wrong or deserves attention."
    )
    clarifying_questions: list[Item] = Field(
        max_length=5,
        description="What information is missing in order to do the task well.",
    )
