"""The JSON formatter must emit the `extra` keys and never double-install."""

import json
import logging

from app.core.logging import JsonFormatter, setup_logging


def _format(record: logging.LogRecord) -> dict:
    return json.loads(JsonFormatter().format(record))


def test_formatter_emits_extra_keys(caplog):
    logger = logging.getLogger("app.test")
    with caplog.at_level(logging.INFO, logger="app.test"):
        logger.info("task_created", extra={"task_id": "abc", "duration_ms": 12})
    payload = _format(caplog.records[0])
    assert payload["message"] == "task_created"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["task_id"] == "abc"
    assert payload["duration_ms"] == 12
    assert payload["timestamp"].endswith("+00:00")


def test_formatter_renders_exception(caplog):
    logger = logging.getLogger("app.test")
    with caplog.at_level(logging.ERROR, logger="app.test"):
        try:
            raise ValueError("boom")
        except ValueError:
            logger.exception("failed")
    assert "ValueError: boom" in _format(caplog.records[0])["exception"]


def test_setup_logging_is_idempotent():
    root = logging.getLogger()
    previous = root.handlers
    try:
        root.handlers = []
        setup_logging()
        setup_logging()
        assert len(root.handlers) == 1
    finally:
        root.handlers = previous
