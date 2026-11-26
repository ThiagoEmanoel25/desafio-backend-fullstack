"""Schemas for the AI chat endpoint."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.schemas.task import TaskResponse


class ChatRequest(BaseModel):
    """A single user message for the task agent."""

    message: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]


class ChatResponse(BaseModel):
    """The agent's reply plus the task it created, if any."""

    reply: str
    created_task: TaskResponse | None = None
