"""Tests for BuildCommandHint."""

import pytest

from agentic_devtools.cli.workflows.manager import (
    _build_command_hint,
)


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestBuildCommandHint:
    """Tests for _build_command_hint function."""

    def test_with_current_value_shows_truncated_preview(self):
        """When value exists and is long, should truncate for display."""
        long_value = "A" * 150  # Longer than 100 chars

        result = _build_command_hint(
            command_name="agdt-add-jira-comment",
            param_name="--jira-comment",
            state_key="jira.comment",
            current_value=long_value,
            is_required=True,
        )

        assert "--jira-comment" in result
        assert "optional" in result
        assert "..." in result  # Truncated
        assert "agdt-get jira.comment" in result

    def test_with_short_value_shows_full_preview(self):
        """When value exists and is short, should show full value."""
        short_value = "Quick note"

        result = _build_command_hint(
            command_name="agdt-add-jira-comment",
            param_name="--jira-comment",
            state_key="jira.comment",
            current_value=short_value,
            is_required=True,
        )

        assert "--jira-comment" in result
        assert "Quick note" in result
        assert "..." not in result

    def test_without_value_required_shows_required(self):
        """When no value and required, should indicate REQUIRED."""
        result = _build_command_hint(
            command_name="agdt-git-save-work",
            param_name="--commit-message",
            state_key="commit_message",
            current_value=None,
            is_required=True,
        )

        assert "--commit-message" in result
        assert "REQUIRED" in result
        assert "not set" in result

    def test_without_value_optional_shows_optional(self):
        """When no value and optional, should indicate optional."""
        result = _build_command_hint(
            command_name="agdt-git-save-work",
            param_name="--source-branch",
            state_key="source_branch",
            current_value=None,
            is_required=False,
        )

        assert "--source-branch" in result
        assert "optional" in result
        assert "not set" in result

    def test_multiline_value_escaped(self):
        """Newlines in value should be escaped for display."""
        multiline = "Line 1\nLine 2\nLine 3"

        result = _build_command_hint(
            command_name="agdt-add-jira-comment",
            param_name="--jira-comment",
            state_key="jira.comment",
            current_value=multiline,
            is_required=True,
        )

        assert "\\n" in result  # Newlines escaped
        assert "\n" not in result.split('"')[1]  # No actual newlines in the quoted value
