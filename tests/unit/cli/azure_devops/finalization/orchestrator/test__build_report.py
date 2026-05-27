"""Tests for _build_report helper function."""

import time
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.finalization.orchestrator import _build_report
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


class TestBuildReportFunction:
    """Tests for _build_report function."""

    def test_calculates_duration(self, temp_state_dir):
        """Should calculate duration_ms from start_time."""
        start = time.monotonic()
        report = _build_report("success", 1, 0, 0, 0, ["detail"], start, _minimal_review_state())
        assert report.duration_ms >= 0
        assert report.status == "success"
        assert report.repaired == 1

    def test_passes_commit_hash_short_to_persist(self, temp_state_dir):
        """Should extract first 12 chars of commitHash for persist."""
        rs = _minimal_review_state()
        rs.commitHash = "abc123def456789"
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch("agentic_devtools.state.get_state_dir", return_value=temp_state_dir),
        ):
            _build_report("success", 0, 0, 0, 0, [], time.monotonic(), rs)
            assert mock_persist.call_args[0][2] == "abc123def456"

    def test_falls_back_to_state_value(self, temp_state_dir):
        """Should fall back to get_value when commitHash is None."""
        rs = _minimal_review_state()
        rs.commitHash = None
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch("agentic_devtools.state.get_state_dir", return_value=temp_state_dir),
            patch("agentic_devtools.state.get_value", return_value="fallback12ch"),
        ):
            _build_report("success", 0, 0, 0, 0, [], time.monotonic(), rs)
            assert mock_persist.call_args[0][2] == "fallback12ch"

    def test_falls_back_to_unknown_when_no_state(self, temp_state_dir):
        """Should use 'unknown' when both commitHash and state key are absent."""
        rs = _minimal_review_state()
        rs.commitHash = None
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch("agentic_devtools.state.get_state_dir", return_value=temp_state_dir),
            patch("agentic_devtools.state.get_value", return_value=None),
        ):
            _build_report("success", 0, 0, 0, 0, [], time.monotonic(), rs)
            assert mock_persist.call_args[0][2] == "unknown"

    def test_handles_none_review_state(self, temp_state_dir):
        """Should handle review_state=None gracefully."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch("agentic_devtools.state.get_state_dir", return_value=temp_state_dir),
            patch("agentic_devtools.state.get_value", return_value=None),
        ):
            report = _build_report("skipped", 0, 0, 0, 0, [], time.monotonic(), None)
            assert report.status == "skipped"
            assert mock_persist.call_args[0][2] == "unknown"

    def test_persist_exception_does_not_raise(self, temp_state_dir):
        """Should swallow persist_report exceptions without raising."""
        rs = _minimal_review_state()
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
                side_effect=Exception("disk full"),
            ),
            patch("agentic_devtools.state.get_state_dir", return_value=temp_state_dir),
        ):
            report = _build_report("success", 1, 0, 0, 0, [], time.monotonic(), rs)
            assert report.status == "success"

    def test_empty_commit_hash_uses_state_fallback(self, temp_state_dir):
        """Should treat empty commitHash string as falsy and fall back."""
        rs = _minimal_review_state()
        rs.commitHash = ""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch("agentic_devtools.state.get_state_dir", return_value=temp_state_dir),
            patch("agentic_devtools.state.get_value", return_value="state-hash"),
        ):
            _build_report("success", 0, 0, 0, 0, [], time.monotonic(), rs)
            assert mock_persist.call_args[0][2] == "state-hash"
