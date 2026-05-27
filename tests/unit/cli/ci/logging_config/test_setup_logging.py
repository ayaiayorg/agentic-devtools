"""Tests for setup_logging() function."""

import logging
import os
import sys
from unittest.mock import patch

from agentic_devtools.cli.ci.logging_config import setup_logging


class TestSetupLogging:
    """Tests for setup_logging()."""

    def _clear_root_handlers(self) -> None:
        """Clear root logger handlers to test setup_logging from clean state."""
        logging.getLogger().handlers.clear()

    def setup_method(self) -> None:
        """Save original root logger state."""
        root = logging.getLogger()
        self._original_handlers = root.handlers[:]
        self._original_level = root.level

    def teardown_method(self) -> None:
        """Restore root logger state."""
        root = logging.getLogger()
        root.handlers[:] = self._original_handlers
        root.setLevel(self._original_level)

    def test_adds_handler_to_root_logger(self) -> None:
        self._clear_root_handlers()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGDT_LOG_LEVEL", None)
            setup_logging()
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)

    def test_handler_outputs_to_stderr(self) -> None:
        self._clear_root_handlers()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGDT_LOG_LEVEL", None)
            setup_logging()
        root = logging.getLogger()
        handler = root.handlers[0]
        assert handler.stream is sys.stderr

    def test_format_includes_timestamp_level_name(self) -> None:
        self._clear_root_handlers()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGDT_LOG_LEVEL", None)
            setup_logging()
        root = logging.getLogger()
        handler = root.handlers[0]
        assert "%(asctime)s" in handler.formatter._fmt
        assert "%(levelname)" in handler.formatter._fmt
        assert "%(name)s" in handler.formatter._fmt

    def test_idempotent_does_not_add_duplicate_handlers(self) -> None:
        self._clear_root_handlers()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGDT_LOG_LEVEL", None)
            setup_logging()
            setup_logging()
        root = logging.getLogger()
        assert len(root.handlers) == 1

    def test_skips_when_handlers_already_present(self) -> None:
        """When root logger already has handlers, setup_logging is a no-op."""
        self._clear_root_handlers()
        root = logging.getLogger()
        handler = logging.StreamHandler()
        root.addHandler(handler)
        existing_count = len(root.handlers)
        try:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("AGDT_LOG_LEVEL", None)
                setup_logging()
            assert len(root.handlers) == existing_count
        finally:
            root.removeHandler(handler)
            handler.close()

    def test_respects_agdt_log_level_debug(self) -> None:
        self._clear_root_handlers()
        with patch.dict(os.environ, {"AGDT_LOG_LEVEL": "DEBUG"}, clear=False):
            setup_logging()
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_respects_agdt_log_level_warning(self) -> None:
        self._clear_root_handlers()
        with patch.dict(os.environ, {"AGDT_LOG_LEVEL": "WARNING"}, clear=False):
            setup_logging()
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_invalid_level_falls_back_to_info(self) -> None:
        self._clear_root_handlers()
        with patch.dict(os.environ, {"AGDT_LOG_LEVEL": "VERBOSE"}, clear=False):
            setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_defaults_to_info_level(self) -> None:
        self._clear_root_handlers()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGDT_LOG_LEVEL", None)
            setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO
