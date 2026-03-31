"""Tests for _prompt_copilot_model."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup.commands import _KNOWN_COPILOT_MODELS, _prompt_copilot_model


class TestPromptCopilotModel:
    """Tests for _prompt_copilot_model."""

    def test_saves_selected_model_to_project_config(self, capsys):
        """Should save the selected model to project config."""
        models = ["gpt-5.3-codex", "gpt-4o"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config",
                    return_value=MagicMock(),
                ) as mock_save:
                    with patch("agentic_devtools.cli.setup.commands.input", return_value="1"):
                        _prompt_copilot_model()

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["default_copilot_model"] == "gpt-5.3-codex"

    def test_uses_first_model_as_default_when_no_existing_config(self, capsys):
        """Uses first model as default when no model is configured."""
        models = ["gpt-5.3-codex", "gpt-4o"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch("agentic_devtools.cli.config.project_config.save_project_config") as mock_save:
                    # Enter selects default
                    with patch("agentic_devtools.cli.setup.commands.input", return_value=""):
                        _prompt_copilot_model()

        saved = mock_save.call_args[0][0]
        assert saved["default_copilot_model"] == "gpt-5.3-codex"

    def test_uses_existing_configured_model_as_default(self, capsys):
        """Uses already-configured model as default when it's in the list."""
        models = ["gpt-5.3-codex", "gpt-4o", "claude-opus-4.6"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"default_copilot_model": "claude-opus-4.6"},
            ):
                with patch("agentic_devtools.cli.config.project_config.save_project_config") as mock_save:
                    # Enter selects default (should be claude-opus-4.6)
                    with patch("agentic_devtools.cli.setup.commands.input", return_value=""):
                        _prompt_copilot_model(force_prompt=True)

        saved = mock_save.call_args[0][0]
        assert saved["default_copilot_model"] == "claude-opus-4.6"

    def test_accepts_free_form_model_name(self, capsys):
        """Accepts a free-form model name typed directly."""
        models = ["gpt-5.3-codex", "gpt-4o"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch("agentic_devtools.cli.config.project_config.save_project_config") as mock_save:
                    with patch("agentic_devtools.cli.setup.commands.input", return_value="my-custom-model"):
                        _prompt_copilot_model()

        saved = mock_save.call_args[0][0]
        assert saved["default_copilot_model"] == "my-custom-model"

    def test_handles_eof_error_gracefully(self, capsys):
        """Handles EOFError (non-interactive) without crashing."""
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=["gpt-4o"]):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch("agentic_devtools.cli.setup.commands.input", side_effect=EOFError):
                    # Should not raise
                    _prompt_copilot_model()

    def test_handles_keyboard_interrupt_gracefully(self, capsys):
        """Handles KeyboardInterrupt without crashing."""
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=["gpt-4o"]):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch("agentic_devtools.cli.setup.commands.input", side_effect=KeyboardInterrupt):
                    # Should not raise
                    _prompt_copilot_model()

    def test_prints_confirmation_message(self, capsys):
        """Prints a confirmation message with the selected model."""
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=["gpt-5.3-codex"]):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch("agentic_devtools.cli.config.project_config.save_project_config"):
                    with patch("agentic_devtools.cli.setup.commands.input", return_value="1"):
                        _prompt_copilot_model()

        out = capsys.readouterr().out
        assert "gpt-5.3-codex" in out
        assert "✓" in out

    def test_invalid_numeric_selection_uses_default(self, capsys):
        """Out-of-range numeric selection keeps the default."""
        models = ["gpt-5.3-codex", "gpt-4o"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch("agentic_devtools.cli.config.project_config.save_project_config") as mock_save:
                    with patch("agentic_devtools.cli.setup.commands.input", return_value="99"):
                        _prompt_copilot_model()

        saved = mock_save.call_args[0][0]
        # Out of range — should fall back to default (first model)
        assert saved["default_copilot_model"] == "gpt-5.3-codex"

    def test_known_copilot_models_list_is_non_empty(self):
        """_KNOWN_COPILOT_MODELS must be a non-empty list of strings."""
        assert isinstance(_KNOWN_COPILOT_MODELS, list)
        assert len(_KNOWN_COPILOT_MODELS) > 0
        for model in _KNOWN_COPILOT_MODELS:
            assert isinstance(model, str)
            assert model.strip() == model

    def test_strips_whitespace_from_existing_configured_model(self, capsys):
        """Strips leading/trailing whitespace from existing config before matching."""
        models = ["gpt-5.3-codex", "gpt-4o", "claude-opus-4.6"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"default_copilot_model": "  claude-opus-4.6  "},
            ):
                with patch("agentic_devtools.cli.config.project_config.save_project_config") as mock_save:
                    # Enter selects default (should match claude-opus-4.6 after strip)
                    with patch("agentic_devtools.cli.setup.commands.input", return_value=""):
                        _prompt_copilot_model(force_prompt=True)

        saved = mock_save.call_args[0][0]
        assert saved["default_copilot_model"] == "claude-opus-4.6"

    def test_skips_prompt_when_model_already_set(self, capsys):
        """Should skip prompt when default_copilot_model key exists in config."""
        existing = {"default_copilot_model": "gpt-5.3-codex"}
        mock_input = patch("agentic_devtools.cli.setup.commands.input")
        with mock_input as m_input:
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                _prompt_copilot_model()

        m_input.assert_not_called()
        out = capsys.readouterr().out
        assert "Default Copilot model already set: gpt-5.3-codex" in out

    def test_skips_prompt_when_model_is_empty_string(self, capsys):
        """Should skip prompt even when default_copilot_model is empty string."""
        existing = {"default_copilot_model": ""}
        mock_input = patch("agentic_devtools.cli.setup.commands.input")
        with mock_input as m_input:
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                _prompt_copilot_model()

        m_input.assert_not_called()
        out = capsys.readouterr().out
        assert "Default Copilot model already set:" in out

    def test_force_prompt_re_prompts_when_model_set(self, capsys):
        """Should re-prompt when force_prompt=True even if model exists."""
        existing = {"default_copilot_model": "gpt-4o"}
        models = ["gpt-5.3-codex", "gpt-4o"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch("agentic_devtools.cli.config.project_config.save_project_config") as mock_save:
                    with patch("agentic_devtools.cli.setup.commands.input", return_value="1"):
                        _prompt_copilot_model(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["default_copilot_model"] == "gpt-5.3-codex"

    def test_skips_prompt_when_model_is_none(self, capsys):
        """Should skip prompt when default_copilot_model is None (key present)."""
        existing = {"default_copilot_model": None}
        mock_input = patch("agentic_devtools.cli.setup.commands.input")
        with mock_input as m_input:
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                _prompt_copilot_model()

        m_input.assert_not_called()
        out = capsys.readouterr().out
        assert "Default Copilot model already set:" in out

    def test_force_prompt_handles_none_model_gracefully(self, capsys):
        """Should handle None model value gracefully when force_prompt=True."""
        existing = {"default_copilot_model": None}
        models = ["gpt-5.3-codex", "gpt-4o"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch("agentic_devtools.cli.config.project_config.save_project_config") as mock_save:
                    with patch("agentic_devtools.cli.setup.commands.input", return_value="1"):
                        _prompt_copilot_model(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["default_copilot_model"] == "gpt-5.3-codex"

    def test_force_prompt_handles_non_string_model_gracefully(self, capsys):
        """Should handle non-string model value gracefully when force_prompt=True."""
        existing = {"default_copilot_model": 42}
        models = ["gpt-5.3-codex", "gpt-4o"]
        with patch("agentic_devtools.cli.setup.commands._query_copilot_models", return_value=models):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch("agentic_devtools.cli.config.project_config.save_project_config") as mock_save:
                    with patch("agentic_devtools.cli.setup.commands.input", return_value="1"):
                        _prompt_copilot_model(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["default_copilot_model"] == "gpt-5.3-codex"
