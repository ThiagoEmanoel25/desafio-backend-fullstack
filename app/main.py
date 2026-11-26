"""FastAPI application entrypoint."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.agent.deps import AssistantUnavailableError, ChatUnavailableError
from app.api.v1.router import router as api_v1_router
from app.config import settings
from app.services.task_service import TaskNotFoundError

# TODO: call setup_logging() from app/core/logging.py here

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# TODO: add CORSMiddleware so the React frontend can call this API.
# Allowed origins are available in `settings.cors_origins_list`.
# Docs: https://fastapi.tiangolo.com/tutorial/cors/

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


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
