"""Tests for is_copilot_session_active_via_agent_task."""

import json
import subprocess
from unittest.mock import patch

from agentic_devtools.cli.ci.pipeline.session_detector import (
    is_copilot_session_active_via_agent_task,
)


class TestIsCopilotSessionActiveViaAgentTask:
    """Tests for the gh agent-task based session detector."""

    def _make_result(self, *, stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")

    def test_running_task_returns_true(self) -> None:
        """A running task for the target PR returns True."""
        tasks = [
            {"id": "task-1", "status": "in_progress", "pullRequestNumber": 42, "createdAt": "2024-01-01T00:00:00Z"},
        ]
        result = self._make_result(stdout=json.dumps(tasks))
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is True

    def test_queued_task_returns_true(self) -> None:
        tasks = [{"id": "task-1", "status": "queued", "pullRequestNumber": 42, "createdAt": "2024-01-01T00:00:00Z"}]
        result = self._make_result(stdout=json.dumps(tasks))
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is True

    def test_completed_task_returns_false(self) -> None:
        tasks = [{"id": "task-1", "status": "completed", "pullRequestNumber": 42, "createdAt": "2024-01-01T00:00:00Z"}]
        result = self._make_result(stdout=json.dumps(tasks))
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_stopped_task_returns_false(self) -> None:
        tasks = [{"id": "task-1", "status": "stopped", "pullRequestNumber": 42, "createdAt": "2024-01-01T00:00:00Z"}]
        result = self._make_result(stdout=json.dumps(tasks))
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_empty_list_returns_false(self) -> None:
        result = self._make_result(stdout="[]")
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_different_pr_number_returns_false(self) -> None:
        """Tasks for a different PR do not affect the result."""
        tasks = [
            {"id": "task-1", "status": "in_progress", "pullRequestNumber": 99, "createdAt": "2024-01-01T00:00:00Z"},
        ]
        result = self._make_result(stdout=json.dumps(tasks))
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_mixed_status_returns_true(self) -> None:
        """If any task for the PR is in an active status, returns True."""
        tasks = [
            {"id": "task-1", "status": "completed", "pullRequestNumber": 42, "createdAt": "2024-01-01T00:00:00Z"},
            {"id": "task-2", "status": "running", "pullRequestNumber": 42, "createdAt": "2024-01-01T01:00:00Z"},
        ]
        result = self._make_result(stdout=json.dumps(tasks))
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is True

    def test_timeout_returns_false_fail_open(self) -> None:
        """Timeout results in False (fail-open)."""
        with patch(
            "agentic_devtools.cli.ci.pipeline.session_detector.run_safe",
            side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=10),
        ):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_nonzero_exit_returns_false_fail_open(self) -> None:
        """Non-zero exit code results in False (fail-open)."""
        result = self._make_result(stdout="", returncode=1)
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_malformed_json_returns_false_fail_open(self) -> None:
        """Malformed JSON results in False (fail-open)."""
        result = self._make_result(stdout="not json at all")
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_missing_binary_returns_false_fail_open(self) -> None:
        """FileNotFoundError (missing gh binary) results in False (fail-open)."""
        with patch(
            "agentic_devtools.cli.ci.pipeline.session_detector.run_safe", side_effect=FileNotFoundError("gh not found")
        ):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_permission_error_returns_false_fail_open(self) -> None:
        """PermissionError results in False (fail-open)."""
        with patch(
            "agentic_devtools.cli.ci.pipeline.session_detector.run_safe",
            side_effect=PermissionError("permission denied"),
        ):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_os_error_returns_false_fail_open(self) -> None:
        """OSError results in False (fail-open)."""
        with patch(
            "agentic_devtools.cli.ci.pipeline.session_detector.run_safe", side_effect=OSError("general OS error")
        ):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_non_list_json_returns_false_fail_open(self) -> None:
        """If JSON is valid but not a list, returns False (fail-open)."""
        result = self._make_result(stdout='{"error": "something"}')
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is False

    def test_non_dict_items_are_ignored(self) -> None:
        """Non-dict list items are ignored while scanning tasks."""
        tasks = ["unexpected-string", {"id": "task-1", "status": "running", "pullRequestNumber": 42}]
        result = self._make_result(stdout=json.dumps(tasks))
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42) is True

    def test_calls_run_safe_with_correct_args(self) -> None:
        """Verify run_safe is called with the correct arguments and flags."""
        result = self._make_result(stdout="[]")
        with patch("agentic_devtools.cli.ci.pipeline.session_detector.run_safe", return_value=result) as mock_run:
            is_copilot_session_active_via_agent_task("owner/repo", 42, timeout_seconds=15)
            mock_run.assert_called_once_with(
                ["gh", "agent-task", "list", "--repo", "owner/repo", "--json", "id,status,pullRequestNumber,createdAt"],
                capture_output=True,
                text=True,
                shell=False,
                timeout=15,
            )

    def test_custom_timeout(self) -> None:
        """Custom timeout_seconds is forwarded to subprocess.run."""
        with patch(
            "agentic_devtools.cli.ci.pipeline.session_detector.run_safe",
            side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=5),
        ):
            assert is_copilot_session_active_via_agent_task("owner/repo", 42, timeout_seconds=5) is False
