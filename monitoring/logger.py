"""
Structured Logging
Rebuild 3: Observability

Provides structured logging across all layers.
Logs are machine-parseable JSON with context.
"""

from typing import Dict, Any, Optional
import json
import time
import sys
from enum import Enum


class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogger:
    """
    Structured logger for Portal-OS.
    Outputs JSON logs with context.
    """
    
    def __init__(self, component: str, min_level: LogLevel = LogLevel.INFO):
        self.component = component
        self.min_level = min_level
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Set logging context (request_id, user, etc)"""
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear logging context"""
        self.context.clear()
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log error message"""
        if exception:
            kwargs["exception"] = str(exception)
            kwargs["exception_type"] = type(exception).__name__
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def _log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Internal logging method"""
        if level.value < self.min_level.value:
            return
        
        log_entry = {
            "timestamp": time.time(),
            "level": level.value,
            "component": self.component,
            "message": message,
            **self.context,
            **kwargs,
        }
        
        json_log = json.dumps(log_entry)
        print(json_log, file=sys.stdout)


class LogContext:
    """
    Context manager for setting logging context.
    """
    
    def __init__(self, logger: StructuredLogger, **kwargs):
        self.logger = logger
        self.context = kwargs
        self.previous_context = None
    
    def __enter__(self):
        self.previous_context = self.logger.context.copy()
        self.logger.set_context(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.context = self.previous_context
