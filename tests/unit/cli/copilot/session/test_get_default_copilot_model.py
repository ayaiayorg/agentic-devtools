"""Tests for get_default_copilot_model."""

from unittest.mock import patch

from agentic_devtools.cli.copilot.session import DEFAULT_COPILOT_MODEL, get_default_copilot_model

_GET_PROJECT_CONFIG_VALUE = "agentic_devtools.cli.config.project_config.get_project_config_value"


class TestGetDefaultCopilotModel:
    """Tests for get_default_copilot_model."""

    def test_returns_hardcoded_default_when_no_project_config(self):
        """Returns DEFAULT_COPILOT_MODEL when project config has no default_copilot_model."""
        with patch(
            _GET_PROJECT_CONFIG_VALUE,
            return_value=None,
        ):
            result = get_default_copilot_model()

        assert result == DEFAULT_COPILOT_MODEL
        assert result == "gpt-4o"

    def test_returns_configured_model_from_project_config(self):
        """Returns the model from project config when set."""
        with patch(
            _GET_PROJECT_CONFIG_VALUE,
            return_value="gpt-5.3-codex",
        ):
            result = get_default_copilot_model()

        assert result == "gpt-5.3-codex"

    def test_strips_whitespace_from_configured_model(self):
        """Strips leading/trailing whitespace from the configured model."""
        with patch(
            _GET_PROJECT_CONFIG_VALUE,
            return_value="  claude-opus-4.6  ",
        ):
            result = get_default_copilot_model()

        assert result == "claude-opus-4.6"

    def test_falls_back_to_hardcoded_default_when_configured_model_is_whitespace_only(self):
        """Falls back to DEFAULT_COPILOT_MODEL when configured value is whitespace-only."""
        with patch(
            _GET_PROJECT_CONFIG_VALUE,
            return_value="   ",
        ):
            result = get_default_copilot_model()

        assert result == DEFAULT_COPILOT_MODEL

    def test_falls_back_to_hardcoded_default_when_configured_model_is_empty_string(self):
        """Falls back to DEFAULT_COPILOT_MODEL when configured value is empty."""
        with patch(
            _GET_PROJECT_CONFIG_VALUE,
            return_value="",
        ):
            result = get_default_copilot_model()

        assert result == DEFAULT_COPILOT_MODEL

    def test_falls_back_to_hardcoded_default_when_get_project_config_value_raises(self):
        """Falls back gracefully when get_project_config_value raises an exception."""
        with patch(
            _GET_PROJECT_CONFIG_VALUE,
            side_effect=RuntimeError("config unavailable"),
        ):
            result = get_default_copilot_model()

        assert result == DEFAULT_COPILOT_MODEL

    def test_default_copilot_model_constant_is_gpt_4o(self):
        """DEFAULT_COPILOT_MODEL is set to a valid known-good model."""
        assert DEFAULT_COPILOT_MODEL == "gpt-4o"
