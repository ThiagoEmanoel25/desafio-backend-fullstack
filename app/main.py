"""FastAPI application entrypoint."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.deps import AssistantUnavailableError, ChatUnavailableError
from app.api.v1.router import router as api_v1_router
from app.config import settings
from app.core.logging import setup_logging
from app.services.task_service import TaskNotFoundError

setup_logging()

DESCRIPTION = """\
Task manager with an AI assistant: every user owns their own tasks, can ask a
chat agent to create them in natural language, and can ask a second agent to
evaluate a task and plan its execution.

All `/v1/tasks` and `/v1/chat` routes need a bearer token. In this page, click
**Authorize** and send your e-mail in the `username` field: the button posts
form data to `POST /v1/auth/login` and reuses the token it returns.
"""

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_v1_router)


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(
    request: Request, exc: TaskNotFoundError
) -> JSONResponse:
    """Missing and not-yours are the same 404, so a foreign task never leaks."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Task not found"}
    )


@app.exception_handler(ChatUnavailableError)
async def chat_unavailable_handler(
    request: Request, exc: ChatUnavailableError
) -> JSONResponse:
    """Provider failures and usage-limit breaches never leak details."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The assistant is unavailable, try again later"},
    )


@app.exception_handler(AssistantUnavailableError)
async def assistant_unavailable_handler(
    request: Request, exc: AssistantUnavailableError
) -> JSONResponse:
    """Provider failures and invalid model output never leak details."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The assistant is unavailable, try again later"},
    )


@app.get(
    "/health",
    tags=["health"],
    response_model=dict[str, str],
    summary="Health check",
)
async def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
