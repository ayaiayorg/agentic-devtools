"""Tests for _prompt_project_config."""

from unittest.mock import patch

from agentic_devtools.cli.setup.commands import _prompt_project_config


class TestPromptProjectConfig:
    """Tests for _prompt_project_config."""

    def test_saves_config_when_values_provided(self, tmp_path, capsys):
        """Should save provided values to project config."""
        inputs = iter(
            [
                "DFLY,PROJ",
                "https://jira.example.com",
                "corp.example.com",
                "https://vpn.example.com",
                "jira.example.com,corp.example.com",
            ]
        )

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config",
                    return_value=tmp_path / "project.json",
                ) as mock_save:
                    _prompt_project_config()

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "DFLY,PROJ"
        assert saved["jira_base_url"] == "https://jira.example.com"
        assert saved["corporate_network_test_host"] == "corp.example.com"
        assert saved["vpn_url"] == "https://vpn.example.com"
        assert saved["vpn_hostnames"] == "jira.example.com,corp.example.com"

        out = capsys.readouterr().out
        assert "Project configuration saved" in out

    def test_keeps_existing_values_on_empty_input(self, capsys):
        """Should keep existing config values when user presses Enter."""
        existing = {"jira_project_keys": "EXISTING", "jira_base_url": "https://existing.example.com"}
        inputs = iter(["", "", "", "", ""])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "EXISTING"
        assert saved["jira_base_url"] == "https://existing.example.com"

    def test_no_values_prints_info_message(self, capsys):
        """Should print info message when no values are provided and no existing config."""
        inputs = iter(["", "", "", "", ""])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                _prompt_project_config()

        out = capsys.readouterr().out
        assert "No project configuration values provided" in out

    def test_removes_cleared_values(self, capsys):
        """Should remove optional keys when user enters empty for allow_clear fields."""
        existing = {
            "jira_project_keys": "DFLY",
            "jira_base_url": "https://jira.example.com",
            "vpn_url": "https://vpn.example.com",
        }
        # Enter empty for all: jira_project_keys and jira_base_url keep existing (not allow_clear),
        # corporate_network_test_host/vpn_url/vpn_hostnames clear (allow_clear=True)
        inputs = iter(["", "", "", "", ""])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        # Non-clearable fields keep existing values
        assert saved["jira_project_keys"] == "DFLY"
        assert saved["jira_base_url"] == "https://jira.example.com"
        # Clearable field with existing value was removed (empty input + allow_clear)
        assert "vpn_url" not in saved
