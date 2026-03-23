"""Tests for _prompt_project_config."""

from unittest.mock import patch

from agentic_devtools.cli.setup.commands import _prompt_project_config


class TestPromptProjectConfig:
    """Tests for _prompt_project_config."""

    def test_saves_config_when_values_provided(self, tmp_path, capsys):
        """Should save provided values to project config."""
        inputs = iter(
            [
                "ACME,PROJ",
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
        assert saved["jira_project_keys"] == "ACME,PROJ"
        assert saved["jira_base_url"] == "https://jira.example.com"
        assert saved["corporate_network_test_host"] == "corp.example.com"
        assert saved["vpn_url"] == "https://vpn.example.com"
        assert saved["vpn_hostnames"] == "jira.example.com,corp.example.com"

        out = capsys.readouterr().out
        assert "Project configuration saved" in out

    def test_keeps_existing_values_on_empty_input(self, capsys):
        """Should keep existing config values when user presses Enter."""
        existing = {
            "jira_project_keys": "EXISTING",
            "jira_base_url": "https://existing.example.com",
            "vpn_url": "https://vpn.existing.com",
        }
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
        # Optional field is KEPT on empty Enter (sentinel required to clear)
        assert saved["vpn_url"] == "https://vpn.existing.com"

    def test_no_values_prints_info_message(self, capsys):
        """Should print info message when no values are provided and no existing config."""
        inputs = iter(["", "", "", "", ""])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                _prompt_project_config()

        out = capsys.readouterr().out
        assert "No project configuration values provided" in out

    def test_clears_optional_values_with_sentinel(self, capsys):
        """Should remove optional keys when user types '-' sentinel."""
        existing = {
            "jira_project_keys": "PROJECT",
            "jira_base_url": "https://jira.example.com",
            "vpn_url": "https://vpn.example.com",
            "corporate_network_test_host": "corp.example.com",
        }
        # Type '-' for optional fields to clear them, empty for required to keep
        inputs = iter(["", "", "-", "-", "-"])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        # Required fields kept on empty Enter
        assert saved["jira_project_keys"] == "PROJECT"
        assert saved["jira_base_url"] == "https://jira.example.com"
        # Optional fields cleared via '-' sentinel
        assert "vpn_url" not in saved
        assert "corporate_network_test_host" not in saved
        assert "vpn_hostnames" not in saved

    def test_clears_optional_values_with_clear_sentinel(self, capsys):
        """Should also accept 'clear' as a sentinel to remove optional keys."""
        existing = {
            "jira_project_keys": "PROJECT",
            "jira_base_url": "https://jira.example.com",
            "vpn_url": "https://vpn.example.com",
        }
        inputs = iter(["", "", "", "clear", ""])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "PROJECT"
        assert "vpn_url" not in saved

    def test_rejects_sentinel_for_required_fields(self, capsys):
        """Should ignore '-'/'clear' sentinels for required fields and keep existing value."""
        existing = {
            "jira_project_keys": "PROJECT",
            "jira_base_url": "https://jira.example.com",
        }
        # Type '-' for jira_keys and 'clear' for jira_base_url — both required
        inputs = iter(["-", "clear", "", "", ""])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        # Required fields retain existing values when sentinel is typed
        assert saved["jira_project_keys"] == "PROJECT"
        assert saved["jira_base_url"] == "https://jira.example.com"
