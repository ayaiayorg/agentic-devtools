"""Tests for resolve_commit_issue_type function."""

from unittest.mock import patch

from agentic_devtools.cli.config.commit_type_resolution import (
    STANDARD_COMMIT_TYPES,
    resolve_commit_issue_type,
)


class TestResolveCommitIssueType:
    """Tests for resolve_commit_issue_type()."""

    def test_explicit_type_wins_over_config(self):
        """Explicit type overrides project config default."""
        config = {"defaultCommitIssueType": "fix"}
        resolved, warnings = resolve_commit_issue_type("refactor", project_config=config)
        assert resolved == "refactor"
        assert not warnings

    def test_config_default_used_when_no_explicit(self):
        """Config default is used when explicit_type is None."""
        config = {"defaultCommitIssueType": "fix"}
        resolved, warnings = resolve_commit_issue_type(None, project_config=config)
        assert resolved == "fix"
        assert not warnings

    def test_hardcoded_feat_fallback(self):
        """Falls back to 'feat' when no explicit or config default."""
        resolved, warnings = resolve_commit_issue_type(None, project_config={})
        assert resolved == "feat"
        assert not warnings

    def test_empty_explicit_type_treated_as_absent(self):
        """Empty string explicit type falls through to config."""
        config = {"defaultCommitIssueType": "docs"}
        resolved, warnings = resolve_commit_issue_type("", project_config=config)
        assert resolved == "docs"
        assert not warnings

    def test_whitespace_explicit_type_treated_as_absent(self):
        """Whitespace-only explicit type falls through to config."""
        config = {"defaultCommitIssueType": "style"}
        resolved, warnings = resolve_commit_issue_type("   ", project_config=config)
        assert resolved == "style"
        assert not warnings

    def test_validation_warning_for_invalid_explicit_type(self):
        """Invalid explicit type emits validation warning."""
        config = {"availableCommitIssueTypes": ["feat", "fix"]}
        resolved, warnings = resolve_commit_issue_type("invalid", project_config=config)
        assert resolved == "invalid"
        assert len(warnings) == 1
        assert "not in availableCommitIssueTypes" in warnings[0]

    def test_misconfigured_default_warning(self):
        """Config default not in allowed types emits misconfiguration warning."""
        config = {
            "defaultCommitIssueType": "yolo",
            "availableCommitIssueTypes": ["feat", "fix"],
        }
        resolved, warnings = resolve_commit_issue_type(None, project_config=config)
        assert resolved == "yolo"
        assert len(warnings) == 1
        assert "defaultCommitIssueType" in warnings[0]
        assert "not in availableCommitIssueTypes" in warnings[0]

    def test_no_duplicate_warnings(self):
        """Only one warning emitted for misconfigured default (not two)."""
        config = {
            "defaultCommitIssueType": "bad",
            "availableCommitIssueTypes": ["feat"],
        }
        resolved, warnings = resolve_commit_issue_type(None, project_config=config)
        assert resolved == "bad"
        # Only the misconfiguration warning, not also a generic validation warning
        assert len(warnings) == 1

    def test_project_config_none_calls_load(self):
        """When project_config is None, load_project_config() is called."""
        with patch(
            "agentic_devtools.cli.config.project_config.load_project_config",
            return_value={"defaultCommitIssueType": "ci"},
        ) as mock_load:
            resolved, warnings = resolve_commit_issue_type(None, project_config=None)
        assert resolved == "ci"
        assert not warnings
        mock_load.assert_called_once()

    def test_snake_case_config_default(self):
        """snake_case alias is respected for default."""
        config = {"default_commit_issue_type": "perf"}
        resolved, warnings = resolve_commit_issue_type(None, project_config=config)
        assert resolved == "perf"
        assert not warnings

    def test_non_string_config_default_warning(self):
        """Non-string config default emits warning, uses hardcoded fallback."""
        config = {"defaultCommitIssueType": 123}
        resolved, warnings = resolve_commit_issue_type(None, project_config=config)
        assert resolved == "feat"  # hardcoded fallback
        assert any("should be a string" in w for w in warnings)

    def test_malformed_available_types_warning(self):
        """Non-array availableCommitIssueTypes emits warning."""
        config = {"availableCommitIssueTypes": "not-a-list"}
        resolved, warnings = resolve_commit_issue_type("feat", project_config=config)
        assert resolved == "feat"
        assert any("should be an array" in w for w in warnings)

    def test_explicit_type_stripped(self):
        """Explicit type is stripped of whitespace."""
        resolved, warnings = resolve_commit_issue_type("  fix  ", project_config={})
        assert resolved == "fix"
        assert not warnings

    def test_valid_type_from_standard_list(self):
        """Standard type validates against default allowed list."""
        for commit_type in STANDARD_COMMIT_TYPES:
            resolved, warnings = resolve_commit_issue_type(commit_type, project_config={})
            assert resolved == commit_type
            assert not warnings

    def test_hardcoded_fallback_invalid_against_custom_list(self):
        """Hardcoded 'feat' fallback triggers validation warning with custom list."""
        config = {"availableCommitIssueTypes": ["deploy", "hotfix"]}
        resolved, warnings = resolve_commit_issue_type(None, project_config=config)
        assert resolved == "feat"
        assert len(warnings) == 1
        assert "not in availableCommitIssueTypes" in warnings[0]
