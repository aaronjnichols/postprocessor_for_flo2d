"""Shared logging utilities for the FLO-2D post-processor."""

from __future__ import annotations

import logging
import os
import sys
import time


DEFAULT_LOGGER_NAME = "FLO2D_Postprocessor"
_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class TimingLogger:
    """Simple step logger that reports step and total elapsed time."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_time = time.time()
        self.last_log_time = self.start_time

    def log(self, message: str) -> None:
        current_time = time.time()
        elapsed = current_time - self.last_log_time
        total_elapsed = current_time - self.start_time
        self.logger.info(
            "%s (Step time: %.2fs, Total time: %.2fs)",
            message,
            elapsed,
            total_elapsed,
        )
        self.last_log_time = current_time


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(_LOG_FORMAT)


def _is_console_handler(handler: logging.Handler) -> bool:
    return isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)


def _normalize_log_file(log_file: str) -> str:
    return os.path.abspath(os.path.normpath(log_file))


def setup_logger(
    name: str = DEFAULT_LOGGER_NAME,
    level: int = logging.INFO,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure a logger without accumulating duplicate handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    formatter = _build_formatter()

    console_handlers = [handler for handler in logger.handlers if _is_console_handler(handler)]
    if console_handlers:
        console_handler = console_handlers[0]
        console_handler.setFormatter(formatter)
        console_handler.setStream(sys.stdout)
        for duplicate in console_handlers[1:]:
            logger.removeHandler(duplicate)
            duplicate.close()
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file:
        normalized_log_file = _normalize_log_file(log_file)
        matching_file_handlers = []
        stale_file_handlers = []

        for handler in logger.handlers:
            if not isinstance(handler, logging.FileHandler):
                continue

            handler_path = _normalize_log_file(handler.baseFilename)
            if handler_path == normalized_log_file:
                matching_file_handlers.append(handler)
            else:
                stale_file_handlers.append(handler)

        if matching_file_handlers:
            file_handler = matching_file_handlers[0]
            file_handler.setFormatter(formatter)
            for duplicate in matching_file_handlers[1:]:
                logger.removeHandler(duplicate)
                duplicate.close()
        else:
            file_handler = logging.FileHandler(normalized_log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        for stale_handler in stale_file_handlers:
            logger.removeHandler(stale_handler)
            stale_handler.close()
    else:
        for handler in list(logger.handlers):
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
                handler.close()

    return logger


logger = setup_logger()
timing_logger = TimingLogger(logger)
