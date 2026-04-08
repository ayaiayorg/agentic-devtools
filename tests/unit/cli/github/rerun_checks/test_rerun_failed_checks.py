"""Tests for rerun_failed_checks."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.rerun_checks import rerun_failed_checks

_MOD = "agentic_devtools.cli.github.rerun_checks"


class TestRerunFailedChecks:
    """Tests for the rerun_failed_checks orchestration function."""

    @patch(f"{_MOD}.set_value")
    @patch(f"{_MOD}._rerun_single_workflow")
    @patch(f"{_MOD}._filter_failed_runs")
    @patch(f"{_MOD}._fetch_workflow_runs")
    def test_full_flow_two_reruns(self, mock_fetch, mock_filter, mock_rerun, mock_set):
        """Two eligible runs both re-run successfully."""
        runs_data = [
            {"id": 1, "name": "Gate", "event": "push", "conclusion": "failure"},
            {"id": 2, "name": "Gate", "event": "pr", "conclusion": "failure"},
        ]
        mock_fetch.return_value = runs_data
        mock_filter.return_value = (runs_data, [])
        mock_rerun.return_value = (True, "triggered")

        result = rerun_failed_checks(
            pr_number=100,
            repo="owner/repo",
            head_sha="abc",
        )

        assert result["rerunCount"] == 2
        assert result["skippedCount"] == 0
        assert result["failedToRerunCount"] == 0
        assert result["prNumber"] == 100
        assert result["repo"] == "owner/repo"
        assert result["headRefOid"] == "abc"
        assert len(result["rerunWorkflows"]) == 2
        assert all(w["rerunStatus"] == "triggered" for w in result["rerunWorkflows"])

    @patch(f"{_MOD}.set_value")
    @patch(f"{_MOD}._rerun_single_workflow")
    @patch(f"{_MOD}._filter_failed_runs")
    @patch(f"{_MOD}._fetch_workflow_runs")
    def test_mixed_success_and_failure(self, mock_fetch, mock_filter, mock_rerun, mock_set):
        """One rerun succeeds, another fails."""
        eligible = [
            {"id": 1, "name": "A", "event": "push", "conclusion": "failure"},
            {"id": 2, "name": "B", "event": "push", "conclusion": "failure"},
        ]
        mock_fetch.return_value = eligible
        mock_filter.return_value = (eligible, [])
        mock_rerun.side_effect = [(True, "triggered"), (False, "403")]

        result = rerun_failed_checks(100, "o/r", "sha")

        assert result["rerunCount"] == 1
        assert result["failedToRerunCount"] == 1
        assert result["failedToRerun"][0]["error"] == "403"

    @patch(f"{_MOD}.set_value")
    @patch(f"{_MOD}._rerun_single_workflow")
    @patch(f"{_MOD}._filter_failed_runs")
    @patch(f"{_MOD}._fetch_workflow_runs")
    def test_state_keys_written(self, mock_fetch, mock_filter, mock_rerun, mock_set):
        """State keys are written after orchestration."""
        mock_fetch.return_value = [{"id": 1, "name": "X", "event": "p", "conclusion": "failure"}]
        mock_filter.return_value = (
            [{"id": 1, "name": "X", "event": "p", "conclusion": "failure"}],
            [],
        )
        mock_rerun.return_value = (True, "triggered")

        rerun_failed_checks(1, "o/r", "sha")

        mock_set.assert_any_call("github.rerun_checks_count", 1)
        mock_set.assert_any_call("github.rerun_checks_failed_to_rerun", 0)

    @patch(f"{_MOD}.set_value")
    @patch(f"{_MOD}._rerun_single_workflow")
    @patch(f"{_MOD}._filter_failed_runs")
    @patch(f"{_MOD}._fetch_workflow_runs")
    def test_name_filter_passed_through(self, mock_fetch, mock_filter, mock_rerun, mock_set):
        """Name filter is passed to _filter_failed_runs."""
        mock_fetch.return_value = []
        mock_filter.return_value = ([], [])

        rerun_failed_checks(1, "o/r", "sha", name_filter="Gate")

        mock_filter.assert_called_once_with([], "Gate", True)

    @patch(f"{_MOD}.set_value")
    @patch(f"{_MOD}._rerun_single_workflow")
    @patch(f"{_MOD}._filter_failed_runs")
    @patch(f"{_MOD}._fetch_workflow_runs")
    def test_no_eligible_runs(self, mock_fetch, mock_filter, mock_rerun, mock_set):
        """No eligible runs results in zero counts."""
        mock_fetch.return_value = [{"id": 1, "name": "CI", "conclusion": "success"}]
        mock_filter.return_value = ([], [])

        result = rerun_failed_checks(1, "o/r", "sha")

        assert result["rerunCount"] == 0
        assert result["failedToRerunCount"] == 0
        mock_rerun.assert_not_called()

    @patch(f"{_MOD}.set_value")
    @patch(f"{_MOD}._rerun_single_workflow")
    @patch(f"{_MOD}._filter_failed_runs")
    @patch(f"{_MOD}._fetch_workflow_runs")
    def test_include_cancelled_passed_through(self, mock_fetch, mock_filter, mock_rerun, mock_set):
        """include_cancelled flag is passed through to _filter_failed_runs."""
        mock_fetch.return_value = []
        mock_filter.return_value = ([], [])

        rerun_failed_checks(1, "o/r", "sha", include_cancelled=False)

        mock_filter.assert_called_once_with([], None, False)

    @patch(f"{_MOD}.set_value")
    @patch(f"{_MOD}._rerun_single_workflow")
    @patch(f"{_MOD}._filter_failed_runs")
    @patch(f"{_MOD}._fetch_workflow_runs")
    def test_skipped_workflows_in_output(self, mock_fetch, mock_filter, mock_rerun, mock_set):
        """Skipped workflows appear in output with reason."""
        skipped = [{"id": 3, "name": "CI", "event": "push", "conclusion": "failure"}]
        mock_fetch.return_value = []
        mock_filter.return_value = ([], skipped)

        result = rerun_failed_checks(1, "o/r", "sha", name_filter="Gate")

        assert result["skippedCount"] == 1
        assert result["skippedWorkflows"][0]["reason"] == "excluded-by-filter"
        assert result["filter"] == "Gate"

    def test_invalid_repo_format_exits(self, capsys):
        """Exits with code 1 when repo format is invalid."""
        with pytest.raises(SystemExit) as exc_info:
            rerun_failed_checks(1, "justrepo", "sha")

        assert exc_info.value.code == 1
        assert "Invalid repo format" in capsys.readouterr().err

    @patch(f"{_MOD}.set_value")
    @patch(f"{_MOD}._rerun_single_workflow")
    @patch(f"{_MOD}._filter_failed_runs")
    @patch(f"{_MOD}._fetch_workflow_runs")
    def test_repo_normalized_before_use(self, mock_fetch, mock_filter, mock_rerun, mock_set):
        """Repo string is stripped/normalized before being passed to helpers."""
        mock_fetch.return_value = []
        mock_filter.return_value = ([], [])

        rerun_failed_checks(1, "  owner/repo  ", "sha")

        mock_fetch.assert_called_once_with("owner/repo", "sha")
