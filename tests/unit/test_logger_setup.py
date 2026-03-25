"""Regression tests for shared logger configuration."""

from __future__ import annotations

import logging
import os
from uuid import uuid4

from core.logger import setup_logger


def _close_logger_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_setup_logger_reuses_console_handler_and_replaces_log_file(tmp_path) -> None:
    """Repeated logger setup should not accumulate duplicate handlers."""
    logger_name = f"flo2d_test_{uuid4().hex}"
    log_file_one = tmp_path / "first.log"
    log_file_two = tmp_path / "second.log"
    logger = logging.getLogger(logger_name)
    _close_logger_handlers(logger)

    try:
        setup_logger(name=logger_name, log_file=str(log_file_one))
        logger = setup_logger(name=logger_name, log_file=str(log_file_two))

        console_handlers = [
            handler
            for handler in logger.handlers
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        ]
        file_handlers = [
            handler
            for handler in logger.handlers
            if isinstance(handler, logging.FileHandler)
        ]

        assert len(console_handlers) == 1
        assert len(file_handlers) == 1
        assert os.path.normcase(file_handlers[0].baseFilename) == os.path.normcase(str(log_file_two))

        logger.info("logger smoke test")
        file_handlers[0].flush()
        assert "logger smoke test" in log_file_two.read_text(encoding="utf-8")

        logger = setup_logger(name=logger_name)
        assert not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)
    finally:
        _close_logger_handlers(logger)
