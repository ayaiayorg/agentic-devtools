"""Tests for merge_pr core function."""

from unittest.mock import patch

from agentic_devtools.cli.github import pr_merge


class TestMergePr:
    """Tests for merge_pr."""

    def test_full_success_first_try(self):
        """Merge succeeds and verification shows MERGED on first try."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", return_value=(True, "")),
            patch.object(
                pr_merge,
                "_verify_merge",
                return_value={"state": "MERGED", "mergedAt": "2026-04-07T09:05:55Z"},
            ),
            patch.object(pr_merge, "set_value") as mock_set,
        ):
            result = pr_merge.merge_pr(42, "o/r")

        assert result["merged"] is True
        assert result["state"] == "MERGED"
        assert result["mergedAt"] == "2026-04-07T09:05:55Z"
        assert result["retries"] == 0
        assert result["prNumber"] == 42
        assert result["repo"] == "o/r"
        calls = [c.args for c in mock_set.call_args_list]
        assert ("github.pr_merged", True) in calls
        assert ("github.pr_merged_at", "2026-04-07T09:05:55Z") in calls
        assert ("github.pr_merge_strategy", "rebase") in calls

    def test_merge_submission_failure(self):
        """Merge command fails — error classified and returned."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(
                pr_merge,
                "_execute_merge",
                return_value=(False, "merge conflict detected"),
            ),
            patch.object(pr_merge, "set_value") as mock_set,
        ):
            result = pr_merge.merge_pr(42, "o/r")

        assert result["merged"] is False
        assert result["state"] == "UNKNOWN"
        assert result["error"] == "merge_conflict"
        assert result["message"] == "merge conflict detected"
        assert result["retries"] == 0
        calls = [c.args for c in mock_set.call_args_list]
        assert ("github.pr_merged", False) in calls

    def test_open_after_merge_retry_success(self):
        """PR still OPEN → retry → MERGED on second try."""
        execute_returns = [(True, ""), (True, "")]
        verify_returns = [
            {"state": "OPEN", "mergedAt": None},
            {"state": "MERGED", "mergedAt": "2026-04-07T10:00:00Z"},
        ]
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", side_effect=execute_returns),
            patch.object(pr_merge, "_verify_merge", side_effect=verify_returns),
            patch.object(pr_merge, "set_value"),
            patch.object(pr_merge.time, "sleep") as mock_sleep,
        ):
            result = pr_merge.merge_pr(42, "o/r")

        assert result["merged"] is True
        assert result["retries"] == 1
        mock_sleep.assert_called_once_with(5.0)

    def test_open_after_merge_retry_still_open(self):
        """PR still OPEN after retry → verification_failed."""
        execute_returns = [(True, ""), (True, "")]
        verify_returns = [
            {"state": "OPEN", "mergedAt": None},
            {"state": "OPEN", "mergedAt": None},
        ]
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", side_effect=execute_returns),
            patch.object(pr_merge, "_verify_merge", side_effect=verify_returns),
            patch.object(pr_merge, "set_value"),
            patch.object(pr_merge.time, "sleep"),
        ):
            result = pr_merge.merge_pr(42, "o/r")

        assert result["merged"] is False
        assert result["error"] == "merge_verification_failed"
        assert result["retries"] == 1

    def test_closed_not_merged(self):
        """Post-merge verification shows CLOSED without mergedAt."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", return_value=(True, "")),
            patch.object(
                pr_merge,
                "_verify_merge",
                return_value={"state": "CLOSED", "mergedAt": None},
            ),
            patch.object(pr_merge, "set_value"),
        ):
            result = pr_merge.merge_pr(42, "o/r")

        assert result["merged"] is False
        assert result["error"] == "closed_not_merged"
        assert result["message"] == "PR was closed but not merged."
        assert result["retries"] == 0

    def test_state_keys_on_success(self):
        """State keys written correctly on successful merge."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", return_value=(True, "")),
            patch.object(
                pr_merge,
                "_verify_merge",
                return_value={"state": "MERGED", "mergedAt": "2026-01-01T00:00:00Z"},
            ),
            patch.object(pr_merge, "set_value") as mock_set,
        ):
            pr_merge.merge_pr(42, "o/r", strategy="rebase")

        calls = [c.args for c in mock_set.call_args_list]
        assert ("github.pr_merged", True) in calls
        assert ("github.pr_merged_at", "2026-01-01T00:00:00Z") in calls
        assert ("github.pr_merge_strategy", "rebase") in calls

    def test_state_keys_on_failure(self):
        """State keys written correctly on failed merge."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(
                pr_merge,
                "_execute_merge",
                return_value=(False, "error msg"),
            ),
            patch.object(pr_merge, "set_value") as mock_set,
        ):
            pr_merge.merge_pr(42, "o/r")

        calls = [c.args for c in mock_set.call_args_list]
        assert ("github.pr_merged", False) in calls
        assert ("github.pr_merged_at", None) in calls
        assert ("github.pr_merge_strategy", "rebase") in calls

    def test_default_strategy_is_rebase(self):
        """Default strategy is rebase."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", return_value=(True, "")) as mock_exec,
            patch.object(
                pr_merge,
                "_verify_merge",
                return_value={"state": "MERGED", "mergedAt": "2026-01-01T00:00:00Z"},
            ),
            patch.object(pr_merge, "set_value"),
        ):
            pr_merge.merge_pr(42, "o/r")

        assert mock_exec.call_args[0][2] == "rebase"

    def test_custom_strategy_passed_through(self):
        """Custom strategy is forwarded to _execute_merge."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", return_value=(True, "")) as mock_exec,
            patch.object(
                pr_merge,
                "_verify_merge",
                return_value={"state": "MERGED", "mergedAt": "2026-01-01T00:00:00Z"},
            ),
            patch.object(pr_merge, "set_value"),
        ):
            pr_merge.merge_pr(42, "o/r", strategy="rebase")

        assert mock_exec.call_args[0][2] == "rebase"

    def test_sleep_called_during_retry(self):
        """time.sleep(5.0) called exactly once during OPEN retry."""
        execute_returns = [(True, ""), (True, "")]
        verify_returns = [
            {"state": "OPEN", "mergedAt": None},
            {"state": "MERGED", "mergedAt": "2026-01-01T00:00:00Z"},
        ]
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", side_effect=execute_returns),
            patch.object(pr_merge, "_verify_merge", side_effect=verify_returns),
            patch.object(pr_merge, "set_value"),
            patch.object(pr_merge.time, "sleep") as mock_sleep,
        ):
            pr_merge.merge_pr(42, "o/r")

        mock_sleep.assert_called_once_with(5.0)

    def test_unexpected_state_returns_verification_error(self):
        """Unexpected state after merge returns verification_error."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", return_value=(True, "")),
            patch.object(
                pr_merge,
                "_verify_merge",
                return_value={"state": "UNKNOWN", "mergedAt": None},
            ),
            patch.object(pr_merge, "set_value"),
        ):
            result = pr_merge.merge_pr(42, "o/r")

        assert result["merged"] is False
        assert result["error"] == "verification_error"
        assert "UNKNOWN" in result["message"]

    def test_delete_branch_default_true(self):
        """Default delete_branch is True."""
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", return_value=(True, "")) as mock_exec,
            patch.object(
                pr_merge,
                "_verify_merge",
                return_value={"state": "MERGED", "mergedAt": "2026-01-01T00:00:00Z"},
            ),
            patch.object(pr_merge, "set_value"),
        ):
            pr_merge.merge_pr(42, "o/r")

        assert mock_exec.call_args[0][3] is True

    def test_retry_merge_fails(self):
        """Retry merge fails — returns classified error with retries=1."""
        execute_returns = [(True, ""), (False, "protected branch")]
        verify_returns = [{"state": "OPEN", "mergedAt": None}]
        with (
            patch.object(pr_merge, "_check_gh_available"),
            patch.object(pr_merge, "_execute_merge", side_effect=execute_returns),
            patch.object(pr_merge, "_verify_merge", side_effect=verify_returns),
            patch.object(pr_merge, "set_value"),
            patch.object(pr_merge.time, "sleep"),
        ):
            result = pr_merge.merge_pr(42, "o/r")

        assert result["merged"] is False
        assert result["error"] == "branch_protection"
        assert result["retries"] == 1
