"""Tests for build_copilot_args."""

from unittest.mock import patch

from agentic_devtools.cli.copilot.session import build_copilot_args


class TestBuildCopilotArgs:
    """Tests for build_copilot_args public wrapper."""

    @patch("agentic_devtools.cli.copilot.session._build_copilot_args")
    def test_delegates_to_internal_function(self, mock_internal):
        """build_copilot_args delegates to the internal _build_copilot_args."""
        mock_internal.return_value = ["copilot", "--autopilot", "-i", "hello"]

        result = build_copilot_args("hello", interactive=True)

        mock_internal.assert_called_once_with("hello", interactive=True, autopilot=True, model=None)
        assert result == ["copilot", "--autopilot", "-i", "hello"]

    @patch("agentic_devtools.cli.copilot.session._build_copilot_args")
    def test_passes_interactive_false(self, mock_internal):
        """build_copilot_args passes interactive=False correctly."""
        mock_internal.return_value = ["copilot", "--allow-all", "-p", "prompt"]

        result = build_copilot_args("prompt", interactive=False)

        mock_internal.assert_called_once_with("prompt", interactive=False, autopilot=True, model=None)
        assert result == ["copilot", "--allow-all", "-p", "prompt"]

    @patch("agentic_devtools.cli.copilot.session._build_copilot_args", return_value=None)
    def test_returns_none_when_prompt_too_large(self, mock_internal):
        """build_copilot_args returns None when the prompt is too large."""
        result = build_copilot_args("x" * 100_000)

        assert result is None

    @patch("agentic_devtools.cli.copilot.session._build_copilot_args")
    def test_delegates_autopilot_parameter(self, mock_internal):
        """build_copilot_args forwards autopilot=False to _build_copilot_args."""
        mock_internal.return_value = ["copilot", "-i", "hello"]

        result = build_copilot_args("hello", interactive=True, autopilot=False)

        mock_internal.assert_called_once_with("hello", interactive=True, autopilot=False, model=None)
        assert result == ["copilot", "-i", "hello"]

    @patch("agentic_devtools.cli.copilot.session._build_copilot_args")
    def test_defaults_autopilot_to_true(self, mock_internal):
        """build_copilot_args defaults autopilot=True when not specified."""
        mock_internal.return_value = ["copilot", "--autopilot", "-i", "hello"]

        build_copilot_args("hello")

        mock_internal.assert_called_once_with("hello", interactive=True, autopilot=True, model=None)
