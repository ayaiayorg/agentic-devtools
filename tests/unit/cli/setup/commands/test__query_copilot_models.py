"""Tests for _query_copilot_models."""

import subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup.commands import _KNOWN_COPILOT_MODELS, _query_copilot_models

_GET_BINARY = "agentic_devtools.cli.copilot.session._get_copilot_binary"
_SUBPROCESS_RUN = "subprocess.run"


class TestQueryCopilotModels:
    """Tests for _query_copilot_models."""

    def test_returns_models_from_binary_when_successful(self):
        """Returns parsed model list from binary output when the call succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "gpt-5.3-codex\nclaude-opus-4.6\ngpt-4o\n"

        with patch(_GET_BINARY, return_value="/usr/local/bin/copilot"):
            with patch(_SUBPROCESS_RUN, return_value=mock_result):
                result = _query_copilot_models()

        assert result == ["gpt-5.3-codex", "claude-opus-4.6", "gpt-4o"]

    def test_falls_back_to_known_models_when_binary_not_found(self):
        """Falls back to _KNOWN_COPILOT_MODELS when _get_copilot_binary returns None."""
        with patch(_GET_BINARY, return_value=None):
            result = _query_copilot_models()

        assert result == list(_KNOWN_COPILOT_MODELS)

    def test_falls_back_to_known_models_when_subprocess_raises_oserror(self):
        """Falls back to _KNOWN_COPILOT_MODELS when subprocess.run raises OSError."""
        with patch(_GET_BINARY, return_value="/usr/local/bin/copilot"):
            with patch(_SUBPROCESS_RUN, side_effect=OSError("not found")):
                result = _query_copilot_models()

        assert result == list(_KNOWN_COPILOT_MODELS)

    def test_falls_back_to_known_models_when_binary_returns_nonzero(self):
        """Falls back to _KNOWN_COPILOT_MODELS when binary exits with non-zero return code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch(_GET_BINARY, return_value="/usr/local/bin/copilot"):
            with patch(_SUBPROCESS_RUN, return_value=mock_result):
                result = _query_copilot_models()

        assert result == list(_KNOWN_COPILOT_MODELS)

    def test_falls_back_to_known_models_when_stdout_is_empty(self):
        """Falls back to _KNOWN_COPILOT_MODELS when binary produces no output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch(_GET_BINARY, return_value="/usr/local/bin/copilot"):
            with patch(_SUBPROCESS_RUN, return_value=mock_result):
                result = _query_copilot_models()

        assert result == list(_KNOWN_COPILOT_MODELS)

    def test_falls_back_to_known_models_on_timeout(self):
        """Falls back to _KNOWN_COPILOT_MODELS when the binary call times out."""
        with patch(_GET_BINARY, return_value="/usr/local/bin/copilot"):
            with patch(
                _SUBPROCESS_RUN,
                side_effect=subprocess.TimeoutExpired(cmd="copilot", timeout=10),
            ):
                result = _query_copilot_models()

        assert result == list(_KNOWN_COPILOT_MODELS)

    def test_strips_blank_lines_from_binary_output(self):
        """Blank lines in binary output are ignored."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "\ngpt-5.3-codex\n\ngpt-4o\n\n"

        with patch(_GET_BINARY, return_value="/usr/local/bin/copilot"):
            with patch(_SUBPROCESS_RUN, return_value=mock_result):
                result = _query_copilot_models()

        assert result == ["gpt-5.3-codex", "gpt-4o"]

    def test_returns_a_copy_of_known_models_on_fallback(self):
        """Returns a copy (not the original list) of _KNOWN_COPILOT_MODELS on fallback."""
        with patch(_GET_BINARY, return_value=None):
            result = _query_copilot_models()

        assert result == list(_KNOWN_COPILOT_MODELS)
        assert result is not _KNOWN_COPILOT_MODELS
