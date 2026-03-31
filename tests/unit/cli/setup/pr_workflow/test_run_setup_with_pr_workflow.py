"""Tests for run_setup_with_pr_workflow."""

from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.setup.pr_workflow import run_setup_with_pr_workflow

_RUN_GIT = "agentic_devtools.cli.setup.pr_workflow.run_git"
_CREATE_PR = "agentic_devtools.cli.azure_devops.commands.create_pull_request"
_SET_VALUE = "agentic_devtools.state.set_value"


def _ok(stdout: str = "") -> CompletedProcess:
    return CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "") -> CompletedProcess:
    return CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class TestRunSetupWithPrWorkflow:
    """Tests for run_setup_with_pr_workflow."""

    # ── Happy path: changes detected → branch → commit → PR → restore ─

    def test_happy_path_creates_branch_and_pr(self):
        """Full flow: changes detected → branch → commit → push → PR → restore."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("feature/my-branch\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                _ok(" M some-file.txt\n"),  # status --porcelain (has changes)
                _fail(),  # rev-parse --verify (branch not taken locally)
                _ok(""),  # ls-remote (branch not taken remotely)
                _ok(),  # checkout -b branch
                _ok(),  # add .
                _ok(),  # commit
                _ok(),  # push
                _ok(),  # checkout original branch (finally)
                _ok(),  # stash pop (finally)
            ]
            with patch(_CREATE_PR):
                with patch(_SET_VALUE) as mock_set:
                    result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert result["branch_created"] == "chore/agdt-setup-1.0.0"
        assert result["pr_created"] is True

        # Verify state values were set for PR creation
        mock_set.assert_any_call("source_branch", "chore/agdt-setup-1.0.0")
        mock_set.assert_any_call("title", "chore: agdt-setup v1.0.0")
        mock_set.assert_any_call("draft", "false")

    # ── No changes path ────────────────────────────────────────────────

    def test_no_changes_skips_branch_and_pr(self):
        """No file changes → skip branch/commit/push/PR, still restore."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok(""),  # stash list (after) — nothing stashed
                _ok(),  # checkout origin/main --detach
                _ok(""),  # status --porcelain (no changes)
                _ok(),  # checkout original branch (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] is None
        assert result["pr_created"] is False
        assert "No file changes" in result["message"]
        setup_fn.assert_called_once()

    # ── Fetch failure → fallback ───────────────────────────────────────

    def test_fetch_failure_falls_back_to_normal_setup(self, capsys):
        """When git fetch fails, runs setup directly without PR workflow."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.return_value = _fail("network error")

            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert result["branch_created"] is None
        assert result["pr_created"] is False
        assert "Fetch failed" in result["message"]

        err = capsys.readouterr().err
        assert "git fetch origin main" in err

    # ── Detached HEAD → fallback ───────────────────────────────────────

    def test_detached_head_falls_back_to_normal_setup(self, capsys):
        """When already on detached HEAD, runs setup directly."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("HEAD\n"),  # rev-parse --abbrev-ref HEAD → detached
            ]

            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert result["branch_created"] is None
        assert "Detached HEAD" in result["message"]

        err = capsys.readouterr().err
        assert "Detached HEAD" in err

    # ── Stash pop failure ──────────────────────────────────────────────

    def test_stash_pop_failure_prints_warning(self, capsys):
        """Stash pop failure prints warning but does not raise."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after) — stash created
                _ok(),  # checkout origin/main --detach
                _ok(""),  # status --porcelain (no changes)
                _ok(),  # checkout original branch (finally)
                _fail("conflict"),  # stash pop fails (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        err = capsys.readouterr().err
        assert "Could not auto-restore stashed changes" in err
        assert "git stash list" in err

    # ── Branch name collision ──────────────────────────────────────────

    def test_branch_name_collision_uses_suffix(self):
        """When base branch name exists, uses -2 suffix."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok(""),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                _ok(" M file.txt\n"),  # status --porcelain (has changes)
                _ok(),  # rev-parse --verify base → taken
                _fail(),  # rev-parse --verify -2 → free
                _ok(""),  # ls-remote -2 → free
                _ok(),  # checkout -b branch-2
                _ok(),  # add .
                _ok(),  # commit
                _ok(),  # push
                _ok(),  # checkout original (finally)
            ]
            with patch(_CREATE_PR):
                with patch(_SET_VALUE):
                    result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["branch_created"] == "chore/agdt-setup-1.0.0-2"

    # ── PR creation failure ────────────────────────────────────────────

    def test_pr_creation_failure_still_restores(self, capsys):
        """PR creation failure → warning, branch still exists, restore happens."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                _ok(" M file.txt\n"),  # status --porcelain
                _fail(),  # rev-parse --verify → free
                _ok(""),  # ls-remote → free
                _ok(),  # checkout -b
                _ok(),  # add .
                _ok(),  # commit
                _ok(),  # push
                _ok(),  # checkout original (finally)
                _ok(),  # stash pop (finally)
            ]
            with patch(
                _CREATE_PR,
                side_effect=RuntimeError("Azure DevOps unavailable"),
            ):
                with patch(_SET_VALUE):
                    result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] == "chore/agdt-setup-1.0.0"
        assert result["pr_created"] is False
        assert "PR creation failed" in result["message"]

        err = capsys.readouterr().err
        assert "PR creation failed" in err

    # ── Push failure ───────────────────────────────────────────────────

    def test_push_failure_still_restores(self, capsys):
        """Push failure prints error, still restores branch and stash."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                _ok(" M file.txt\n"),  # status --porcelain
                _fail(),  # rev-parse --verify → free
                _ok(""),  # ls-remote → free
                _ok(),  # checkout -b
                _ok(),  # add .
                _ok(),  # commit
                _fail("auth error"),  # push fails
                _ok(),  # checkout original (finally)
                _ok(),  # stash pop (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] == "chore/agdt-setup-1.0.0"
        assert result["pr_created"] is False
        assert "push failed" in result["message"]

        err = capsys.readouterr().err
        assert "Failed to push branch" in err

    # ── Setup function raises ──────────────────────────────────────────

    def test_setup_fn_exception_restores_and_reraises(self):
        """When setup_fn raises, finally block restores branch and stash, then re-raises."""
        setup_fn = MagicMock(side_effect=RuntimeError("setup boom"))

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                # setup_fn raises here — skip status/branch/commit/push
                _ok(),  # checkout original (finally)
                _ok(),  # stash pop (finally)
            ]
            with pytest.raises(RuntimeError, match="setup boom"):
                run_setup_with_pr_workflow(setup_fn, "1.0.0")

        # Verify finally block ran — checkout and stash pop should have been called
        git_calls = [c.args for c in mock_git.call_args_list]
        # The last two calls should be checkout original and stash pop
        assert ("checkout", "main") in [c[:2] for c in git_calls]
        assert ("stash", "pop") in [c[:2] for c in git_calls]

    # ── Checkout origin/main failure ───────────────────────────────────

    def test_checkout_origin_main_failure_falls_back(self, capsys):
        """When checkout origin/main fails, setup runs on current branch."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok(""),  # stash list (after)
                _fail("error"),  # checkout origin/main --detach fails
                _ok(),  # checkout original (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert "Could not checkout origin/main" in result["message"]

        err = capsys.readouterr().err
        assert "Could not checkout origin/main" in err

    # ── Branch restore failure ─────────────────────────────────────────

    def test_branch_restore_failure_prints_warning(self, capsys):
        """When checkout of original branch fails in finally, prints warning."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("feature/work\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok(""),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                _ok(""),  # status --porcelain (no changes)
                _fail("error: pathspec"),  # checkout original branch FAILS (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        err = capsys.readouterr().err
        assert "Could not restore branch" in err
        assert "feature/work" in err
