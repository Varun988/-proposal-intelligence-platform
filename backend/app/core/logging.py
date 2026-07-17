import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "taskName",
    "thread",
    "threadName",
}


class JsonLogFormatter(logging.Formatter):
    """Format application logs as structured JSON."""

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        """Convert one log record into JSON."""

        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in STANDARD_LOG_RECORD_FIELDS and not key.startswith("_")
        }

        if extra_fields:
            log_entry["context"] = extra_fields

        if record.exc_info:
            log_entry["exception"] = self.formatException(
                record.exc_info,
            )

        return json.dumps(
            log_entry,
            default=str,
            ensure_ascii=False,
        )


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = True,
) -> None:
    """Configure application-wide logging."""

    normalized_level = log_level.strip().upper()

    level = getattr(
        logging,
        normalized_level,
        logging.INFO,
    )

    handler = logging.StreamHandler(
        stream=sys.stdout,
    )

    if json_format:
        handler.setFormatter(
            JsonLogFormatter(),
        )
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    _configure_dependency_loggers()


def get_logger(
    name: str,
) -> logging.Logger:
    """Return a named application logger."""

    return logging.getLogger(name)


def _configure_dependency_loggers() -> None:
    """Reduce noise from third-party dependency loggers."""

    logging.getLogger("httpx").setLevel(
        logging.WARNING,
    )
    logging.getLogger("httpcore").setLevel(
        logging.WARNING,
    )
    logging.getLogger("urllib3").setLevel(
        logging.WARNING,
    )
    logging.getLogger("sentence_transformers").setLevel(
        logging.WARNING,
    )
