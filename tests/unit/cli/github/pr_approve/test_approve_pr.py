"""Tests for approve_pr core function."""

from unittest.mock import patch

from agentic_devtools.cli.github import pr_approve


class TestApprovePr:
    """Tests for approve_pr."""

    def test_full_success_flow(self):
        """Full success: approval submitted and verified."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")),
            patch.object(
                pr_approve,
                "_verify_approval",
                return_value=({"id": 999, "submitted_at": "2026-04-07T09:00:00Z"}, 0),
            ),
            patch.object(pr_approve, "set_value") as mock_set,
        ):
            result = pr_approve.approve_pr(42, "owner/repo")

        assert result["prNumber"] == 42
        assert result["repo"] == "owner/repo"
        assert result["approved"] is True
        assert result["reviewId"] == 999
        assert result["approver"] == "alice"
        assert result["submittedAt"] == "2026-04-07T09:00:00Z"
        assert result["verified"] is True
        assert result["retries"] == 0
        assert mock_set.called

    def test_full_success_flow_with_retries(self):
        """Success after retries: retries field reflects actual attempts."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")),
            patch.object(
                pr_approve,
                "_verify_approval",
                return_value=({"id": 999, "submitted_at": "2026-04-07T09:00:00Z"}, 1),
            ),
            patch.object(pr_approve, "set_value"),
        ):
            result = pr_approve.approve_pr(42, "owner/repo")

        assert result["verified"] is True
        assert result["retries"] == 1

    def test_approval_submission_failure(self):
        """Approval submission fails: returns approved=False."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(
                pr_approve,
                "_submit_approval",
                return_value=(False, "draft state"),
            ),
            patch.object(pr_approve, "set_value") as mock_set,
        ):
            result = pr_approve.approve_pr(42, "owner/repo")

        assert result["approved"] is False
        assert result["error"] == "approval_failed"
        assert result["message"] == "draft state"
        assert result["verified"] is False
        assert mock_set.called

    def test_verification_exhausted(self):
        """Approval submitted but verification fails."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")),
            patch.object(pr_approve, "_verify_approval", return_value=(None, 2)),
            patch.object(pr_approve, "set_value") as mock_set,
        ):
            result = pr_approve.approve_pr(42, "owner/repo")

        assert result["approved"] is True
        assert result["verified"] is False
        assert result["reviewId"] is None
        assert result["retries"] == 2
        assert mock_set.called

    def test_state_keys_written_on_success(self):
        """State keys written correctly on successful approval."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")),
            patch.object(
                pr_approve,
                "_verify_approval",
                return_value=({"id": 555, "submitted_at": "2026-01-01T00:00:00Z"}, 0),
            ),
            patch.object(pr_approve, "set_value") as mock_set,
        ):
            pr_approve.approve_pr(42, "owner/repo")

        calls = [call.args for call in mock_set.call_args_list]
        assert ("github.pr_approval_verified", True) in calls
        assert ("github.pr_approval_review_id", 555) in calls

    def test_state_keys_written_on_failure(self):
        """State keys written correctly on failed submission."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(
                pr_approve,
                "_submit_approval",
                return_value=(False, "error"),
            ),
            patch.object(pr_approve, "set_value") as mock_set,
        ):
            pr_approve.approve_pr(42, "owner/repo")

        calls = [call.args for call in mock_set.call_args_list]
        assert ("github.pr_approval_verified", False) in calls
        assert ("github.pr_approval_review_id", None) in calls

    def test_default_body_used(self):
        """Default body used when body is None."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")) as mock_submit,
            patch.object(
                pr_approve,
                "_verify_approval",
                return_value=({"id": 1, "submitted_at": "2026-01-01T00:00:00Z"}, 0),
            ),
            patch.object(pr_approve, "set_value"),
        ):
            pr_approve.approve_pr(42, "owner/repo", body=None)

        assert mock_submit.call_args[0][2] == "Approved via agdt-gh-pr-approve"

    def test_custom_body_passed_through(self):
        """Custom body is passed through to _submit_approval."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")) as mock_submit,
            patch.object(
                pr_approve,
                "_verify_approval",
                return_value=({"id": 1, "submitted_at": "2026-01-01T00:00:00Z"}, 0),
            ),
            patch.object(pr_approve, "set_value"),
        ):
            pr_approve.approve_pr(42, "owner/repo", body="Custom message")

        assert mock_submit.call_args[0][2] == "Custom message"

    def test_empty_string_body_preserved(self):
        """Empty string body is preserved, not replaced with default."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")) as mock_submit,
            patch.object(
                pr_approve,
                "_verify_approval",
                return_value=({"id": 1, "submitted_at": "2026-01-01T00:00:00Z"}, 0),
            ),
            patch.object(pr_approve, "set_value"),
        ):
            pr_approve.approve_pr(42, "owner/repo", body="")

        assert mock_submit.call_args[0][2] == ""

    def test_repo_normalized_before_downstream_calls(self):
        """Repo is normalized (stripped, .git removed) before _submit_approval and _verify_approval."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")) as mock_submit,
            patch.object(
                pr_approve,
                "_verify_approval",
                return_value=({"id": 1, "submitted_at": "2026-01-01T00:00:00Z"}, 0),
            ) as mock_verify,
            patch.object(pr_approve, "set_value"),
        ):
            pr_approve.approve_pr(42, "  owner/repo.git  ")

        # Both downstream calls receive the normalized repo
        assert mock_submit.call_args[0][1] == "owner/repo"
        assert mock_verify.call_args[0][1] == "owner/repo"

    def test_repo_in_result_uses_normalized_value(self):
        """Result dict contains the normalized repo, not the raw input."""
        with (
            patch.object(pr_approve, "_check_gh_available"),
            patch.object(pr_approve, "_resolve_current_user", return_value="alice"),
            patch.object(pr_approve, "_submit_approval", return_value=(True, "")),
            patch.object(
                pr_approve,
                "_verify_approval",
                return_value=({"id": 1, "submitted_at": "2026-01-01T00:00:00Z"}, 0),
            ),
            patch.object(pr_approve, "set_value"),
        ):
            result = pr_approve.approve_pr(42, "  owner/repo.git  ")

        assert result["repo"] == "owner/repo"
