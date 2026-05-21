"""Tests for LangChain dependency preflight validation."""

from unittest.mock import patch

import pytest

from agentic_devtools.orchestration.review.preflight import validate_langchain_dependencies


class TestValidateLangchainDependencies:
    """Tests for validate_langchain_dependencies."""

    def test_returns_true_when_dependencies_available(self):
        """Returns True when langchain_core and langgraph imports succeed."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name in {"langchain_core", "langgraph"}:
                return object()
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            assert validate_langchain_dependencies() is True

    def test_exits_when_langchain_core_missing(self):
        """Exits with error when langchain_core cannot be imported."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langchain_core":
                raise ImportError("No module named 'langchain_core'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                validate_langchain_dependencies()
            assert exc_info.value.code == 1

    def test_exits_when_langgraph_missing(self):
        """Exits with error when langgraph cannot be imported."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langgraph":
                raise ImportError("No module named 'langgraph'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                validate_langchain_dependencies()
            assert exc_info.value.code == 1

    def test_error_message_includes_install_instructions(self, capsys):
        """Error message includes pip install instructions."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langchain_core":
                raise ImportError("No module named 'langchain_core'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit):
                validate_langchain_dependencies()

        captured = capsys.readouterr()
        assert "agentic-devtools[langchain]" in captured.err
