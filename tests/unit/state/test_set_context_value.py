"""Tests for agentic_devtools.state.set_context_value."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


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
        state.set_value("jira.issue_key", "DFLY-OLD")
        state.set_value("pull_request_id", 12345)
        state.set_value("other_data", "should be cleared")

        with patch.object(state, "_trigger_cross_lookup"):
            result = state.set_context_value("jira.issue_key", "DFLY-NEW", verbose=False)

        assert result is True
        assert state.get_value("jira.issue_key") == "DFLY-NEW"
        assert state.get_value("pull_request_id") is None
        assert state.get_value("other_data") is None

    def test_set_context_value_no_change_returns_false(self, temp_state_dir):
        """Test that setting same value returns False (no change)."""
        state.set_value("pull_request_id", 12345)

        result = state.set_context_value("pull_request_id", 12345, verbose=False)

        assert result is False

    def test_set_context_value_no_change_preserves_other_state(self, temp_state_dir):
        """Test that setting same value doesn't clear other state."""
        state.set_value("pull_request_id", 12345)
        state.set_value("other_key", "should_persist")

        state.set_context_value("pull_request_id", 12345, verbose=False)

        assert state.get_value("other_key") == "should_persist"

    def test_set_context_value_change_clears_temp(self, temp_state_dir):
        """Test that changing context value clears temp folder."""
        state.set_value("pull_request_id", 12345)
        state.set_value("other_key", "should_be_cleared")

        (temp_state_dir / "temp-data.json").write_text("{}", encoding="utf-8")

        with patch.object(state, "_trigger_cross_lookup"):
            result = state.set_context_value("pull_request_id", 99999, verbose=False)

        assert result is True
        assert state.get_value("pull_request_id") == 99999
        assert state.get_value("other_key") is None
        assert not (temp_state_dir / "temp-data.json").exists()

    def test_set_context_value_change_preserves_new_value(self, temp_state_dir):
        """Test that the new context value is preserved during clearing."""
        state.set_value("pull_request_id", 12345)
        state.set_value("jira.issue_key", "DFLY-OLD")

        with patch.object(state, "_trigger_cross_lookup"):
            state.set_context_value("pull_request_id", 99999, verbose=False)

        assert state.get_value("pull_request_id") == 99999
        assert state.get_value("jira.issue_key") is None

    def test_set_context_value_string_to_int_comparison(self, temp_state_dir):
        """Test that string/int values are normalized for comparison."""
        state.set_value("pull_request_id", "12345")

        result = state.set_context_value("pull_request_id", 12345, verbose=False)

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
    """Tests for _trigger_cross_lookup (called by set_context_value)."""

    def test_trigger_cross_lookup_pr_to_jira(self, temp_state_dir, capsys):
        """Test that PR change triggers Jira lookup."""
        with patch("agentic_devtools.state._start_jira_lookup_from_pr") as mock_jira_lookup:
            state._trigger_cross_lookup("pull_request_id", 12345, verbose=True)

            mock_jira_lookup.assert_called_once_with(12345)

        captured = capsys.readouterr()
        assert "Starting background lookup for Jira issue from PR" in captured.out

    def test_trigger_cross_lookup_jira_to_pr(self, temp_state_dir, capsys):
        """Test that Jira change triggers PR lookup."""
        with patch("agentic_devtools.state._start_pr_lookup_from_jira") as mock_pr_lookup:
            state._trigger_cross_lookup("jira.issue_key", "DFLY-1234", verbose=True)

            mock_pr_lookup.assert_called_once_with("DFLY-1234")

        captured = capsys.readouterr()
        assert "Starting background lookup for PR from Jira issue" in captured.out

    def test_trigger_cross_lookup_unknown_key_does_nothing(self, temp_state_dir, capsys):
        """Test that unknown key does nothing (early exit)."""
        with patch("agentic_devtools.state._start_jira_lookup_from_pr") as mock_jira:
            with patch("agentic_devtools.state._start_pr_lookup_from_jira") as mock_pr:
                state._trigger_cross_lookup("unknown_key", "value", verbose=True)

                mock_jira.assert_not_called()
                mock_pr.assert_not_called()

        captured = capsys.readouterr()
        assert captured.out == ""


class TestStartJiraLookupFromPr:
    """Tests for _start_jira_lookup_from_pr (called by _trigger_cross_lookup)."""

    def test_start_jira_lookup_calls_async_function(self, temp_state_dir):
        """Test that _start_jira_lookup_from_pr calls async lookup."""
        with patch("agentic_devtools.cli.azure_devops.async_commands.lookup_jira_issue_from_pr_async") as mock_async:
            state._start_jira_lookup_from_pr(12345)

            mock_async.assert_called_once_with(12345)

    def test_start_jira_lookup_handles_import_error(self, temp_state_dir):
        """Test that _start_jira_lookup_from_pr handles ImportError gracefully."""
        with patch.dict(
            "sys.modules",
            {"agentic_devtools.cli.azure_devops.async_commands": None},
        ):
            state._start_jira_lookup_from_pr(12345)

    def test_start_jira_lookup_handles_exception(self, temp_state_dir):
        """Test that _start_jira_lookup_from_pr handles exceptions gracefully."""
        with patch(
            "agentic_devtools.cli.azure_devops.async_commands.lookup_jira_issue_from_pr_async",
            side_effect=Exception("Network error"),
        ):
            state._start_jira_lookup_from_pr(12345)


class TestStartPrLookupFromJira:
    """Tests for _start_pr_lookup_from_jira (called by _trigger_cross_lookup)."""

    def test_start_pr_lookup_calls_async_function(self, temp_state_dir):
        """Test that _start_pr_lookup_from_jira calls async lookup."""
        with patch("agentic_devtools.cli.azure_devops.async_commands.lookup_pr_from_jira_issue_async") as mock_async:
            state._start_pr_lookup_from_jira("DFLY-1234")

            mock_async.assert_called_once_with("DFLY-1234")

    def test_start_pr_lookup_handles_import_error(self, temp_state_dir):
        """Test that _start_pr_lookup_from_jira handles ImportError gracefully."""
        with patch.dict(
            "sys.modules",
            {"agentic_devtools.cli.azure_devops.async_commands": None},
        ):
            state._start_pr_lookup_from_jira("DFLY-1234")

    def test_start_pr_lookup_handles_exception(self, temp_state_dir):
        """Test that _start_pr_lookup_from_jira handles exceptions gracefully."""
        with patch(
            "agentic_devtools.cli.azure_devops.async_commands.lookup_pr_from_jira_issue_async",
            side_effect=Exception("Network error"),
        ):
            state._start_pr_lookup_from_jira("DFLY-1234")
