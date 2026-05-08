"""Tests for targeted_repair function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment
from agentic_devtools.cli.azure_devops.finalization.repair import targeted_repair
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)


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
        files={"/src/a.py": FileEntry(threadId=10, commentId=1, folder="src", fileName="a.py", status="approved")},
    )


def _mock_config():
    config = MagicMock()
    config.build_api_url.return_value = "https://api/url"
    return config


class TestTargetedRepair:
    """Tests for targeted_repair function."""

    def test_dry_run_skips_mutations(self):
        """Should not make API calls in dry-run mode."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        result = targeted_repair(
            [comment],
            {(10, 1): "expected content"},
            _mock_config(),
            {},
            42,
            _minimal_review_state(),
            dry_run=True,
        )
        assert result.attempted == 1
        assert result.succeeded == 1

    def test_patches_non_converged_comment(self):
        """Should PATCH non-converged comments."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.repair.patch_comment",
            ) as mock_pc,
            patch(
                "agentic_devtools.cli.azure_devops.finalization.repair._patch_file_thread_status",
            ) as mock_pts,
        ):
            result = targeted_repair(
                [comment],
                {(10, 1): "expected content"},
                _mock_config(),
                {},
                42,
                _minimal_review_state(),
            )
        assert result.succeeded == 1
        mock_pc.assert_called_once()
        mock_pts.assert_called_once()

    def test_handles_missing_expected_content(self):
        """Should fail gracefully when expected content is missing."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=99,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        result = targeted_repair(
            [comment],
            {},
            _mock_config(),
            {},
            42,
            _minimal_review_state(),
        )
        assert result.failed == 1

    def test_repairs_activity_log_entry(self):
        """Should call _targeted_repair_activity_log for activity-log-entry type."""
        comment = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={"type": "activity-log-entry"},
            current_content="old log",
        )

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair._targeted_repair_activity_log",
        ) as mock_repair:
            result = targeted_repair(
                [comment],
                {(200, 2): "expected log content"},
                _mock_config(),
                {},
                42,
                _minimal_review_state(),
            )
        assert result.succeeded == 1
        mock_repair.assert_called_once()

    def test_catches_api_error_on_activity_log_repair(self):
        """Should catch and record error when activity-log-entry repair fails."""
        comment = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={"type": "activity-log-entry"},
            current_content="old log",
        )

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair._targeted_repair_activity_log",
            side_effect=Exception("repair failed"),
        ):
            result = targeted_repair(
                [comment],
                {(200, 2): "expected content"},
                _mock_config(),
                {},
                42,
                _minimal_review_state(),
            )
        assert result.failed == 1
        assert any("activity-log-entry" in e for e in result.errors)

    def test_skips_thread_status_for_non_file_summary(self):
        """Should NOT call _patch_file_thread_status for non-file-summary types."""
        comment = EligibleComment(
            thread_id=100,
            comment_id=1,
            marker_type="overall-summary",
            marker_data={},
            current_content="old",
            file_path=None,
        )

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.repair.patch_comment",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.repair._patch_file_thread_status",
            ) as mock_pts,
        ):
            result = targeted_repair(
                [comment],
                {(100, 1): "expected content"},
                _mock_config(),
                {},
                42,
                _minimal_review_state(),
            )
        assert result.succeeded == 1
        mock_pts.assert_not_called()
