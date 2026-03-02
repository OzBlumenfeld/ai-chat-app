import json
import logging
from logging import LogRecord

from app.config import settings

_STANDARD_ATTRS: frozenset[str] = frozenset({
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "message", "module",
    "msecs", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "taskName", "thread", "threadName",
})


class StructuredFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        base = super().format(record)
        extras = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        if extras:
            return f"{base} | {json.dumps(extras, default=str)}"
        return base


def setup_logging() -> None:
    """Configure structured logging for the application. Call once at startup."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    formatter = StructuredFormatter(fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)
