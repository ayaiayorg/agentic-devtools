"""Tests for run_finalization_pass orchestrator function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import (
    BatchRepairResult,
    ConvergenceResult,
    EligibleComment,
    EligibleComments,
    FinalizationReport,
)
from agentic_devtools.cli.azure_devops.finalization.orchestrator import (
    _build_report,
    run_finalization_pass,
)
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)


def _minimal_review_state():
    """Build a minimal ReviewState."""
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
    config.organization = "https://dev.azure.com/org"
    config.build_api_url.return_value = "https://api/threads"
    return config


class TestRunFinalizationPass:
    """Tests for run_finalization_pass function."""

    def test_returns_skipped_when_identity_fails(self, temp_state_dir):
        """Should return skipped status when PAT identity cannot be resolved."""
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
            return_value=None,
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
                dry_run=False,
            )
        assert isinstance(result, FinalizationReport)
        assert result.status == "skipped"

    def test_returns_skipped_when_threads_fail(self, temp_state_dir):
        """Should return skipped when thread fetching fails."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=None,
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "skipped"

    def test_returns_noop_when_no_eligible_comments(self, temp_state_dir):
        """Should return no-op when no eligible comments found."""
        from agentic_devtools.cli.azure_devops.finalization.models import EligibleComments

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=EligibleComments(),
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "no-op"

    def test_non_blocking_on_exception(self, temp_state_dir):
        """Should catch exceptions and return failure report."""
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
            side_effect=RuntimeError("unexpected"),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "failure"
        assert any("unexpected" in d for d in result.details)

    def test_missing_review_state_returns_report(self, temp_state_dir):
        """Should handle review state gracefully and return a report."""
        # The orchestrator always receives review_state as a parameter,
        # so this tests the exception path
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
            side_effect=Exception("state issue"),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert isinstance(result, FinalizationReport)

    def test_noop_when_all_converged(self, temp_state_dir):
        """Should return no-op when all eligible comments are already converged."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="correct content",
            file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="correct content",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "no-op"
        assert result.unchanged == 1
        assert any("already in terminal state" in d for d in result.details)

    def test_dry_run_returns_success(self, temp_state_dir):
        """Should return success with non-converged count in dry_run mode."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
                dry_run=True,
            )
        assert result.status == "success"
        assert result.repaired == 1

    def test_success_after_batch_repair_and_verification(self, temp_state_dir):
        """Should return success when batch repair + verification converge all comments."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])
        cr = ConvergenceResult(comment=comment, converged=True, expected_content="exp", observed_content="exp")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=[cr],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "success"
        assert result.repaired == 1

    def test_timeout_marks_remaining_as_failed(self, temp_state_dir):
        """Should mark remaining non-converged as failed on timeout."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])
        cr = ConvergenceResult(comment=comment, converged=False, expected_content="exp", observed_content="old")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "failure"
        assert result.failed == 1
        assert any("Timeout" in d for d in result.details)


class TestBuildReport:
    """Tests for _build_report helper."""

    def test_uses_review_state_commit_hash(self, temp_state_dir):
        """Should use review_state.commitHash for report filename."""
        import time

        rs = _minimal_review_state()
        rs.commitHash = "abc123def456789"

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch(
                "agentic_devtools.state.get_state_dir",
                return_value=temp_state_dir,
            ),
        ):
            _build_report("success", 0, 0, 0, 0, [], time.monotonic(), rs)
            mock_persist.assert_called_once()
            # commit_hash_short should be first 12 chars
            call_args = mock_persist.call_args
            assert call_args[0][2] == "abc123def456"

    def test_falls_back_to_state_key(self, temp_state_dir):
        """Should fall back to review.commit_hash_short state key when commitHash is None."""
        import time

        rs = _minimal_review_state()
        rs.commitHash = None

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch(
                "agentic_devtools.state.get_state_dir",
                return_value=temp_state_dir,
            ),
            patch(
                "agentic_devtools.state.get_value",
                return_value="short123hash",
            ),
        ):
            _build_report("success", 0, 0, 0, 0, [], time.monotonic(), rs)
            mock_persist.assert_called_once()
            assert mock_persist.call_args[0][2] == "short123hash"

    def test_handles_persist_exception(self, temp_state_dir):
        """Should not raise when persist_report fails."""
        import time

        rs = _minimal_review_state()

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
                side_effect=Exception("disk full"),
            ),
            patch(
                "agentic_devtools.state.get_state_dir",
                return_value=temp_state_dir,
            ),
        ):
            # Should not raise despite persist_report failure
            report = _build_report("success", 1, 0, 0, 0, [], time.monotonic(), rs)
            assert report.status == "success"

    def test_falls_back_to_unknown(self, temp_state_dir):
        """Should use 'unknown' when both commitHash and state key are absent."""
        import time

        rs = _minimal_review_state()
        rs.commitHash = None

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch(
                "agentic_devtools.state.get_state_dir",
                return_value=temp_state_dir,
            ),
            patch(
                "agentic_devtools.state.get_value",
                return_value=None,
            ),
        ):
            _build_report("success", 0, 0, 0, 0, [], time.monotonic(), rs)
            assert mock_persist.call_args[0][2] == "unknown"


class TestRunFinalizationPassAdvanced:
    """Additional tests for edge cases in run_finalization_pass."""

    def test_noop_with_skipped_comments(self, temp_state_dir):
        """Should include skipped comment info when no eligible but skipped exist."""
        eligible = EligibleComments(
            skipped=[{"thread_id": "5", "reason": "authored by other user"}],
        )
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.status == "no-op"
        assert result.skipped == 1
        assert any("authored by other user" in d for d in result.details)

    def test_noop_all_converged_with_skipped(self, temp_state_dir):
        """Should include skipped info in details when all converged but some skipped."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="correct", file_path="/src/a.py",
        )
        eligible = EligibleComments(
            file_summaries=[comment],
            skipped=[{"thread_id": "99", "reason": "different author"}],
        )
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="correct",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.status == "no-op"
        assert result.skipped == 1
        assert any("different author" in d for d in result.details)

    def test_batch_errors_recorded_in_details(self, temp_state_dir):
        """Should record batch repair errors in details."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])
        batch_result = BatchRepairResult(
            attempted=1, succeeded=0, failed=1,
            errors=["file-summary /src/a.py: API error"],
        )
        cr = ConvergenceResult(
            comment=comment, converged=True,
            expected_content="exp", observed_content="exp",
        )
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=batch_result,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=[cr],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert any("Batch error" in d for d in result.details)

    def test_targeted_repair_on_retry(self, temp_state_dir):
        """Should perform targeted repair when verification finds non-converged."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])
        cr_fail = ConvergenceResult(
            comment=comment, converged=False,
            expected_content="exp", observed_content="old",
        )
        cr_pass = ConvergenceResult(
            comment=comment, converged=True,
            expected_content="exp", observed_content="exp",
        )
        from agentic_devtools.cli.azure_devops.finalization.models import TargetedRepairResult

        targeted_result = TargetedRepairResult(attempted=1, succeeded=1)

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                side_effect=[[cr_fail], [cr_pass]],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.targeted_repair",
                return_value=targeted_result,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.time",
            ) as mock_time,
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            mock_time.monotonic.return_value = 100.0
            mock_time.sleep = MagicMock()
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.status == "success"
        assert any("targeted repair" in d for d in result.details)

    def test_max_retries_reached(self, temp_state_dir):
        """Should report failure when max retries are reached."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])
        cr_fail = ConvergenceResult(
            comment=comment, converged=False,
            expected_content="exp", observed_content="old",
        )
        from agentic_devtools.cli.azure_devops.finalization.models import TargetedRepairResult

        targeted_result = TargetedRepairResult(attempted=1, succeeded=0, failed=1)

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=[cr_fail],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.targeted_repair",
                return_value=targeted_result,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.time",
            ) as mock_time,
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            mock_time.monotonic.return_value = 100.0
            mock_time.sleep = MagicMock()
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.failed == 1
        assert any("Max retries" in d for d in result.details)

    def test_partial_status_when_some_converge(self, temp_state_dir):
        """Should return partial when some converge but some fail."""
        c1 = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        c2 = EligibleComment(
            thread_id=20, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old2", file_path="/src/b.py",
        )
        rs = _minimal_review_state()
        rs.files["/src/b.py"] = rs.files["/src/a.py"]
        eligible = EligibleComments(file_summaries=[c1, c2])
        cr1 = ConvergenceResult(comment=c1, converged=True, expected_content="e1", observed_content="e1")
        cr2 = ConvergenceResult(comment=c2, converged=False, expected_content="e2", observed_content="old2")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=2, succeeded=2),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=[cr1, cr2],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.targeted_repair",
                return_value=MagicMock(errors=[]),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.time",
            ) as mock_time,
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            mock_time.monotonic.return_value = 100.0
            mock_time.sleep = MagicMock()
            result = run_finalization_pass(rs, 42, _mock_config(), {})
        assert result.status == "partial"
        assert result.failed >= 1
        assert result.repaired >= 1

    def test_skipped_info_added_after_retry_loop(self, temp_state_dir):
        """Should add skipped info at the end of the retry loop."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        eligible = EligibleComments(
            file_summaries=[comment],
            skipped=[{"thread_id": "77", "reason": "other author"}],
        )
        cr = ConvergenceResult(comment=comment, converged=True, expected_content="exp", observed_content="exp")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=[cr],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.skipped == 1
        assert any("other author" in d for d in result.details)

    def test_targeted_repair_errors_recorded(self, temp_state_dir):
        """Should record targeted repair errors in details."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])
        cr_fail = ConvergenceResult(
            comment=comment, converged=False,
            expected_content="exp", observed_content="old",
        )
        cr_pass = ConvergenceResult(
            comment=comment, converged=True,
            expected_content="exp", observed_content="exp",
        )
        from agentic_devtools.cli.azure_devops.finalization.models import TargetedRepairResult

        targeted_result = TargetedRepairResult(
            attempted=1, succeeded=0, failed=1,
            errors=["file-summary thread=10: PATCH failed"],
        )

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                side_effect=[[cr_fail], [cr_pass]],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.targeted_repair",
                return_value=targeted_result,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.time",
            ) as mock_time,
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            mock_time.monotonic.return_value = 100.0
            mock_time.sleep = MagicMock()
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert any("Targeted repair error" in d for d in result.details)

    def test_seeding_includes_initially_converged(self, temp_state_dir):
        """Should seed converged_keys with comments that pass check_convergence in Phase 6."""
        c1 = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old1", file_path="/src/a.py",
        )
        c2 = EligibleComment(
            thread_id=20, comment_id=2, marker_type="file-summary",
            marker_data={}, current_content="old2", file_path="/src/b.py",
        )
        rs = _minimal_review_state()
        rs.files["/src/b.py"] = FileEntry(
            threadId=20, commentId=2, folder="src", fileName="b.py", status="approved",
        )
        eligible = EligibleComments(file_summaries=[c1, c2])
        cr_both = [
            ConvergenceResult(comment=c1, converged=True, expected_content="e1", observed_content="e1"),
            ConvergenceResult(comment=c2, converged=True, expected_content="e2", observed_content="e2"),
        ]

        # Phase 4: c1→True(unchanged), c2→False(non_converged)
        # Phase 6 seeding: c1→True(seeded!), c2→True(seeded)
        check_side = [True, False, True, True]

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                side_effect=check_side,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=cr_both,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.time",
            ) as mock_time,
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            mock_time.monotonic.return_value = 100.0
            mock_time.sleep = MagicMock()
            result = run_finalization_pass(rs, 42, _mock_config(), {})
        assert result.status == "success"
        # 1 was already converged (unchanged), 1 was repaired
        assert result.unchanged >= 1

    def test_falls_back_to_unknown_when_no_hash_available(self, temp_state_dir):
        """Should use 'unknown' when no commit hash is available."""
        import time

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.persist_report",
            ) as mock_persist,
            patch(
                "agentic_devtools.state.get_state_dir",
                return_value=temp_state_dir,
            ),
            patch(
                "agentic_devtools.state.get_value",
                return_value=None,
            ),
        ):
            _build_report("success", 0, 0, 0, 0, [], time.monotonic(), None)
            mock_persist.assert_called_once()
            assert mock_persist.call_args[0][2] == "unknown"

    def test_partial_status_when_some_repaired_and_some_failed(self, temp_state_dir):
        """Should return 'partial' when some comments repaired but others failed."""
        c1 = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old1", file_path="/src/a.py",
        )
        c2 = EligibleComment(
            thread_id=20, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old2", file_path="/src/b.py",
        )
        rs = _minimal_review_state()
        rs.files["/src/b.py"] = FileEntry(
            threadId=20, commentId=1, folder="src", fileName="b.py", status="approved",
        )
        eligible = EligibleComments(file_summaries=[c1, c2])

        cr1_pass = ConvergenceResult(
            comment=c1, converged=True, expected_content="e1", observed_content="e1",
        )
        cr2_fail = ConvergenceResult(
            comment=c2, converged=False, expected_content="e2", observed_content="old2",
        )

        from agentic_devtools.cli.azure_devops.finalization.models import TargetedRepairResult

        targeted_result = TargetedRepairResult(attempted=1, succeeded=0, failed=1)

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=2, succeeded=1, failed=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=[cr1_pass, cr2_fail],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.targeted_repair",
                return_value=targeted_result,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.time",
            ) as mock_time,
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            mock_time.monotonic.return_value = 100.0
            mock_time.sleep = MagicMock()
            result = run_finalization_pass(rs, 42, _mock_config(), {})
        assert result.status == "partial"
        assert result.repaired >= 1
        assert result.failed >= 1

    def test_failure_status_when_none_repaired(self, temp_state_dir):
        """Should return 'failure' when no comments repaired and some failed."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        eligible = EligibleComments(file_summaries=[comment])
        cr_fail = ConvergenceResult(
            comment=comment, converged=False,
            expected_content="exp", observed_content="old",
        )

        from agentic_devtools.cli.azure_devops.finalization.models import TargetedRepairResult

        targeted_result = TargetedRepairResult(attempted=1, succeeded=0, failed=1)

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=0, failed=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=[cr_fail],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.targeted_repair",
                return_value=targeted_result,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.time",
            ) as mock_time,
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            mock_time.monotonic.return_value = 100.0
            mock_time.sleep = MagicMock()
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.status == "failure"
        assert result.failed >= 1

    def test_skipped_added_after_successful_repair_loop(self, temp_state_dir):
        """Should add skipped info after the repair loop completes successfully."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        eligible = EligibleComments(
            file_summaries=[comment],
            skipped=[{"thread_id": "55", "reason": "authored by bot"}],
        )
        cr = ConvergenceResult(
            comment=comment, converged=True,
            expected_content="exp", observed_content="exp",
        )

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="expected",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.batch_repair_pass",
                return_value=BatchRepairResult(attempted=1, succeeded=1),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.verify_convergence",
                return_value=[cr],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._check_timeout",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.skipped == 1
        assert any("authored by bot" in d for d in result.details)

    def test_noop_when_all_comments_have_empty_expected_content(self, temp_state_dir):
        """Should return no-op when all eligible comments have empty expected content."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/missing.py",
        )
        eligible = EligibleComments(file_summaries=[comment])

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                return_value="",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.status == "no-op"
        assert result.skipped == 1
        assert any("empty expected content" in d for d in result.details)
        assert any("All eligible comments had empty expected content" in d for d in result.details)

    def test_some_comments_with_empty_expected_content_are_skipped(self, temp_state_dir):
        """Should skip comments with empty expected content and proceed with the rest."""
        c1 = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        c2 = EligibleComment(
            thread_id=20, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old2", file_path="/src/missing.py",
        )
        eligible = EligibleComments(file_summaries=[c1, c2])

        def expected_side_effect(comment, _rs, _url):
            if comment.file_path == "/src/missing.py":
                return ""
            return "expected content"

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                side_effect=expected_side_effect,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.status == "no-op"
        assert result.skipped == 1
        assert result.unchanged == 1
        assert any("empty expected content" in d for d in result.details)

    def test_overall_summary_with_empty_expected_content_is_skipped(self, temp_state_dir):
        """Should skip overall summary when it has empty expected content."""
        file_comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        overall_comment = EligibleComment(
            thread_id=100, comment_id=1, marker_type="overall-summary",
            marker_data={}, current_content="old-overall",
        )
        eligible = EligibleComments(
            file_summaries=[file_comment],
            overall_summary=overall_comment,
        )

        def expected_side_effect(comment, _rs, _url):
            if comment.marker_type == "overall-summary":
                return ""
            return "expected content"

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[{"id": 10}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=eligible,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.compute_expected_content",
                side_effect=expected_side_effect,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.check_convergence",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://base",
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(), 42, _mock_config(), {},
            )
        assert result.status == "no-op"
        assert result.skipped == 1
        assert result.unchanged == 1
        assert any("empty expected content" in d for d in result.details)
