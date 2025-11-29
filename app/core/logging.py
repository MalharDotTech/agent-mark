"""Logging configuration for Meta Ads API Service."""

import logging
import sys
from datetime import datetime
from typing import Any, Dict

from .config import settings


class TimestampFormatter(logging.Formatter):
    """Custom formatter that adds timestamps to log messages."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with timestamp."""
        # Add timestamp to the record
        record.timestamp = datetime.utcnow().isoformat() + "Z"
        
        if settings.log_format.lower() == "json":
            return self._format_json(record)
        else:
            return self._format_text(record)
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        import json
        
        log_data: Dict[str, Any] = {
            "timestamp": record.timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ("name", "msg", "args", "levelname", "levelno", "pathname", 
                          "filename", "module", "lineno", "funcName", "created", 
                          "msecs", "relativeCreated", "thread", "threadName", 
                          "processName", "process", "getMessage", "exc_info", 
                          "exc_text", "stack_info", "timestamp"):
                log_data[key] = value
        
        return json.dumps(log_data)
    
    def _format_text(self, record: logging.LogRecord) -> str:
        """Format log record as plain text."""
        return f"{record.timestamp} [{record.levelname}] {record.name}: {record.getMessage()}"


def setup_logging() -> None:
    """Configure logging for the application."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Set formatter
    formatter = TimestampFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)