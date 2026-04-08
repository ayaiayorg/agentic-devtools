"""Tests for get_pr_checks_status orchestration function."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.pr_checks_status import get_pr_checks_status


class TestGetPrChecksStatus:
    """Tests for the orchestration function."""

    @patch("agentic_devtools.cli.github.pr_checks_status.set_value")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_check_suites")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_pr_checks")
    def test_full_flow(self, mock_fetch_checks, mock_fetch_suites, mock_set_value):
        """Full flow returns correct dict with all fields."""
        mock_fetch_checks.return_value = [
            {"name": "build", "bucket": "pass"},
            {"name": "test", "bucket": "pass"},
        ]
        mock_fetch_suites.return_value = [
            {"id": 1, "status": "completed", "conclusion": "success", "app": {"slug": "ci"}},
        ]
        result = get_pr_checks_status(42, "owner/repo", "abc123")

        assert result["status"] == "all-pass"
        assert result["prNumber"] == 42
        assert result["repo"] == "owner/repo"
        assert result["totalChecks"] == 2
        assert result["passed"] == 2
        assert result["checkSuitesVerified"] is True

    @patch("agentic_devtools.cli.github.pr_checks_status.set_value")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_pr_checks")
    def test_head_sha_none_skips_suites(self, mock_fetch_checks, mock_set_value):
        """head_sha=None skips check-suite verification entirely."""
        mock_fetch_checks.return_value = [{"name": "build", "bucket": "pass"}]
        result = get_pr_checks_status(42, "owner/repo", None)

        assert result["status"] == "all-pass"
        assert result["checkSuitesVerified"] is False

    @patch("agentic_devtools.cli.github.pr_checks_status.set_value")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_check_suites")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_pr_checks")
    def test_empty_suites_graceful_degradation(self, mock_fetch_checks, mock_fetch_suites, mock_set_value):
        """Empty suites result → graceful degradation."""
        mock_fetch_checks.return_value = [{"name": "build", "bucket": "pass"}]
        mock_fetch_suites.return_value = []

        result = get_pr_checks_status(42, "owner/repo", "abc123")
        assert result["checkSuitesVerified"] is False

    @patch("agentic_devtools.cli.github.pr_checks_status.set_value")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_pr_checks")
    def test_state_keys_written(self, mock_fetch_checks, mock_set_value):
        """State keys are written via set_value."""
        mock_fetch_checks.return_value = [
            {"name": "build", "bucket": "pass"},
            {"name": "lint", "bucket": "fail"},
        ]
        get_pr_checks_status(42, "owner/repo", None)

        calls = {c[0][0]: c[0][1] for c in mock_set_value.call_args_list}
        assert calls["github.pr_checks_status"] == "failed"
        assert calls["github.pr_checks_failed"] == ["lint"]
        assert calls["github.pr_checks_pending"] == []

    @patch("agentic_devtools.cli.github.pr_checks_status.set_value")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_check_suites")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_pr_checks")
    def test_suite_discrepancy_overrides_status(self, mock_fetch_checks, mock_fetch_suites, mock_set_value):
        """Suite discrepancy overrides all-pass status."""
        mock_fetch_checks.return_value = [{"name": "build", "bucket": "pass"}]
        mock_fetch_suites.return_value = [
            {"id": 1, "status": "in_progress", "conclusion": "", "app": {"slug": "ci"}},
        ]
        result = get_pr_checks_status(42, "owner/repo", "abc123")
        assert result["status"] == "pending"
        assert len(result["checkSuiteDiscrepancies"]) == 1

    @patch("agentic_devtools.cli.github.pr_checks_status.set_value")
    @patch("agentic_devtools.cli.github.pr_checks_status._fetch_pr_checks")
    def test_repo_trailing_git_stripped(self, mock_fetch_checks, mock_set_value):
        """Trailing .git is stripped from repo before downstream calls."""
        mock_fetch_checks.return_value = [{"name": "build", "bucket": "pass"}]
        result = get_pr_checks_status(42, "owner/repo.git", None)
        assert result["repo"] == "owner/repo"

    def test_malformed_repo_no_slash(self):
        """sys.exit(1) on repo string without a slash."""
        with pytest.raises(SystemExit) as exc_info:
            get_pr_checks_status(42, "noslash", None)
        assert exc_info.value.code == 1

    def test_malformed_repo_multiple_slashes(self):
        """sys.exit(1) on repo with multiple slashes."""
        with pytest.raises(SystemExit) as exc_info:
            get_pr_checks_status(42, "a/b/c", None)
        assert exc_info.value.code == 1
