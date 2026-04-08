"""Tests for request_copilot_review core function."""

from unittest.mock import call, patch

import pytest

from agentic_devtools.cli.github.request_copilot_review import (
    COPILOT_REVIEWER_LOGIN,
    request_copilot_review,
)

MODULE = "agentic_devtools.cli.github.request_copilot_review"


class TestRequestCopilotReview:
    """Tests for request_copilot_review."""

    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._verify_reviewer_requested", return_value=True)
    @patch(f"{MODULE}._post_review_request", return_value=(True, None))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_success_immediate_verification(self, mock_which, mock_post, mock_verify, mock_set):
        """Successful POST + immediate verification → retries=0."""
        result = request_copilot_review(42, "owner/repo")
        assert result["prNumber"] == 42
        assert result["repo"] == "owner/repo"
        assert result["requested"] is True
        assert result["reviewer"] == COPILOT_REVIEWER_LOGIN
        assert result["verified"] is True
        assert result["retries"] == 0

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._verify_reviewer_requested", side_effect=[False, True])
    @patch(f"{MODULE}._post_review_request", return_value=(True, None))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_success_after_one_retry(self, mock_which, mock_post, mock_verify, mock_set, mock_sleep):
        """Verification fails then succeeds on retry 1 → retries=1."""
        result = request_copilot_review(42, "owner/repo")
        assert result["verified"] is True
        assert result["retries"] == 1
        mock_sleep.assert_called_once_with(5.0)

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._verify_reviewer_requested", return_value=False)
    @patch(f"{MODULE}._post_review_request", return_value=(True, None))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_all_verification_attempts_fail(self, mock_which, mock_post, mock_verify, mock_set, mock_sleep):
        """All 3 verification attempts fail → verified=False, retries=2."""
        result = request_copilot_review(42, "owner/repo")
        assert result["verified"] is False
        assert result["retries"] == 2
        assert mock_verify.call_count == 3  # initial + 2 retries
        assert mock_sleep.call_count == 2

    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._post_review_request", return_value=(False, "Validation Failed"))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_post_failure(self, mock_which, mock_post, mock_set):
        """POST failure → requested=False, error present."""
        result = request_copilot_review(42, "owner/repo")
        assert result["requested"] is False
        assert result["error"] == "request_failed"
        assert result["message"] == "Validation Failed"
        assert result["verified"] is False
        assert result["retries"] == 0

    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._verify_reviewer_requested", return_value=True)
    @patch(f"{MODULE}._post_review_request", return_value=(True, None))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_state_keys_written_on_success(self, mock_which, mock_post, mock_verify, mock_set):
        """State keys are written correctly on successful POST."""
        request_copilot_review(42, "owner/repo")
        mock_set.assert_any_call("github.copilot_review_requested", True)
        mock_set.assert_any_call("github.copilot_review_request_verified", True)

    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._post_review_request", return_value=(False, "error"))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_state_keys_written_on_failure(self, mock_which, mock_post, mock_set):
        """State keys are written correctly on POST failure."""
        request_copilot_review(42, "owner/repo")
        mock_set.assert_any_call("github.copilot_review_requested", False)
        mock_set.assert_any_call("github.copilot_review_request_verified", False)

    @patch(f"{MODULE}.shutil.which", return_value=None)
    def test_gh_cli_not_installed_exits(self, mock_which):
        """sys.exit(1) when gh CLI is not installed."""
        with pytest.raises(SystemExit) as exc_info:
            request_copilot_review(42, "owner/repo")
        assert exc_info.value.code == 1

    def test_repo_without_slash_exits(self):
        """sys.exit(1) when repo format is invalid (no slash)."""
        with pytest.raises(SystemExit) as exc_info:
            request_copilot_review(42, "noslash")
        assert exc_info.value.code == 1

    def test_repo_with_extra_segments_exits(self):
        """sys.exit(1) when repo has extra path segments like 'owner/repo/extra'."""
        with pytest.raises(SystemExit) as exc_info:
            request_copilot_review(42, "owner/repo/extra")
        assert exc_info.value.code == 1

    def test_repo_with_empty_owner_exits(self):
        """sys.exit(1) when repo has empty owner like '/repo'."""
        with pytest.raises(SystemExit) as exc_info:
            request_copilot_review(42, "/repo")
        assert exc_info.value.code == 1

    def test_repo_with_empty_name_exits(self):
        """sys.exit(1) when repo has empty name like 'owner/'."""
        with pytest.raises(SystemExit) as exc_info:
            request_copilot_review(42, "owner/")
        assert exc_info.value.code == 1

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._verify_reviewer_requested", side_effect=[False, False, True])
    @patch(f"{MODULE}._post_review_request", return_value=(True, None))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_sleep_called_between_retries(self, mock_which, mock_post, mock_verify, mock_set, mock_sleep):
        """time.sleep(5.0) is called between each verification retry."""
        request_copilot_review(42, "owner/repo")
        assert mock_sleep.call_args_list == [call(5.0), call(5.0)]

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.set_value")
    @patch(
        f"{MODULE}._verify_reviewer_requested",
        return_value=False,
    )
    @patch(f"{MODULE}._post_review_request", return_value=(True, None))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_state_keys_written_on_unverified(self, mock_which, mock_post, mock_verify, mock_set, mock_sleep):
        """State keys reflect verified=False when verification exhausted."""
        request_copilot_review(42, "owner/repo")
        mock_set.assert_any_call("github.copilot_review_requested", True)
        mock_set.assert_any_call("github.copilot_review_request_verified", False)

    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._verify_reviewer_requested", return_value=True)
    @patch(f"{MODULE}._post_review_request", return_value=(True, None))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_repo_with_git_suffix_normalized(self, mock_which, mock_post, mock_verify, mock_set):
        """Repo with .git suffix is accepted and normalized."""
        result = request_copilot_review(42, "owner/repo.git")
        assert result["requested"] is True
        # _post_review_request should receive the normalized repo name
        mock_post.assert_called_once_with(42, "owner", "repo")

    @patch(f"{MODULE}.set_value")
    @patch(f"{MODULE}._verify_reviewer_requested", return_value=True)
    @patch(f"{MODULE}._post_review_request", return_value=(True, None))
    @patch(f"{MODULE}.shutil.which", return_value="/usr/bin/gh")
    def test_repo_with_whitespace_normalized(self, mock_which, mock_post, mock_verify, mock_set):
        """Repo with leading/trailing whitespace is accepted and normalized."""
        result = request_copilot_review(42, "  owner/repo  ")
        assert result["requested"] is True
        mock_post.assert_called_once_with(42, "owner", "repo")
