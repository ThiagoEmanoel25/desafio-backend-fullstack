"""Structured (JSON) logging for the whole application.

Call `setup_logging()` once at startup (`app/main.py`). After that, any module
can log with the standard library and the line comes out as one JSON object:

    logger.info("task_created", extra={"task_id": str(task.id)})
    {"timestamp": "...", "level": "INFO", "logger": "app.services.task_service",
     "message": "task_created", "task_id": "..."}

Never put a password, a password hash, a JWT, an e-mail address, a full prompt
or a task's title/description in `extra` — ids, durations and outcomes only.
"""

import json
import logging
from datetime import UTC, datetime

from app.config import settings

# Every attribute a bare LogRecord already carries. Whatever a call site passed
# via `extra=` is exactly the difference between a record's `__dict__` and this.
_STANDARD_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Render a record as a single-line JSON object, `extra` keys included."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _STANDARD_RECORD_ATTRS
            }
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # default=str so an unexpected object in `extra` degrades instead of raising.
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Install one JSON stream handler on the root logger.

    Idempotent: uvicorn imports the module tree more than once under
    `--reload`, and a second call must not double every line. Uvicorn's own
    loggers keep their configuration; only the application's lines are JSON.
    """
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    if any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]
