"""Tests for read_available_commit_types helper."""

from agentic_devtools.cli.config.commit_type_resolution import (
    STANDARD_COMMIT_TYPES,
    read_available_commit_types,
)


class TestReadAvailableCommitTypes:
    """Tests for read_available_commit_types()."""

    def test_camel_case_key_found(self):
        """Reads from camelCase key when present."""
        custom = ["feat", "fix", "chore"]
        config = {"availableCommitIssueTypes": custom}
        types, warning = read_available_commit_types(config)
        assert types == custom
        assert warning is None

    def test_snake_case_alias_used_as_fallback(self):
        """Falls back to snake_case alias when camelCase absent."""
        custom = ["feat", "fix"]
        config = {"available_commit_issue_types": custom}
        types, warning = read_available_commit_types(config)
        assert types == custom
        assert warning is None

    def test_camel_case_takes_precedence(self):
        """camelCase wins when both keys present."""
        config = {
            "availableCommitIssueTypes": ["feat"],
            "available_commit_issue_types": ["fix"],
        }
        types, warning = read_available_commit_types(config)
        assert types == ["feat"]
        assert warning is None

    def test_empty_array_falls_back_to_standard(self):
        """Empty array returns STANDARD_COMMIT_TYPES."""
        config = {"availableCommitIssueTypes": []}
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is None

    def test_non_array_returns_standard_with_warning(self):
        """Non-array value returns standard types and a warning."""
        config = {"availableCommitIssueTypes": "feat,fix"}
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is not None
        assert "should be an array" in warning
        assert "str" in warning

    def test_non_array_int_returns_warning(self):
        """Integer value returns standard types and a warning."""
        config = {"availableCommitIssueTypes": 42}
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is not None
        assert "should be an array" in warning

    def test_array_with_non_string_elements_returns_warning(self):
        """Array containing non-strings returns standard types and warning."""
        config = {"availableCommitIssueTypes": ["feat", 42, "fix"]}
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is not None
        assert "non-string elements" in warning
        assert "1" in warning  # index 1

    def test_absent_key_returns_standard(self):
        """Both keys absent returns STANDARD_COMMIT_TYPES."""
        config = {"jira_project_keys": "PROJ"}
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is None

    def test_empty_config(self):
        """Empty config returns STANDARD_COMMIT_TYPES."""
        types, warning = read_available_commit_types({})
        assert types == STANDARD_COMMIT_TYPES
        assert warning is None

    def test_returns_copy_not_reference(self):
        """Standard types fallback returns a copy, not the original."""
        types, _ = read_available_commit_types({})
        types.append("custom")
        assert "custom" not in STANDARD_COMMIT_TYPES

    def test_both_keys_non_array_uses_first_warning_only(self):
        """When both keys are non-arrays, warning comes from camelCase key only."""
        config = {
            "availableCommitIssueTypes": "feat,fix",
            "available_commit_issue_types": "chore",
        }
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is not None
        assert "availableCommitIssueTypes" in warning
        assert "available_commit_issue_types" not in warning

    def test_both_keys_non_string_elements_uses_first_warning_only(self):
        """When both keys have non-string array elements, warning is from camelCase only."""
        config = {
            "availableCommitIssueTypes": [1, 2],
            "available_commit_issue_types": [3, 4],
        }
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is not None
        assert "availableCommitIssueTypes" in warning
        assert "available_commit_issue_types" not in warning

    def test_blank_entry_returns_standard_with_warning(self):
        """Array containing blank/whitespace strings falls back to standard types."""
        config = {"availableCommitIssueTypes": ["feat", "  ", "fix"]}
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is not None
        assert "blank entries" in warning
        assert "1" in warning  # index 1

    def test_both_keys_blank_entries_uses_first_warning_only(self):
        """When both keys have blank entries, warning comes from camelCase key only."""
        config = {
            "availableCommitIssueTypes": ["feat", ""],
            "available_commit_issue_types": ["fix", "   "],
        }
        types, warning = read_available_commit_types(config)
        assert types == STANDARD_COMMIT_TYPES
        assert warning is not None
        assert "availableCommitIssueTypes" in warning
        assert "available_commit_issue_types" not in warning
