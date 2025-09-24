"""Logging configuration and utilities."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import coloredlogs
from pythonjsonlogger import jsonlogger
from datetime import datetime
import json


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    max_bytes: int = 10485760,
    backup_count: int = 5,
    json_format: bool = False
) -> None:
    """
    Setup logging configuration for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        json_format: Whether to use JSON format for logs
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatters
    if json_format:
        formatter = CustomJsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    if not json_format:
        coloredlogs.install(
            level=log_level.upper(),
            logger=root_logger,
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('supabase').setLevel(logging.WARNING)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to the log record."""
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()

        # Add log level
        log_record['level'] = record.levelname

        # Add module and function info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # Add custom fields if present
        if hasattr(record, 'duration'):
            log_record['duration_seconds'] = record.duration
        if hasattr(record, 'coins_scraped'):
            log_record['coins_scraped'] = record.coins_scraped
        if hasattr(record, 'error_type'):
            log_record['error_type'] = record.error_type


class LoggerMixin:
    """Mixin class to provide logging functionality."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for the class."""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_execution_time(func):
    """Decorator to log function execution time."""
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                f"{func.__name__} completed successfully",
                extra={'duration': duration}
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{func.__name__} failed: {str(e)}",
                extra={'duration': duration, 'error_type': type(e).__name__}
            )
            raise

    return wrapper


def log_scraping_metrics(
    status: str,
    coins_scraped: int,
    duration: float,
    error: Optional[str] = None
) -> dict:
    """
    Log scraping metrics for monitoring.

    Args:
        status: Scraping status (success, partial, failed)
        coins_scraped: Number of coins scraped
        duration: Duration in seconds
        error: Error message if any

    Returns:
        Dictionary with metrics
    """
    logger = get_logger("scraping_metrics")

    metrics = {
        "status": status,
        "coins_scraped": coins_scraped,
        "duration_seconds": round(duration, 2),
        "timestamp": datetime.utcnow().isoformat()
    }

    if error:
        metrics["error_message"] = error
        logger.error("Scraping failed", extra=metrics)
    else:
        logger.info(f"Scraping completed: {coins_scraped} coins in {duration:.2f}s", extra=metrics)

    return metrics


class ScrapeLogger:
    """Context manager for logging scraping operations."""

    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the scrape logger.

        Args:
            operation: Name of the operation being performed
            logger: Logger instance to use
        """
        self.operation = operation
        self.logger = logger or get_logger("scraper")
        self.start_time = None
        self.metrics = {}

    def __enter__(self):
        """Enter the context manager."""
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        duration = time.time() - self.start_time

        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation} in {duration:.2f}s",
                extra={'duration': duration, **self.metrics}
            )
        else:
            self.logger.error(
                f"Failed {self.operation} after {duration:.2f}s: {exc_val}",
                extra={
                    'duration': duration,
                    'error_type': exc_type.__name__,
                    'error_message': str(exc_val),
                    **self.metrics
                }
            )

    def add_metric(self, key: str, value: any) -> None:
        """Add a metric to be logged."""
        self.metrics[key] = value


import time