"""Tests for read_default_commit_type helper."""

from agentic_devtools.cli.config.commit_type_resolution import read_default_commit_type


class TestReadDefaultCommitType:
    """Tests for read_default_commit_type()."""

    def test_camel_case_key_found(self):
        """Reads from camelCase key when present."""
        config = {"defaultCommitIssueType": "fix"}
        value, warning = read_default_commit_type(config)
        assert value == "fix"
        assert warning is None

    def test_snake_case_alias_used_as_fallback(self):
        """Falls back to snake_case alias when camelCase absent."""
        config = {"default_commit_issue_type": "docs"}
        value, warning = read_default_commit_type(config)
        assert value == "docs"
        assert warning is None

    def test_camel_case_takes_precedence(self):
        """camelCase wins when both keys present."""
        config = {
            "defaultCommitIssueType": "feat",
            "default_commit_issue_type": "fix",
        }
        value, warning = read_default_commit_type(config)
        assert value == "feat"
        assert warning is None

    def test_empty_string_treated_as_absent(self):
        """Empty string value returns None with no warning."""
        config = {"defaultCommitIssueType": ""}
        value, warning = read_default_commit_type(config)
        assert value is None
        assert warning is None

    def test_whitespace_only_treated_as_absent(self):
        """Whitespace-only value returns None with no warning."""
        config = {"defaultCommitIssueType": "   "}
        value, warning = read_default_commit_type(config)
        assert value is None
        assert warning is None

    def test_non_string_returns_warning(self):
        """Non-string value returns None and a warning."""
        config = {"defaultCommitIssueType": 42}
        value, warning = read_default_commit_type(config)
        assert value is None
        assert warning is not None
        assert "should be a string" in warning
        assert "int" in warning

    def test_non_string_list_returns_warning(self):
        """List value returns None and a warning."""
        config = {"defaultCommitIssueType": ["feat"]}
        value, warning = read_default_commit_type(config)
        assert value is None
        assert warning is not None
        assert "should be a string" in warning
        assert "list" in warning

    def test_absent_key_returns_none(self):
        """Both keys absent returns None with no warning."""
        config = {"jira_project_keys": "PROJ"}
        value, warning = read_default_commit_type(config)
        assert value is None
        assert warning is None

    def test_empty_config(self):
        """Empty config returns None with no warning."""
        value, warning = read_default_commit_type({})
        assert value is None
        assert warning is None

    def test_value_is_stripped(self):
        """Leading/trailing whitespace is stripped from value."""
        config = {"defaultCommitIssueType": "  fix  "}
        value, warning = read_default_commit_type(config)
        assert value == "fix"
        assert warning is None

    def test_both_keys_non_string_uses_first_warning_only(self):
        """When both keys are non-string, warning comes from camelCase key only."""
        config = {
            "defaultCommitIssueType": 42,
            "default_commit_issue_type": 99,
        }
        value, warning = read_default_commit_type(config)
        assert value is None
        assert warning is not None
        assert "defaultCommitIssueType" in warning
        assert "default_commit_issue_type" not in warning
