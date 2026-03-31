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
                    _prompt_project_config(force_prompt=True)

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
                    _prompt_project_config(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "EXISTING"
        assert saved["jira_base_url"] == "https://existing.example.com"
        # Optional field is KEPT on empty Enter (sentinel required to clear)
        assert saved["vpn_url"] == "https://vpn.existing.com"

    def test_no_values_stores_empty_strings(self, capsys):
        """Should store all keys as empty strings when no values are provided."""
        inputs = iter(["", "", "", "", ""])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == ""
        assert saved["jira_base_url"] == ""
        assert saved["corporate_network_test_host"] == ""
        assert saved["vpn_url"] == ""
        assert saved["vpn_hostnames"] == ""

    def test_clears_optional_values_with_sentinel(self, capsys):
        """Should store empty string for optional keys when user types '-' sentinel."""
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
                    _prompt_project_config(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        # Required fields kept on empty Enter
        assert saved["jira_project_keys"] == "PROJECT"
        assert saved["jira_base_url"] == "https://jira.example.com"
        # Optional fields cleared via '-' sentinel → stored as ""
        assert saved["vpn_url"] == ""
        assert saved["corporate_network_test_host"] == ""
        assert saved["vpn_hostnames"] == ""

    def test_clears_optional_values_with_clear_sentinel(self, capsys):
        """Should also accept 'clear' as a sentinel to store empty string for optional keys."""
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
                    _prompt_project_config(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "PROJECT"
        assert saved["vpn_url"] == ""

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
                    _prompt_project_config(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        # Required fields retain existing values when sentinel is typed
        assert saved["jira_project_keys"] == "PROJECT"
        assert saved["jira_base_url"] == "https://jira.example.com"

    def test_skips_prompts_when_keys_present(self, capsys):
        """Should skip all prompts when all keys are already present in config."""
        existing = {
            "jira_project_keys": "PROJ",
            "jira_base_url": "https://jira.example.com",
            "corporate_network_test_host": "",
            "vpn_url": "https://vpn.example.com",
            "vpn_hostnames": "",
        }

        mock_input = patch("agentic_devtools.cli.setup.commands.input")
        with mock_input as m_input:
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        m_input.assert_not_called()
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved == existing

    def test_prompts_only_for_absent_keys(self, capsys):
        """Should prompt only for keys not present in existing config."""
        existing = {
            "jira_project_keys": "PROJ",
            "jira_base_url": "https://jira.example.com",
            "corporate_network_test_host": "corp.example.com",
        }
        # Only 2 keys absent: vpn_url and vpn_hostnames
        inputs = iter(["https://vpn.example.com", "vpn1.example.com"])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)) as m_input:
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        assert m_input.call_count == 2
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "PROJ"
        assert saved["jira_base_url"] == "https://jira.example.com"
        assert saved["corporate_network_test_host"] == "corp.example.com"
        assert saved["vpn_url"] == "https://vpn.example.com"
        assert saved["vpn_hostnames"] == "vpn1.example.com"

    def test_force_prompt_re_prompts_all(self, capsys):
        """Should prompt for all keys when force_prompt=True, even if they exist."""
        existing = {
            "jira_project_keys": "PROJ",
            "jira_base_url": "https://jira.example.com",
            "corporate_network_test_host": "corp.example.com",
            "vpn_url": "https://vpn.example.com",
            "vpn_hostnames": "vpn1.example.com",
        }
        inputs = iter(["NEW", "https://new.example.com", "new-corp", "https://new-vpn.example.com", "new-vpn"])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)) as m_input:
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config(force_prompt=True)

        assert m_input.call_count == 5
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "NEW"

    def test_empty_values_stored_not_popped(self, capsys):
        """Should store empty strings and preserve extra keys in config."""
        # Start with an extra key that should survive the save
        inputs = iter(["", "", "", "", ""])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"extra_key": "preserved"},
            ):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        # All 5 prompt keys stored as "" (not popped)
        assert saved["jira_project_keys"] == ""
        assert saved["jira_base_url"] == ""
        assert saved["corporate_network_test_host"] == ""
        assert saved["vpn_url"] == ""
        assert saved["vpn_hostnames"] == ""
        # Extra key preserved
        assert saved["extra_key"] == "preserved"

    def test_skip_path_normalises_none_to_empty_string(self, capsys):
        """Should normalise None values to empty string in the skip path."""
        existing = {
            "jira_project_keys": None,
            "jira_base_url": "https://jira.example.com",
            "corporate_network_test_host": None,
            "vpn_url": "",
            "vpn_hostnames": "host.example.com",
        }

        mock_input = patch("agentic_devtools.cli.setup.commands.input")
        with mock_input as m_input:
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        m_input.assert_not_called()
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        # None normalised to ""
        assert saved["jira_project_keys"] == ""
        assert saved["corporate_network_test_host"] == ""
        # Non-None values preserved as-is
        assert saved["jira_base_url"] == "https://jira.example.com"
        assert saved["vpn_url"] == ""
        assert saved["vpn_hostnames"] == "host.example.com"

    def test_skip_path_normalises_non_string_to_str(self, capsys):
        """Should coerce non-string values (e.g. int) to str in the skip path."""
        existing = {
            "jira_project_keys": 42,
            "jira_base_url": "https://jira.example.com",
            "corporate_network_test_host": "",
            "vpn_url": "",
            "vpn_hostnames": "",
        }

        mock_input = patch("agentic_devtools.cli.setup.commands.input")
        with mock_input as m_input:
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config()

        m_input.assert_not_called()
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "42"

    def test_prompt_path_normalises_none_current_value(self, capsys):
        """Should normalise None current value to empty string in the prompt path."""
        existing = {
            "jira_project_keys": None,
            "jira_base_url": None,
        }
        # force_prompt=True forces prompt path; absent keys also prompt
        inputs = iter(["NEW_KEY", "https://new.example.com", "corp", "vpn", "hosts"])

        with patch("agentic_devtools.cli.setup.commands.input", side_effect=lambda _: next(inputs)):
            with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value=existing):
                with patch(
                    "agentic_devtools.cli.config.project_config.save_project_config", return_value="/fake/path"
                ) as mock_save:
                    _prompt_project_config(force_prompt=True)

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["jira_project_keys"] == "NEW_KEY"
        assert saved["jira_base_url"] == "https://new.example.com"
