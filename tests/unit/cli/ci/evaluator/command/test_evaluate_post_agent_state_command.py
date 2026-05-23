"""Tests for evaluate_post_agent_state_command() CLI entry point."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.evaluator.command import evaluate_post_agent_state_command
from agentic_devtools.cli.ci.evaluator.models import (
    EvaluationResult,
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
)


class TestEvaluatePostAgentStateCommand:
    """Tests for evaluate_post_agent_state_command."""

    def test_missing_pr_number_exits(self, capsys):
        """Exits with error when PR number is not provided."""
        with (
            patch("sys.argv", ["agdt-evaluate-post-agent-state"]),
            patch("agentic_devtools.cli.ci.evaluator.command.get_value", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            evaluate_post_agent_state_command()

        assert exc_info.value.code == 1

    def test_missing_repo_exits(self, capsys):
        """Exits with error when repo is not provided."""
        with (
            patch("sys.argv", ["agdt-evaluate-post-agent-state", "--pr", "42"]),
            patch("agentic_devtools.cli.ci.evaluator.command.get_value", return_value=None),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.resolve_github_repo",
                side_effect=SystemExit(1),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            evaluate_post_agent_state_command()

        assert exc_info.value.code == 1

    def test_concurrent_lock_returns_skipped(self, capsys):
        """Outputs concurrent_evaluation_skipped when lock can't be acquired."""
        with (
            patch("sys.argv", ["agdt-evaluate-post-agent-state", "--pr", "42", "--repo", "o/r"]),
            patch("agentic_devtools.cli.ci.evaluator.command.get_value", return_value=None),
            patch("agentic_devtools.cli.ci.evaluator.command.set_value"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.resolve_github_repo",
                return_value="o/r",
            ),
            patch("agentic_devtools.cli.ci.evaluator.command.GitHubActionsProvider"),
            patch("agentic_devtools.cli.ci.evaluator.command.acquire_lock", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            evaluate_post_agent_state_command()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["classification"] == "concurrent_evaluation_skipped"

    def test_dry_run_skips_lock(self, capsys):
        """Dry run mode skips lock acquisition."""
        snap = PostAgentSnapshot(pr_number=42, repo="o/r", has_sentinel=True)
        with (
            patch("sys.argv", ["agdt-evaluate-post-agent-state", "--pr", "42", "--repo", "o/r", "--dry-run"]),
            patch("agentic_devtools.cli.ci.evaluator.command.get_value", return_value=None),
            patch("agentic_devtools.cli.ci.evaluator.command.set_value"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.resolve_github_repo",
                return_value="o/r",
            ),
            patch("agentic_devtools.cli.ci.evaluator.command.GitHubActionsProvider"),
            patch("agentic_devtools.cli.ci.evaluator.command.build_snapshot", return_value=snap),
            patch("agentic_devtools.cli.ci.evaluator.command.acquire_lock") as mock_lock,
        ):
            evaluate_post_agent_state_command()

        mock_lock.assert_not_called()
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["classification"] == "complete"
        assert result["dry_run"] is True

    def test_end_to_end_complete_classification(self, capsys):
        """End-to-end: sentinel present → complete → no_action."""
        snap = PostAgentSnapshot(pr_number=42, repo="o/r", has_sentinel=True)
        with (
            patch("sys.argv", ["agdt-evaluate-post-agent-state", "--pr", "42", "--repo", "o/r"]),
            patch("agentic_devtools.cli.ci.evaluator.command.get_value", return_value=None),
            patch("agentic_devtools.cli.ci.evaluator.command.set_value") as mock_set,
            patch(
                "agentic_devtools.cli.ci.evaluator.command.resolve_github_repo",
                return_value="o/r",
            ),
            patch("agentic_devtools.cli.ci.evaluator.command.GitHubActionsProvider"),
            patch("agentic_devtools.cli.ci.evaluator.command.acquire_lock", return_value="token"),
            patch("agentic_devtools.cli.ci.evaluator.command.release_lock"),
            patch("agentic_devtools.cli.ci.evaluator.command.build_snapshot", return_value=snap) as mock_build,
        ):
            evaluate_post_agent_state_command()

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["classification"] == "complete"
        assert result["action_taken"] == "no_action"
        assert result["success"] is True
        provider_arg, pr_arg, repo_arg = mock_build.call_args.args
        assert provider_arg is not None
        assert (pr_arg, repo_arg) == (42, "o/r")
        assert mock_build.call_args.kwargs == {"current_lock_token": "token"}

        # Verify state was written
        calls = {c[0][0]: c[0][1] for c in mock_set.call_args_list}
        assert calls["evaluator.classification"] == "complete"
        assert calls["evaluator.action_taken"] == "no_action"
        assert calls["evaluator.success"] is True

    def test_exits_nonzero_when_action_fails(self):
        """Command exits 1 when dispatched action reports failure."""
        with (
            patch("sys.argv", ["agdt-evaluate-post-agent-state", "--pr", "42", "--repo", "o/r"]),
            patch("agentic_devtools.cli.ci.evaluator.command.get_value", return_value=None),
            patch("agentic_devtools.cli.ci.evaluator.command.set_value"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.resolve_github_repo",
                return_value="o/r",
            ),
            patch("agentic_devtools.cli.ci.evaluator.command.GitHubActionsProvider"),
            patch("agentic_devtools.cli.ci.evaluator.command.acquire_lock", return_value="token"),
            patch("agentic_devtools.cli.ci.evaluator.command.release_lock"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.build_snapshot",
                return_value=PostAgentSnapshot(pr_number=42, repo="o/r"),
            ),
            patch("agentic_devtools.cli.ci.evaluator.command.classify_post_agent_state"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.dispatch_action",
                return_value=EvaluationResult(
                    classification=PostAgentClassification.agent_silent,
                    action_taken=PostAgentAction.agentic_fallback,
                    success=False,
                ),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            evaluate_post_agent_state_command()

        assert exc_info.value.code == 1

    def test_release_lock_failure_is_swallowed(self):
        """Release-lock errors are logged and do not fail successful execution."""
        snap = PostAgentSnapshot(pr_number=42, repo="o/r", has_sentinel=True)
        with (
            patch("sys.argv", ["agdt-evaluate-post-agent-state", "--pr", "42", "--repo", "o/r"]),
            patch("agentic_devtools.cli.ci.evaluator.command.get_value", return_value=None),
            patch("agentic_devtools.cli.ci.evaluator.command.set_value"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.resolve_github_repo",
                return_value="o/r",
            ),
            patch("agentic_devtools.cli.ci.evaluator.command.GitHubActionsProvider"),
            patch("agentic_devtools.cli.ci.evaluator.command.acquire_lock", return_value="token"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.release_lock",
                side_effect=RuntimeError("release failed"),
            ),
            patch("agentic_devtools.cli.ci.evaluator.command.build_snapshot", return_value=snap),
        ):
            evaluate_post_agent_state_command()

    def test_repo_resolution_uses_shared_helper(self):
        """Repo resolution delegates to the shared helper."""
        with (
            patch("sys.argv", ["agdt-evaluate-post-agent-state", "--pr", "42"]),
            patch("agentic_devtools.cli.ci.evaluator.command.get_value", return_value=None),
            patch("agentic_devtools.cli.ci.evaluator.command.set_value"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.resolve_github_repo",
                return_value="detected/repo",
            ) as mock_resolve,
            patch("agentic_devtools.cli.ci.evaluator.command.GitHubActionsProvider"),
            patch("agentic_devtools.cli.ci.evaluator.command.acquire_lock", return_value="token"),
            patch("agentic_devtools.cli.ci.evaluator.command.release_lock"),
            patch(
                "agentic_devtools.cli.ci.evaluator.command.build_snapshot",
                return_value=PostAgentSnapshot(pr_number=42, repo="detected/repo", has_sentinel=True),
            ),
        ):
            evaluate_post_agent_state_command()

        mock_resolve.assert_called_once_with(None)
