"""structlog configuration for structured JSON/console logging."""

import logging
import sys

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from src.config.settings import get_settings


def configure_logging() -> None:
    """Configure structlog processors for the current environment."""
    settings = get_settings()
    level = logging.DEBUG if settings.environment == "development" else logging.INFO

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "prism-backend") -> structlog.stdlib.BoundLogger:
    """Return a bound logger with service + env context."""
    settings = get_settings()
    return structlog.get_logger(name).bind(service="prism-backend", env=settings.environment)


def bind_user_context(*, org_id: str, user_id: str, role: str | None = None) -> None:
    """Attach authenticated identity to subsequent log lines in this request."""
    fields: dict[str, str] = {"org_id": org_id, "user_id": user_id}
    if role:
        fields["role"] = role
    bind_contextvars(**fields)


def clear_log_context() -> None:
    """Drop request-scoped contextvars (used by middleware teardown)."""
    clear_contextvars()
