"""
Structured logging configuration
"""

import logging
import sys
from typing import Optional

import structlog

from src.config.settings import settings


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """Setup structured logging for the application"""

    # Use settings if not provided
    log_level = level or settings.LOG_LEVEL
    format_string = format_string or settings.LOG_FORMAT

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        stream=sys.stdout,
        format=format_string,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to classes"""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class"""
        class_name = self.__class__.__name__
        return get_logger(f"{class_name}")


# Global logger instance
logger = get_logger(__name__)