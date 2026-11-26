"""Task CRUD endpoints. Every route is scoped to the authenticated user."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.assistance import TaskAssistance
from app.schemas.task import (
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)
from app.services import task_assistant_service, task_service

router = APIRouter()


async def _commit(db: AsyncSession) -> None:
    """Commit the request's transaction; a constraint failure becomes a 409."""
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Task conflict") from None


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    """Create a task owned by the current user."""
    task = await task_service.create_task(db, current_user.id, payload)
    await _commit(db)
    return task


@router.get("/", response_model=list[TaskResponse], summary="List my tasks")
async def list_tasks(
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Task]:
    """List the current user's tasks, newest first, optionally filtered."""
    tasks = await task_service.list_tasks(
        db, current_user.id, status=status, priority=priority, skip=skip, limit=limit
    )
    return list(tasks)


@router.get("/{task_id}", response_model=TaskResponse, summary="Get a task")
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    """Return one of the current user's tasks; 404 if missing or not theirs."""
    return await task_service.get_task(db, current_user.id, task_id)


@router.patch("/{task_id}", response_model=TaskResponse, summary="Update a task")
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    """Change only the fields sent; 404 if missing or not theirs."""
    task = await task_service.update_task(db, current_user.id, task_id, payload)
    await _commit(db)
    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete one of the current user's tasks; 404 if missing or not theirs."""
    await task_service.delete_task(db, current_user.id, task_id)
    await _commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{task_id}/assist",
    response_model=TaskAssistance,
    summary="Get AI assistance for a task",
)
async def assist_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskAssistance:
    """Analyse one of the current user's tasks with the LLM; may take a few seconds.

    Returns a structured evaluation and plan. 404 if the task is missing or not
    theirs (before any model call); 503 if the model fails.
    """
    return await task_assistant_service.assist_task(db, current_user.id, task_id)
