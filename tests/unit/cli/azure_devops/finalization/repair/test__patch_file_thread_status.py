"""Tests for _patch_file_thread_status function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment
from agentic_devtools.cli.azure_devops.finalization.repair import _patch_file_thread_status
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)


def _minimal_review_state(file_status="approved"):
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
                status=file_status,
            ),
        },
    )


def _mock_config():
    config = MagicMock()
    config.build_api_url.return_value = "https://api/url"
    return config


class TestPatchFileThreadStatus:
    """Tests for _patch_file_thread_status function."""

    def test_patches_thread_closed_for_approved(self):
        """Should set thread status to 'closed' for approved files."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        state = _minimal_review_state(file_status="approved")
        config = _mock_config()
        headers = {"Authorization": "Bearer token"}

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair.patch_thread_status",
        ) as mock_pts:
            _patch_file_thread_status(comment, state, config, headers, 42)

        mock_pts.assert_called_once_with(
            mock_pts.call_args[0][0],  # requests_module
            headers,
            config,
            "repo-guid",
            42,
            10,
            "closed",
        )

    def test_patches_thread_active_for_needs_work(self):
        """Should set thread status to 'active' for needs-work files."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        state = _minimal_review_state(file_status="needs-work")
        config = _mock_config()
        headers = {}

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair.patch_thread_status",
        ) as mock_pts:
            _patch_file_thread_status(comment, state, config, headers, 42)

        mock_pts.assert_called_once()
        assert mock_pts.call_args[0][6] == "active"

    def test_skips_when_no_file_path(self):
        """Should return early when comment has no file_path."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path=None,
        )
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair.patch_thread_status",
        ) as mock_pts:
            _patch_file_thread_status(
                comment, _minimal_review_state(), _mock_config(), {}, 42,
            )
        mock_pts.assert_not_called()

    def test_skips_when_file_not_in_review_state(self):
        """Should return early when file_path not found in review state."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/unknown/file.py",
        )
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair.patch_thread_status",
        ) as mock_pts:
            _patch_file_thread_status(
                comment, _minimal_review_state(), _mock_config(), {}, 42,
            )
        mock_pts.assert_not_called()

    def test_defaults_to_active_for_unknown_status(self):
        """Should default to 'active' for unknown file statuses."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        state = _minimal_review_state(file_status="unknown-status")

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.repair.patch_thread_status",
        ) as mock_pts:
            _patch_file_thread_status(comment, state, _mock_config(), {}, 42)

        mock_pts.assert_called_once()
        assert mock_pts.call_args[0][6] == "active"
