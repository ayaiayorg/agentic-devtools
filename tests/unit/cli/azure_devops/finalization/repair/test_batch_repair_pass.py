"""Tests for batch_repair_pass function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment, EligibleComments
from agentic_devtools.cli.azure_devops.finalization.repair import batch_repair_pass
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"


def _minimal_review_state():
    return ReviewState(
        prId=42,
        repoId="repo-guid",
        repoName="test-repo",
        project="TestProject",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=100, commentId=1, status="approved"),
        folders={"src": FolderGroup(files=["/src/a.py"])},
        files={
            "/src/a.py": FileEntry(
                threadId=10,
                commentId=1,
                folder="src",
                fileName="a.py",
                status="approved",
                summary="LGTM",
            ),
        },
    )


def _mock_config():
    config = MagicMock()
    config.organization = "https://dev.azure.com/org"
    config.build_api_url.return_value = "https://api/url"
    return config


class TestBatchRepairPass:
    """Tests for batch_repair_pass function."""

    def test_dry_run_skips_mutations(self):
        """Should not make API calls in dry-run mode."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/src/a.py"},
                    current_content="old",
                    file_path="/src/a.py",
                )
            ],
        )
        result = batch_repair_pass(
            eligible,
            _minimal_review_state(),
            _mock_config(),
            {},
            42,
            _BASE_URL,
            dry_run=True,
        )
        assert result.attempted == 1
        assert result.succeeded == 1
        assert result.failed == 0

    def test_dry_run_does_not_mutate_non_terminal_statuses(self):
        """Should not mutate review_state file statuses in dry-run mode."""
        state = _minimal_review_state()
        state.files["/src/a.py"].status = "in-progress"

        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/src/a.py"},
                    current_content="old",
                    file_path="/src/a.py",
                )
            ],
        )
        batch_repair_pass(
            eligible,
            state,
            _mock_config(),
            {},
            42,
            _BASE_URL,
            dry_run=True,
        )
        # Status must remain unmutated in dry-run mode
        assert state.files["/src/a.py"].status == "in-progress"

    def test_patches_file_summary(self):
        """Should PATCH file summary comments."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/src/a.py"},
                    current_content="old",
                    file_path="/src/a.py",
                )
            ],
        )

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.repair.patch_comment",
            ) as mock_pc,
            patch(
                "agentic_devtools.cli.azure_devops.finalization.repair._patch_file_thread_status",
            ) as mock_pts,
        ):
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.succeeded == 1
        assert result.failed == 0
        mock_pc.assert_called_once()
        mock_pts.assert_called_once()

    def test_catches_api_errors(self):
        """Should catch API errors and continue."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/src/a.py"},
                    current_content="old",
                    file_path="/src/a.py",
                )
            ],
        )

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair.patch_comment",
            side_effect=Exception("API error"),
        ):
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_skips_patch_when_already_converged(self):
        """Should skip PATCH for comments that are already converged."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/src/a.py"},
                    current_content="already correct",
                    file_path="/src/a.py",
                )
            ],
        )

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.repair.check_convergence",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.repair.patch_comment",
            ) as mock_pc,
        ):
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.attempted == 1
        assert result.succeeded == 1
        # No patch_comment call should have been made
        mock_pc.assert_not_called()

    def test_skips_patch_when_expected_content_empty(self):
        """Should skip PATCH and record failure when expected content is empty."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/missing/file.py"},
                    current_content="old",
                    file_path="/missing/file.py",
                )
            ],
        )

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair.compute_expected_content",
            return_value="",
        ):
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.attempted == 1
        assert result.failed == 1
        assert result.succeeded == 0
        assert "empty expected content" in result.errors[0]

    def test_repairs_overall_summary_via_cascade(self):
        """Should repair overall summary by calling _cascade_overall_summary."""
        eligible = EligibleComments(
            overall_summary=EligibleComment(
                thread_id=100,
                comment_id=1,
                marker_type="overall-summary",
                marker_data={"type": "overall-summary"},
                current_content="old",
            ),
        )
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair._cascade_overall_summary",
        ) as mock_cascade:
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.attempted == 1
        assert result.succeeded == 1
        mock_cascade.assert_called_once()

    def test_overall_summary_cascade_error(self):
        """Should catch and record error when overall summary cascade fails."""
        eligible = EligibleComments(
            overall_summary=EligibleComment(
                thread_id=100,
                comment_id=1,
                marker_type="overall-summary",
                marker_data={"type": "overall-summary"},
                current_content="old",
            ),
        )
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair._cascade_overall_summary",
            side_effect=Exception("cascade failed"),
        ):
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.failed == 1
        assert any("overall-summary" in e for e in result.errors)

    def test_overall_summary_dry_run(self):
        """Should count overall summary as succeeded in dry-run mode."""
        eligible = EligibleComments(
            overall_summary=EligibleComment(
                thread_id=100,
                comment_id=1,
                marker_type="overall-summary",
                marker_data={"type": "overall-summary"},
                current_content="old",
            ),
        )
        result = batch_repair_pass(
            eligible,
            _minimal_review_state(),
            _mock_config(),
            {},
            42,
            _BASE_URL,
            dry_run=True,
        )
        assert result.attempted == 1
        assert result.succeeded == 1

    def test_completes_activity_log_session(self):
        """Should complete activity log session when entries exist."""
        eligible = EligibleComments(
            activity_log_entries=[
                EligibleComment(
                    thread_id=200,
                    comment_id=2,
                    marker_type="activity-log-entry",
                    marker_data={"type": "activity-log-entry"},
                    current_content="log entry",
                ),
            ],
        )
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair._complete_activity_log",
        ) as mock_complete:
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.activity_log_completed is True
        mock_complete.assert_called_once()

    def test_activity_log_dry_run(self):
        """Should set activity_log_completed in dry-run mode without mutations."""
        eligible = EligibleComments(
            activity_log_entries=[
                EligibleComment(
                    thread_id=200,
                    comment_id=2,
                    marker_type="activity-log-entry",
                    marker_data={"type": "activity-log-entry"},
                    current_content="log entry",
                ),
            ],
        )
        result = batch_repair_pass(
            eligible,
            _minimal_review_state(),
            _mock_config(),
            {},
            42,
            _BASE_URL,
            dry_run=True,
        )
        assert result.activity_log_completed is True

    def test_activity_log_error_is_recorded(self):
        """Should record error when activity log completion fails."""
        eligible = EligibleComments(
            activity_log_entries=[
                EligibleComment(
                    thread_id=200,
                    comment_id=2,
                    marker_type="activity-log-entry",
                    marker_data={"type": "activity-log-entry"},
                    current_content="log entry",
                ),
            ],
        )
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair._complete_activity_log",
            side_effect=Exception("activity log failed"),
        ):
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.activity_log_completed is False
        assert any("activity-log completion" in e for e in result.errors)
