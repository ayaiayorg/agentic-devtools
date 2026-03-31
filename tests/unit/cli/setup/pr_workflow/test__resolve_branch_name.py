"""Tests for _resolve_branch_name."""

from subprocess import CompletedProcess
from unittest.mock import patch

from agentic_devtools.cli.setup.pr_workflow import _resolve_branch_name


def _ok(stdout: str = "") -> CompletedProcess:
    return CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "") -> CompletedProcess:
    return CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class TestResolveBranchName:
    """Tests for _resolve_branch_name."""

    def test_returns_base_name_when_not_taken(self):
        """Returns chore/agdt-setup-{version} when name is free locally and remotely."""
        with patch("agentic_devtools.cli.setup.pr_workflow.run_git") as mock_git:
            # rev-parse --verify fails (not found locally)
            # ls-remote returns empty (not found remotely)
            mock_git.side_effect = [_fail(), _ok("")]

            result = _resolve_branch_name("1.0.0")

        assert result == "chore/agdt-setup-1.0.0"

    def test_appends_suffix_when_base_taken_locally(self):
        """Appends -2 when the base name exists locally."""
        with patch("agentic_devtools.cli.setup.pr_workflow.run_git") as mock_git:
            mock_git.side_effect = [
                _ok(),  # rev-parse for base name → found locally
                _fail(),  # rev-parse for -2 → not found locally
                _ok(""),  # ls-remote for -2 → not found remotely
            ]

            result = _resolve_branch_name("1.0.0")

        assert result == "chore/agdt-setup-1.0.0-2"

    def test_appends_suffix_when_base_taken_remotely(self):
        """Appends -2 when the base name exists remotely but not locally."""
        with patch("agentic_devtools.cli.setup.pr_workflow.run_git") as mock_git:
            mock_git.side_effect = [
                _fail(),  # rev-parse for base → not local
                _ok("abc123\trefs/heads/x"),  # ls-remote for base → found remotely
                _fail(),  # rev-parse for -2 → not local
                _ok(""),  # ls-remote for -2 → not remote
            ]

            result = _resolve_branch_name("1.0.0")

        assert result == "chore/agdt-setup-1.0.0-2"

    def test_increments_suffix_until_free(self):
        """Increments suffix (-2, -3, …) until a free name is found."""
        with patch("agentic_devtools.cli.setup.pr_workflow.run_git") as mock_git:
            mock_git.side_effect = [
                _ok(),  # base taken locally
                _ok(),  # -2 taken locally
                _fail(),  # -3 not local
                _ok(""),  # -3 not remote
            ]

            result = _resolve_branch_name("2.0.0")

        assert result == "chore/agdt-setup-2.0.0-3"
