"""
Tests for dfly-ai-helpers state management.
"""

from unittest.mock import patch

import pytest

from agdt_ai_helpers import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


class TestStateManagement:
    """Tests for basic state operations."""

    def test_set_and_get_value(self, temp_state_dir):
        """Test setting and getting a simple value."""
        state.set_value("test_key", "test_value")
        assert state.get_value("test_key") == "test_value"

    def test_get_nonexistent_key_returns_none(self, temp_state_dir):
        """Test that getting a nonexistent key returns None."""
        assert state.get_value("nonexistent") is None

    def test_get_required_key_raises_error(self, temp_state_dir):
        """Test that getting a required nonexistent key raises KeyError."""
        with pytest.raises(KeyError, match="Required state key not found"):
            state.get_value("nonexistent", required=True)

    def test_delete_existing_key(self, temp_state_dir):
        """Test deleting an existing key."""
        state.set_value("to_delete", "value")
        assert state.delete_value("to_delete") is True
        assert state.get_value("to_delete") is None

    def test_delete_nonexistent_key(self, temp_state_dir):
        """Test deleting a nonexistent key returns False."""
        assert state.delete_value("nonexistent") is False

    def test_clear_state(self, temp_state_dir):
        """Test clearing all state."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        state.clear_state()
        assert state.load_state() == {}

    def test_load_state_returns_dict(self, temp_state_dir):
        """Test that load_state returns a dictionary."""
        state.set_value("test", "value")
        loaded = state.load_state()
        assert isinstance(loaded, dict)
        assert loaded["test"] == "value"

    def test_get_all_keys(self, temp_state_dir):
        """Test getting all keys in state."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        keys = state.get_all_keys()
        assert set(keys) == {"key1", "key2"}


class TestSpecialCharacters:
    """Tests for handling special characters in content."""

    def test_parentheses_in_content(self, temp_state_dir):
        """Test that parentheses are preserved."""
        content = "This (has) parentheses"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_brackets_in_content(self, temp_state_dir):
        """Test that brackets are preserved."""
        content = "Array [0] and [1]"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_braces_in_content(self, temp_state_dir):
        """Test that braces are preserved."""
        content = "Object {key: value}"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_mixed_special_characters(self, temp_state_dir):
        """Test mixed special characters."""
        content = "func(arg) { return array[0]; }"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_unicode_characters(self, temp_state_dir):
        """Test Unicode characters are preserved."""
        content = "Größe Übung Äpfel 你好 🎉"
        state.set_value("content", content)
        assert state.get_value("content") == content


class TestMultilineContent:
    """Tests for handling multiline content."""

    def test_simple_multiline(self, temp_state_dir):
        """Test simple multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_multiline_with_empty_lines(self, temp_state_dir):
        """Test multiline with empty lines."""
        content = "Line 1\n\nLine 3 after empty"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_multiline_with_special_chars(self, temp_state_dir):
        """Test multiline with special characters."""
        content = """Thanks for the feedback!

I've fixed the issue:
- Updated function(arg)
- Fixed array[0] access
- Changed {config}"""
        state.set_value("content", content)
        assert state.get_value("content") == content


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_pull_request_id(self, temp_state_dir):
        """Test pull request ID functions."""
        state.set_pull_request_id(12345)
        assert state.get_pull_request_id() == 12345

    def test_thread_id(self, temp_state_dir):
        """Test thread ID functions."""
        state.set_thread_id(67890)
        assert state.get_thread_id() == 67890

    def test_dry_run_boolean(self, temp_state_dir):
        """Test dry run with boolean."""
        state.set_dry_run(True)
        assert state.is_dry_run() is True
        state.set_dry_run(False)
        assert state.is_dry_run() is False

    def test_dry_run_string(self, temp_state_dir):
        """Test dry run with string values."""
        state.set_value("dry_run", "true")
        assert state.is_dry_run() is True
        state.set_value("dry_run", "1")
        assert state.is_dry_run() is True
        state.set_value("dry_run", "false")
        assert state.is_dry_run() is False

    def test_resolve_thread(self, temp_state_dir):
        """Test resolve thread functions."""
        state.set_resolve_thread(True)
        assert state.should_resolve_thread() is True
        state.set_resolve_thread(False)
        assert state.should_resolve_thread() is False


class TestJSONTypes:
    """Tests for different JSON types."""

    def test_integer_value(self, temp_state_dir):
        """Test integer values."""
        state.set_value("count", 42)
        assert state.get_value("count") == 42

    def test_float_value(self, temp_state_dir):
        """Test float values."""
        state.set_value("ratio", 3.14)
        assert state.get_value("ratio") == 3.14

    def test_boolean_value(self, temp_state_dir):
        """Test boolean values."""
        state.set_value("flag", True)
        assert state.get_value("flag") is True

    def test_list_value(self, temp_state_dir):
        """Test list values."""
        items = ["a", "b", "c"]
        state.set_value("items", items)
        assert state.get_value("items") == items

    def test_dict_value(self, temp_state_dir):
        """Test dictionary values."""
        config = {"key": "value", "nested": {"inner": 1}}
        state.set_value("config", config)
        assert state.get_value("config") == config


class TestCliStateCommands:
    """Tests for CLI state commands."""

    def test_get_cmd_missing_key_exits_with_error(self, temp_state_dir):
        """Test that get_cmd exits with error when no key provided."""
        from agdt_ai_helpers.cli.state import get_cmd

        with patch("sys.argv", ["agdt-get"]):
            with pytest.raises(SystemExit) as exc_info:
                get_cmd()
            assert exc_info.value.code == 1

    def test_delete_cmd_missing_key_exits_with_error(self, temp_state_dir):
        """Test that delete_cmd exits with error when no key provided."""
        from agdt_ai_helpers.cli.state import delete_cmd

        with patch("sys.argv", ["agdt-delete"]):
            with pytest.raises(SystemExit) as exc_info:
                delete_cmd()
            assert exc_info.value.code == 1


class TestStateDirResolution:
    """Tests for state directory resolution edge cases."""

    def test_env_var_state_dir(self, tmp_path):
        """Test that DFLY_AI_HELPERS_STATE_DIR environment variable is used."""
        custom_dir = tmp_path / "custom_state"
        with patch.dict("os.environ", {"DFLY_AI_HELPERS_STATE_DIR": str(custom_dir)}):
            result = state.get_state_dir()
            assert result == custom_dir
            assert custom_dir.exists()

    def test_finds_existing_scripts_temp(self, tmp_path, monkeypatch):
        """Test that existing scripts/temp is found and used."""
        # Create a project with existing scripts/temp
        project_dir = tmp_path / "project"
        scripts_temp = project_dir / "scripts" / "temp"
        scripts_temp.mkdir(parents=True)

        work_dir = project_dir / "src" / "app"
        work_dir.mkdir(parents=True)

        monkeypatch.chdir(work_dir)
        monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

        result = state.get_state_dir()
        assert result == scripts_temp

    def test_fallback_dir_when_no_scripts_temp(self, tmp_path, monkeypatch):
        """Test fallback to .agdt-temp when scripts/temp not found."""
        # Create an isolated working directory with no scripts/temp
        isolated_dir = tmp_path / "isolated"
        isolated_dir.mkdir()

        monkeypatch.chdir(isolated_dir)
        # Clear any env var
        monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

        result = state.get_state_dir()
        assert result.name == ".agdt-temp"
        assert result.exists()

    def test_scripts_dir_creates_temp(self, tmp_path, monkeypatch):
        """Test that temp is created when inside scripts directory."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        monkeypatch.chdir(scripts_dir)
        monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

        result = state.get_state_dir()
        assert result == scripts_dir / "temp"
        assert result.exists()

    def test_creates_temp_when_scripts_exists_but_temp_missing(self, tmp_path, monkeypatch):
        """Test that scripts/temp is created when scripts exists but temp doesn't.

        This is the key fix for multi-worktree support: new worktrees have a scripts
        directory (tracked in git) but scripts/temp doesn't exist (gitignored).
        The get_state_dir function should create scripts/temp automatically.
        """
        # Create a project with scripts directory but no temp subdirectory
        project_dir = tmp_path / "project"
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Put a file in scripts to confirm it's a valid scripts directory
        (scripts_dir / "some_helper.py").touch()

        work_dir = project_dir / "src" / "app"
        work_dir.mkdir(parents=True)

        monkeypatch.chdir(work_dir)
        monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

        result = state.get_state_dir()
        expected_temp = scripts_dir / "temp"
        assert result == expected_temp
        assert expected_temp.exists(), "scripts/temp should be created automatically"


class TestLoadStateEdgeCases:
    """Tests for load_state edge cases."""

    def test_load_state_handles_corrupt_json(self, temp_state_dir):
        """Test that corrupt JSON returns empty dict."""
        state_file = temp_state_dir / "agdt-state.json"
        state_file.write_text("{ invalid json", encoding="utf-8")

        result = state.load_state()
        assert result == {}


class TestDeleteNestedKey:
    """Tests for deleting nested keys."""

    def test_delete_nested_key_success(self, temp_state_dir):
        """Test deleting a nested key."""
        state.set_value("parent", {"child": "value", "other": "keep"})
        result = state.delete_value("parent.child")
        assert result is True
        assert state.get_value("parent") == {"other": "keep"}

    def test_delete_nested_key_missing_parent(self, temp_state_dir):
        """Test deleting nested key when parent doesn't exist."""
        result = state.delete_value("nonexistent.child")
        assert result is False

    def test_delete_nested_key_missing_child(self, temp_state_dir):
        """Test deleting nested key when child doesn't exist."""
        state.set_value("parent", {"other": "value"})
        result = state.delete_value("parent.nonexistent")
        assert result is False

    def test_delete_deeply_nested_key(self, temp_state_dir):
        """Test deleting a deeply nested key."""
        state.set_value("a", {"b": {"c": {"d": "deep"}}})
        result = state.delete_value("a.b.c.d")
        assert result is True
        assert state.get_value("a.b.c") == {}


class TestIsTruthyEdgeCases:
    """Tests for is_truthy edge cases."""

    def test_is_dry_run_with_yes_string(self, temp_state_dir):
        """Test that 'yes' is treated as truthy."""
        state.set_value("dry_run", "yes")
        assert state.is_dry_run() is True

    def test_resolve_thread_with_numeric_one(self, temp_state_dir):
        """Test that numeric 1 is treated as truthy."""
        state.set_value("resolve_thread", "1")
        assert state.should_resolve_thread() is True


class TestClearTempFolder:
    """Tests for clear_temp_folder function."""

    def test_clear_temp_folder_removes_state_file(self, temp_state_dir):
        """Test that clear_temp_folder removes the state file."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")

        # Verify state exists
        assert state.get_value("key1") == "value1"

        # Clear temp folder
        state.clear_temp_folder()

        # State should be empty
        assert state.get_value("key1") is None
        assert state.get_value("key2") is None

    def test_clear_temp_folder_removes_other_files(self, temp_state_dir):
        """Test that clear_temp_folder removes other files in temp directory."""
        # Create some temp files
        (temp_state_dir / "temp-file.json").write_text("{}", encoding="utf-8")
        (temp_state_dir / "another-file.txt").write_text("content", encoding="utf-8")

        # Verify files exist
        assert (temp_state_dir / "temp-file.json").exists()
        assert (temp_state_dir / "another-file.txt").exists()

        # Clear temp folder
        state.clear_temp_folder()

        # All files should be removed
        # Only agdt-state.json might exist (empty) after clearing
        remaining_files = list(temp_state_dir.iterdir())
        # The state file should be recreated by load_state, but be empty
        assert len(remaining_files) <= 1
        assert state.load_state() == {}

    def test_clear_temp_folder_removes_subdirectories(self, temp_state_dir):
        """Test that clear_temp_folder removes subdirectories."""
        # Create a subdirectory with files
        subdir = temp_state_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested-file.json").write_text("{}", encoding="utf-8")

        # Verify exists
        assert subdir.exists()

        # Clear temp folder
        state.clear_temp_folder()

        # Subdirectory should be removed
        assert not subdir.exists()

    def test_clear_temp_folder_with_preserve_keys(self, temp_state_dir):
        """Test that clear_temp_folder preserves specified keys."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        state.set_value("key3", "value3")

        # Clear with preserved keys
        state.clear_temp_folder(preserve_keys={"key1": "value1", "key3": "preserved"})

        # key1 should be preserved, key2 deleted, key3 overwritten
        assert state.get_value("key1") == "value1"
        assert state.get_value("key2") is None
        assert state.get_value("key3") == "preserved"

    def test_clear_temp_folder_preserves_nested_keys(self, temp_state_dir):
        """Test that clear_temp_folder preserves nested keys correctly."""
        state.set_value("jira.issue_key", "DFLY-1234")
        state.set_value("jira.summary", "Test summary")
        state.set_value("other", "value")

        # Clear with preserved nested keys
        state.clear_temp_folder(preserve_keys={"jira": {"issue_key": "DFLY-5678"}})

        # Only the preserved nested key should exist
        assert state.get_value("jira.issue_key") == "DFLY-5678"
        assert state.get_value("jira.summary") is None
        assert state.get_value("other") is None

    def test_clear_temp_folder_recreates_directory(self, temp_state_dir):
        """Test that clear_temp_folder recreates the temp directory."""
        state.set_value("key", "value")

        # Clear temp folder
        state.clear_temp_folder()

        # Directory should still exist
        assert temp_state_dir.exists()

        # Should be able to set new values
        state.set_value("new_key", "new_value")
        assert state.get_value("new_key") == "new_value"

    def test_clear_temp_folder_handles_missing_directory(self, tmp_path):
        """Test that clear_temp_folder handles missing directory gracefully."""
        missing_dir = tmp_path / "nonexistent"

        with patch.object(state, "get_state_dir", return_value=missing_dir):
            # Should not raise
            state.clear_temp_folder()

            # Directory should be created
            assert missing_dir.exists()


class TestSetContextValue:
    """Tests for set_context_value function."""

    def test_set_context_value_rejects_non_context_keys(self, temp_state_dir):
        """Test that set_context_value only accepts context keys."""
        with pytest.raises(ValueError, match="set_context_value only accepts"):
            state.set_context_value("some_other_key", "value")

    def test_set_context_value_pull_request_id(self, temp_state_dir):
        """Test setting pull_request_id via set_context_value."""
        result = state.set_context_value("pull_request_id", 12345, verbose=False)

        assert result is True
        assert state.get_value("pull_request_id") == 12345

    def test_set_context_value_jira_issue_key(self, temp_state_dir):
        """Test setting jira.issue_key via set_context_value."""
        result = state.set_context_value("jira.issue_key", "DFLY-1234", verbose=False)

        assert result is True
        assert state.get_value("jira.issue_key") == "DFLY-1234"

    def test_set_context_value_jira_issue_key_change_preserves_new_key(self, temp_state_dir):
        """Test changing jira.issue_key preserves the new key after clearing."""
        # Set initial jira issue key
        state.set_value("jira.issue_key", "DFLY-OLD")
        state.set_value("pull_request_id", 12345)
        state.set_value("other_data", "should be cleared")

        # Change jira issue key - should clear temp folder but preserve new key
        with patch.object(state, "_trigger_cross_lookup"):
            result = state.set_context_value("jira.issue_key", "DFLY-NEW", verbose=False)

        assert result is True
        # New jira key should be preserved
        assert state.get_value("jira.issue_key") == "DFLY-NEW"
        # Old PR ID should be cleared
        assert state.get_value("pull_request_id") is None
        # Other data should be cleared
        assert state.get_value("other_data") is None

    def test_set_context_value_no_change_returns_false(self, temp_state_dir):
        """Test that setting same value returns False (no change)."""
        # Set initial value
        state.set_value("pull_request_id", 12345)

        # Set same value via set_context_value
        result = state.set_context_value("pull_request_id", 12345, verbose=False)

        # Should return False (no change)
        assert result is False

    def test_set_context_value_no_change_preserves_other_state(self, temp_state_dir):
        """Test that setting same value doesn't clear other state."""
        # Set up initial state
        state.set_value("pull_request_id", 12345)
        state.set_value("other_key", "should_persist")

        # Set same value
        state.set_context_value("pull_request_id", 12345, verbose=False)

        # Other state should be preserved
        assert state.get_value("other_key") == "should_persist"

    def test_set_context_value_change_clears_temp(self, temp_state_dir):
        """Test that changing context value clears temp folder."""
        # Set up initial state
        state.set_value("pull_request_id", 12345)
        state.set_value("other_key", "should_be_cleared")

        # Create a temp file to verify clearing
        (temp_state_dir / "temp-data.json").write_text("{}", encoding="utf-8")

        # Change value
        with patch.object(state, "_trigger_cross_lookup"):
            result = state.set_context_value("pull_request_id", 99999, verbose=False)

        # Should return True (changed)
        assert result is True

        # New value should be set
        assert state.get_value("pull_request_id") == 99999

        # Other state should be cleared
        assert state.get_value("other_key") is None

        # Temp file should be removed
        assert not (temp_state_dir / "temp-data.json").exists()

    def test_set_context_value_change_preserves_new_value(self, temp_state_dir):
        """Test that the new context value is preserved during clearing."""
        state.set_value("pull_request_id", 12345)
        state.set_value("jira.issue_key", "DFLY-OLD")

        with patch.object(state, "_trigger_cross_lookup"):
            state.set_context_value("pull_request_id", 99999, verbose=False)

        # New PR ID should be preserved
        assert state.get_value("pull_request_id") == 99999

        # Old Jira key should be cleared
        assert state.get_value("jira.issue_key") is None

    def test_set_context_value_string_to_int_comparison(self, temp_state_dir):
        """Test that string/int values are normalized for comparison."""
        # Set as string
        state.set_value("pull_request_id", "12345")

        # Try to set as int - should detect as same value
        result = state.set_context_value("pull_request_id", 12345, verbose=False)

        # Values are normalized to string, so this is NOT a change
        assert result is False

    def test_set_context_value_triggers_cross_lookup(self, temp_state_dir):
        """Test that set_context_value triggers cross-lookup when enabled."""
        with patch.object(state, "_trigger_cross_lookup") as mock_lookup:
            state.set_context_value(
                "pull_request_id",
                12345,
                verbose=False,
                trigger_cross_lookup=True,
            )

            mock_lookup.assert_called_once_with("pull_request_id", 12345, False)

    def test_set_context_value_no_cross_lookup_when_disabled(self, temp_state_dir):
        """Test that cross-lookup is not triggered when disabled."""
        with patch.object(state, "_trigger_cross_lookup") as mock_lookup:
            state.set_context_value(
                "pull_request_id",
                12345,
                verbose=False,
                trigger_cross_lookup=False,
            )

            mock_lookup.assert_not_called()

    def test_set_context_value_no_cross_lookup_on_same_value(self, temp_state_dir):
        """Test that cross-lookup is not triggered when value unchanged."""
        state.set_value("pull_request_id", 12345)

        with patch.object(state, "_trigger_cross_lookup") as mock_lookup:
            state.set_context_value(
                "pull_request_id",
                12345,
                verbose=False,
                trigger_cross_lookup=True,
            )

            # Should not be called because value didn't change
            mock_lookup.assert_not_called()

    def test_set_context_value_verbose_output(self, temp_state_dir, capsys):
        """Test verbose output during context switching."""
        state.set_value("pull_request_id", 12345)

        with patch.object(state, "_trigger_cross_lookup"):
            state.set_context_value("pull_request_id", 99999, verbose=True)

        captured = capsys.readouterr()
        assert "Context switch" in captured.out
        assert "12345" in captured.out
        assert "99999" in captured.out

    def test_set_context_value_verbose_first_set(self, temp_state_dir, capsys):
        """Test verbose output when setting context for first time."""
        with patch.object(state, "_trigger_cross_lookup"):
            state.set_context_value("pull_request_id", 12345, verbose=True)

        captured = capsys.readouterr()
        assert "Setting context" in captured.out
        assert "12345" in captured.out

    def test_set_context_value_verbose_unchanged(self, temp_state_dir, capsys):
        """Test verbose output when value unchanged."""
        state.set_value("pull_request_id", 12345)

        state.set_context_value("pull_request_id", 12345, verbose=True)

        captured = capsys.readouterr()
        assert "unchanged" in captured.out


class TestTriggerCrossLookup:
    """Tests for _trigger_cross_lookup function."""

    def test_trigger_cross_lookup_pr_to_jira(self, temp_state_dir, capsys):
        """Test that PR change triggers Jira lookup."""
        with patch("agdt_ai_helpers.state._start_jira_lookup_from_pr") as mock_jira_lookup:
            state._trigger_cross_lookup("pull_request_id", 12345, verbose=True)

            mock_jira_lookup.assert_called_once_with(12345)

        captured = capsys.readouterr()
        assert "Starting background lookup for Jira issue from PR" in captured.out

    def test_trigger_cross_lookup_jira_to_pr(self, temp_state_dir, capsys):
        """Test that Jira change triggers PR lookup."""
        with patch("agdt_ai_helpers.state._start_pr_lookup_from_jira") as mock_pr_lookup:
            state._trigger_cross_lookup("jira.issue_key", "DFLY-1234", verbose=True)

            mock_pr_lookup.assert_called_once_with("DFLY-1234")

        captured = capsys.readouterr()
        assert "Starting background lookup for PR from Jira issue" in captured.out

    def test_trigger_cross_lookup_unknown_key_does_nothing(self, temp_state_dir, capsys):
        """Test that unknown key does nothing (early exit)."""
        # This tests the implicit else branch (360->exit) in _trigger_cross_lookup
        with patch("agdt_ai_helpers.state._start_jira_lookup_from_pr") as mock_jira:
            with patch("agdt_ai_helpers.state._start_pr_lookup_from_jira") as mock_pr:
                state._trigger_cross_lookup("unknown_key", "value", verbose=True)

                mock_jira.assert_not_called()
                mock_pr.assert_not_called()

        # No output since neither branch was taken
        captured = capsys.readouterr()
        assert captured.out == ""


class TestStartJiraLookupFromPr:
    """Tests for _start_jira_lookup_from_pr function."""

    def test_start_jira_lookup_calls_async_function(self, temp_state_dir):
        """Test that _start_jira_lookup_from_pr calls async lookup."""
        with patch("agdt_ai_helpers.cli.azure_devops.async_commands.lookup_jira_issue_from_pr_async") as mock_async:
            state._start_jira_lookup_from_pr(12345)

            mock_async.assert_called_once_with(12345)

    def test_start_jira_lookup_handles_import_error(self, temp_state_dir):
        """Test that _start_jira_lookup_from_pr handles ImportError gracefully."""
        # Patch at the import location within the function
        with patch.dict("sys.modules", {"agdt_ai_helpers.cli.azure_devops.async_commands": None}):
            # Should not raise
            state._start_jira_lookup_from_pr(12345)

    def test_start_jira_lookup_handles_exception(self, temp_state_dir):
        """Test that _start_jira_lookup_from_pr handles exceptions gracefully."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.async_commands.lookup_jira_issue_from_pr_async",
            side_effect=Exception("Network error"),
        ):
            # Should not raise
            state._start_jira_lookup_from_pr(12345)


class TestStartPrLookupFromJira:
    """Tests for _start_pr_lookup_from_jira function."""

    def test_start_pr_lookup_calls_async_function(self, temp_state_dir):
        """Test that _start_pr_lookup_from_jira calls async lookup."""
        with patch("agdt_ai_helpers.cli.azure_devops.async_commands.lookup_pr_from_jira_issue_async") as mock_async:
            state._start_pr_lookup_from_jira("DFLY-1234")

            mock_async.assert_called_once_with("DFLY-1234")

    def test_start_pr_lookup_handles_import_error(self, temp_state_dir):
        """Test that _start_pr_lookup_from_jira handles ImportError gracefully."""
        # Patch at the import location within the function
        with patch.dict("sys.modules", {"agdt_ai_helpers.cli.azure_devops.async_commands": None}):
            # Should not raise
            state._start_pr_lookup_from_jira("DFLY-1234")

    def test_start_pr_lookup_handles_exception(self, temp_state_dir):
        """Test that _start_pr_lookup_from_jira handles exceptions gracefully."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.async_commands.lookup_pr_from_jira_issue_async",
            side_effect=Exception("Network error"),
        ):
            # Should not raise
            state._start_pr_lookup_from_jira("DFLY-1234")


class TestGetGitRepoRoot:
    """Tests for _get_git_repo_root function."""

    def test_returns_path_when_in_git_repo(self, tmp_path):
        """Test returns Path when git command succeeds."""
        from unittest.mock import MagicMock

        with patch("agdt_ai_helpers.state.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = str(tmp_path) + "\n"
            mock_run.return_value = mock_result

            result = state._get_git_repo_root()

            assert result == tmp_path
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_returns_none_when_not_in_git_repo(self):
        """Test returns None when git command fails (not in repo)."""
        from unittest.mock import MagicMock

        with patch("agdt_ai_helpers.state.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 128  # Git error: not in repo
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            result = state._get_git_repo_root()

            assert result is None

    def test_returns_none_when_git_not_found(self):
        """Test returns None when git command is not found."""
        with patch("agdt_ai_helpers.state.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")

            result = state._get_git_repo_root()

            assert result is None

    def test_returns_none_on_os_error(self):
        """Test returns None when OSError occurs."""
        with patch("agdt_ai_helpers.state.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")

            result = state._get_git_repo_root()

            assert result is None

    def test_returns_none_when_stdout_empty(self):
        """Test returns None when git returns empty stdout."""
        from unittest.mock import MagicMock

        with patch("agdt_ai_helpers.state.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "   \n"  # Only whitespace
            mock_run.return_value = mock_result

            result = state._get_git_repo_root()

            assert result is None


class TestGetStateDirWithGit:
    """Tests for get_state_dir using git-based detection."""

    def test_uses_git_repo_root_when_available(self, tmp_path):
        """Test that get_state_dir uses git repo root when available."""
        # Create scripts/temp structure
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / "scripts" / "temp"
                assert result.exists()

    def test_falls_back_to_dfly_temp_when_no_scripts_dir(self, tmp_path):
        """Test that get_state_dir falls back to .agdt-temp when no scripts dir found."""
        # Create a directory structure WITHOUT scripts folder
        subdir = tmp_path / "deep" / "nested" / "path"
        subdir.mkdir(parents=True)

        with patch.object(state, "_get_git_repo_root", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=subdir):
                    result = state.get_state_dir()

                    # Should fall back to .agdt-temp since no scripts dir in parent chain
                    assert ".agdt-temp" in str(result)

    def test_env_var_takes_precedence_over_git(self, tmp_path):
        """Test that DFLY_AI_HELPERS_STATE_DIR env var takes precedence."""
        env_dir = tmp_path / "custom_state"

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path / "repo"):
            with patch.dict("os.environ", {"DFLY_AI_HELPERS_STATE_DIR": str(env_dir)}):
                result = state.get_state_dir()

                assert result == env_dir
                assert result.exists()

    def test_git_root_without_scripts_dir_falls_back(self, tmp_path):
        """Test fallback when git root exists but has no scripts directory."""
        # Git root without scripts directory
        git_root = tmp_path / "repo_no_scripts"
        git_root.mkdir()

        # Create a different structure with scripts in parent chain for cwd fallback
        cwd = tmp_path / "cwd"
        cwd.mkdir()

        with patch.object(state, "_get_git_repo_root", return_value=git_root):
            with patch.dict("os.environ", {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=cwd):
                    result = state.get_state_dir()

                    # Should fall back to .agdt-temp since git root has no scripts dir
                    # and cwd walk doesn't find scripts either
                    assert ".agdt-temp" in str(result)


class TestFileLocking:
    """Tests for file locking functions."""

    def test_load_state_with_locking(self, temp_state_dir):
        """Test load_state with use_locking=True."""
        # First save some state
        state.save_state({"test_key": "test_value"})

        # Load with locking enabled
        loaded = state.load_state(use_locking=True)
        assert loaded == {"test_key": "test_value"}

    def test_save_state_with_locking(self, temp_state_dir):
        """Test save_state with use_locking=True."""
        # Save with locking enabled
        state.save_state({"locked_key": "locked_value"}, use_locking=True)

        # Verify it was saved correctly
        loaded = state.load_state()
        assert loaded == {"locked_key": "locked_value"}

    def test_load_state_locked_convenience(self, temp_state_dir):
        """Test load_state_locked convenience function."""
        state.save_state({"key": "value"})

        loaded = state.load_state_locked()
        assert loaded == {"key": "value"}

    def test_save_state_locked_convenience(self, temp_state_dir):
        """Test save_state_locked convenience function."""
        path = state.save_state_locked({"key": "value"})

        assert path.exists()
        loaded = state.load_state()
        assert loaded == {"key": "value"}

    def test_load_state_filelock_error_fallback(self, temp_state_dir):
        """Test that load_state falls back to unlocked read on FileLockError."""
        from agdt_ai_helpers.file_locking import FileLockError

        state.save_state({"fallback_key": "fallback_value"})

        # Mock locked_state_file to raise FileLockError
        with patch.object(state, "locked_state_file") as mock_lock:
            mock_lock.side_effect = FileLockError("Lock timeout")

            # Should still return the data via unlocked fallback
            loaded = state.load_state(use_locking=True)
            assert loaded == {"fallback_key": "fallback_value"}

    def test_save_state_filelock_error_fallback(self, temp_state_dir):
        """Test that save_state falls back to unlocked write on FileLockError."""
        from agdt_ai_helpers.file_locking import FileLockError

        # Mock locked_state_file to raise FileLockError
        with patch.object(state, "locked_state_file") as mock_lock:
            mock_lock.side_effect = FileLockError("Lock timeout")

            # Should still save via unlocked fallback
            state.save_state({"fallback_save": "value"}, use_locking=True)

            # Verify it was saved
            loaded = state.load_state()
            assert loaded == {"fallback_save": "value"}


class TestWorkflowState:
    """Tests for workflow state management."""

    def test_get_workflow_state_when_none(self, temp_state_dir):
        """Test get_workflow_state returns None when no workflow active."""
        assert state.get_workflow_state() is None

    def test_set_and_get_workflow_state(self, temp_state_dir):
        """Test setting and getting workflow state."""
        state.set_workflow_state(
            name="test-workflow",
            status="in-progress",
            step="step-1",
            context={"key": "value"},
        )

        workflow = state.get_workflow_state()
        assert workflow["active"] == "test-workflow"
        assert workflow["status"] == "in-progress"
        assert workflow["step"] == "step-1"
        assert workflow["context"] == {"key": "value"}
        assert "started_at" in workflow

    def test_set_workflow_state_preserves_started_at(self, temp_state_dir):
        """Test that updating workflow preserves original started_at."""
        state.set_workflow_state(name="test-workflow", status="initiated")
        original_started = state.get_workflow_state()["started_at"]

        # Update the same workflow
        state.set_workflow_state(name="test-workflow", status="in-progress")
        updated_started = state.get_workflow_state()["started_at"]

        assert original_started == updated_started

    def test_set_workflow_state_merges_context(self, temp_state_dir):
        """Test that context is merged when updating same workflow."""
        state.set_workflow_state(
            name="test-workflow",
            status="initiated",
            context={"key1": "value1"},
        )

        # Update with additional context
        state.set_workflow_state(
            name="test-workflow",
            status="in-progress",
            context={"key2": "value2"},
        )

        workflow = state.get_workflow_state()
        assert workflow["context"] == {"key1": "value1", "key2": "value2"}

    def test_set_workflow_state_context_none_removal(self, temp_state_dir):
        """Test that None values in context remove keys."""
        state.set_workflow_state(
            name="test-workflow",
            status="initiated",
            context={"key1": "value1", "key2": "value2"},
        )

        # Update with None to remove a key
        state.set_workflow_state(
            name="test-workflow",
            status="in-progress",
            context={"key1": None, "key3": "value3"},
        )

        workflow = state.get_workflow_state()
        assert "key1" not in workflow["context"]
        assert workflow["context"]["key2"] == "value2"
        assert workflow["context"]["key3"] == "value3"

    def test_clear_workflow_state(self, temp_state_dir):
        """Test clearing workflow state."""
        state.set_workflow_state(name="test-workflow", status="in-progress")
        assert state.get_workflow_state() is not None

        state.clear_workflow_state()
        assert state.get_workflow_state() is None

    def test_is_workflow_active_when_active(self, temp_state_dir):
        """Test is_workflow_active returns True when workflow is active."""
        state.set_workflow_state(name="test-workflow", status="in-progress")

        assert state.is_workflow_active() is True

    def test_is_workflow_active_when_none(self, temp_state_dir):
        """Test is_workflow_active returns False when no workflow active."""
        assert state.is_workflow_active() is False

    def test_is_workflow_active_with_specific_name(self, temp_state_dir):
        """Test is_workflow_active with specific workflow name."""
        state.set_workflow_state(name="test-workflow", status="in-progress")

        assert state.is_workflow_active("test-workflow") is True
        assert state.is_workflow_active("other-workflow") is False

    def test_update_workflow_step(self, temp_state_dir):
        """Test update_workflow_step updates the step."""
        state.set_workflow_state(
            name="test-workflow",
            status="in-progress",
            step="step-1",
        )

        state.update_workflow_step("step-2")

        workflow = state.get_workflow_state()
        assert workflow["step"] == "step-2"
        assert workflow["status"] == "in-progress"

    def test_update_workflow_step_with_status(self, temp_state_dir):
        """Test update_workflow_step updates both step and status."""
        state.set_workflow_state(name="test-workflow", status="initiated")

        state.update_workflow_step("step-1", status="in-progress")

        workflow = state.get_workflow_state()
        assert workflow["step"] == "step-1"
        assert workflow["status"] == "in-progress"

    def test_update_workflow_step_raises_when_no_workflow(self, temp_state_dir):
        """Test update_workflow_step raises ValueError when no workflow active."""
        with pytest.raises(ValueError, match="No workflow is currently active"):
            state.update_workflow_step("step-1")

    def test_update_workflow_context(self, temp_state_dir):
        """Test update_workflow_context merges context."""
        state.set_workflow_state(
            name="test-workflow",
            status="in-progress",
            context={"key1": "value1"},
        )

        state.update_workflow_context({"key2": "value2"})

        workflow = state.get_workflow_state()
        assert workflow["context"] == {"key1": "value1", "key2": "value2"}

    def test_update_workflow_context_raises_when_no_workflow(self, temp_state_dir):
        """Test update_workflow_context raises ValueError when no workflow active."""
        with pytest.raises(ValueError, match="No workflow is currently active"):
            state.update_workflow_context({"key": "value"})


class TestClearTempFolderOSError:
    """Tests for OSError handling in clear_temp_folder."""

    def test_clear_temp_folder_ignores_oserror_on_rmtree(self, temp_state_dir):
        """Test that clear_temp_folder ignores OSError when removing directories."""

        # Create a subdirectory
        subdir = temp_state_dir / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")

        def raise_oserror(path, **kwargs):
            raise OSError("Directory in use")

        with patch("shutil.rmtree", raise_oserror):
            # Should not raise - OSError should be caught and ignored
            state.clear_temp_folder()


class TestResolveThreadStringYes:
    """Test should_resolve_thread with 'yes' string value."""

    def test_should_resolve_thread_with_yes_string(self, temp_state_dir):
        """Test should_resolve_thread returns True for 'yes' string."""
        state.set_value("resolve_thread", "yes")
        assert state.should_resolve_thread() is True

    def test_should_resolve_thread_with_one_string(self, temp_state_dir):
        """Test should_resolve_thread returns True for '1' string."""
        state.set_value("resolve_thread", "1")
        assert state.should_resolve_thread() is True

    def test_should_resolve_thread_with_true_string(self, temp_state_dir):
        """Test should_resolve_thread returns True for 'true' string."""
        state.set_value("resolve_thread", "true")
        assert state.should_resolve_thread() is True


class TestNoneValueReturns:
    """Test functions returning False when value is None (never set)."""

    def test_is_dry_run_returns_false_when_not_set(self, temp_state_dir):
        """Test is_dry_run returns False when dry_run is never set."""
        # Make sure dry_run is not set
        state.delete_value("dry_run")
        assert state.is_dry_run() is False

    def test_should_resolve_thread_returns_false_when_not_set(self, temp_state_dir):
        """Test should_resolve_thread returns False when resolve_thread is never set."""
        # Make sure resolve_thread is not set
        state.delete_value("resolve_thread")
        assert state.should_resolve_thread() is False
