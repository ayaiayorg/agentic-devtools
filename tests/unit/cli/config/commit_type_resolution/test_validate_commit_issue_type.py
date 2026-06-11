"""Tests for validate_commit_issue_type function."""

from agentic_devtools.cli.config.commit_type_resolution import (
    STANDARD_COMMIT_TYPES,
    validate_commit_issue_type,
)


class TestValidateCommitIssueType:
    """Tests for validate_commit_issue_type()."""

    def test_valid_type_returns_none(self):
        """Valid type in allowed list returns None."""
        result = validate_commit_issue_type("feat", STANDARD_COMMIT_TYPES)
        assert result is None

    def test_valid_type_custom_list(self):
        """Valid type in a custom allowed list returns None."""
        result = validate_commit_issue_type("deploy", ["deploy", "hotfix"])
        assert result is None

    def test_invalid_type_returns_warning(self):
        """Invalid type returns a warning string."""
        result = validate_commit_issue_type("invalid", ["feat", "fix"])
        assert result is not None
        assert "invalid" in result
        assert "availableCommitIssueTypes" in result
        assert "'feat'" in result
        assert "'fix'" in result

    def test_case_sensitive_comparison(self):
        """Comparison is case-sensitive: 'Feat' does not match 'feat'."""
        result = validate_commit_issue_type("Feat", ["feat", "fix"])
        assert result is not None
        assert "Feat" in result

    def test_truncation_at_max_types(self):
        """Lists exceeding 20 entries are truncated with 'and N more'."""
        many_types = [f"type{i}" for i in range(25)]
        result = validate_commit_issue_type("invalid", many_types)
        assert result is not None
        assert "'and 6 more'" in result
        # First 19 should be shown
        assert "'type0'" in result
        assert "'type18'" in result
        # 20th should NOT be shown individually
        assert "'type19'" not in result

    def test_exactly_20_types_no_truncation(self):
        """Exactly 20 entries are all shown without truncation."""
        types_20 = [f"type{i}" for i in range(20)]
        result = validate_commit_issue_type("invalid", types_20)
        assert result is not None
        assert "'type19'" in result
        assert "and" not in result.split("Allowed:")[1].replace("'and", "PLACEHOLDER")

    def test_single_quote_in_type_escaped(self):
        """Single quotes in the type name are escaped in warning."""
        result = validate_commit_issue_type("it's", ["feat", "fix"])
        assert result is not None
        assert "it\\'s" in result

    def test_single_quote_in_allowed_types_escaped(self):
        """Single quotes in allowed type names are escaped."""
        result = validate_commit_issue_type("bad", ["it's", "fix"])
        assert result is not None
        assert "it\\'s" in result

    def test_empty_allowed_list(self):
        """Any type is invalid when allowed list is empty."""
        result = validate_commit_issue_type("feat", [])
        assert result is not None
        assert "feat" in result

    def test_warning_format_structure(self):
        """Warning follows expected format structure."""
        result = validate_commit_issue_type("bad", ["feat", "fix", "docs"])
        assert result is not None
        assert result.startswith("Warning: Issue type ")
        assert "Allowed: [" in result
        assert result.endswith("]")
