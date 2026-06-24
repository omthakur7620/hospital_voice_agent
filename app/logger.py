"""
JSON logging setup.

Why JSON logs: in production (Railway/Render), logs get piped to a log
aggregator. Plain-text logs are hard to filter/query there; JSON logs let
you grep/filter by field (e.g. find every log where doctor_id=4) instantly.

No third-party logging library used on purpose — stdlib `logging` +
a custom formatter is enough here and keeps the dependency list smaller.
"""

import json
import logging
import sys
from datetime import datetime, timezone

from app.config import settings


class JSONFormatter(logging.Formatter):
    """Formats every log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Attach exception info if present (e.g. logger.exception(...))
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Allow callers to attach structured context, e.g.:
        # logger.info("Booking attempt", extra={"context": {"doctor_id": 4}})
        if hasattr(record, "context"):
            log_entry["context"] = record.context

        return json.dumps(log_entry)


_configured = False


def _configure_root_logger() -> None:
    """Idempotent root logger setup — safe to call multiple times."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    root.handlers = [handler]  # replace default handlers to avoid duplicate logs

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Usage: logger = get_logger(__name__)
    Every module should fetch its own named logger so log lines show
    exactly which module emitted them (e.g. "app.services.appointment_service").
    """
    _configure_root_logger()
    return logging.getLogger(name)