"""Tests for run_setup_with_pr_workflow."""

import os
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.setup.pr_workflow import run_setup_with_pr_workflow

_RUN_GIT = "agentic_devtools.cli.setup.pr_workflow.run_git"
_CREATE_PR = "agentic_devtools.cli.azure_devops.commands.create_pull_request"
_SET_VALUE = "agentic_devtools.state.set_value"
_GET_VALUE = "agentic_devtools.state.get_value"


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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
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
                    with patch(_GET_VALUE, return_value=None):
                        result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert result["branch_created"] == "chore/agdt-setup-1.0.0"
        assert result["pr_created"] is True

        # Verify state values were set for PR creation
        mock_set.assert_any_call("source_branch", "chore/agdt-setup-1.0.0")
        mock_set.assert_any_call("title", "chore: agdt-setup v1.0.0")
        mock_set.assert_any_call("draft", "false")

        # Verify prior state values were restored (None when previously unset)
        mock_set.assert_any_call("source_branch", None)
        mock_set.assert_any_call("title", None)
        mock_set.assert_any_call("draft", None)

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

    # ── Idempotency: tree matches origin/main ──────────────────────────

    def test_idempotent_run_skips_branch_when_tree_matches_main(self):
        """When staged tree matches origin/main tree, skip branch creation."""
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
                _ok(),  # add . (idempotency staging)
                _ok("same_tree_hash\n"),  # write-tree
                _ok("same_tree_hash\n"),  # rev-parse origin/main^{tree} (SAME)
                _ok(),  # reset HEAD (unstage)
                _ok(),  # checkout original branch (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] is None
        assert result["pr_created"] is False
        assert "already merged" in result["message"]
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

    def test_stash_push_failure_falls_back_to_normal_setup(self, capsys):
        """When git stash push fails (e.g. during merge/rebase), runs setup without PR workflow."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _fail("cannot stash"),  # stash push FAILS
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert result["branch_created"] is None
        assert result["pr_created"] is False
        assert "Stash failed" in result["message"]

        err = capsys.readouterr().err
        assert "git stash push" in err
        assert "cannot stash" in err

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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
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
                    with patch(_GET_VALUE, return_value=None):
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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
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
                    with patch(_GET_VALUE, return_value=None):
                        result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] == "chore/agdt-setup-1.0.0"
        assert result["pr_created"] is False
        assert "PR creation failed" in result["message"]

        err = capsys.readouterr().err
        assert "PR creation failed" in err

    def test_pr_creation_system_exit_still_restores(self, capsys):
        """SystemExit from create_pull_request() is caught and treated as non-fatal."""
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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
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
                side_effect=SystemExit(1),
            ):
                with patch(_SET_VALUE):
                    with patch(_GET_VALUE, return_value=None):
                        result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] == "chore/agdt-setup-1.0.0"
        assert result["pr_created"] is False
        assert "PR creation failed" in result["message"]

        err = capsys.readouterr().err
        assert "PR creation failed" in err

    def test_pr_creation_restores_prior_state_values(self):
        """State keys are restored to their prior values after PR creation."""
        setup_fn = MagicMock()

        prior_values = {
            "source_branch": "old-branch",
            "title": "old-title",
            "draft": "true",
        }

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                _ok(" M file.txt\n"),  # status --porcelain
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
                _fail(),  # rev-parse --verify → free
                _ok(""),  # ls-remote → free
                _ok(),  # checkout -b
                _ok(),  # add .
                _ok(),  # commit
                _ok(),  # push
                _ok(),  # checkout original (finally)
                _ok(),  # stash pop (finally)
            ]
            with patch(_CREATE_PR):
                with patch(_SET_VALUE) as mock_set:
                    with patch(_GET_VALUE, side_effect=lambda k: prior_values.get(k)):
                        result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["pr_created"] is True

        # The final set_value calls must restore the prior values
        mock_set.assert_any_call("source_branch", "old-branch")
        mock_set.assert_any_call("title", "old-title")
        mock_set.assert_any_call("draft", "true")

    def test_pr_creation_failure_still_restores_state_values(self):
        """State keys are restored even when PR creation raises."""
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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
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
                side_effect=RuntimeError("fail"),
            ):
                with patch(_SET_VALUE) as mock_set:
                    with patch(_GET_VALUE, return_value="existing"):
                        result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["pr_created"] is False

        # Prior values are restored even after failure
        mock_set.assert_any_call("source_branch", "existing")
        mock_set.assert_any_call("title", "existing")
        mock_set.assert_any_call("draft", "existing")

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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
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

        # Verify finally block ran — checkout and stash pop should have been called.
        # No emergency stash was created, so stash pop targets stash@{0}.
        git_calls = [c.args for c in mock_git.call_args_list]
        assert ("checkout", "main") in [c[:2] for c in git_calls]
        assert ("stash", "pop", "stash@{0}") in [c[:3] for c in git_calls]

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
                _ok(""),  # stash list (after) — nothing stashed
                _fail("error"),  # checkout origin/main --detach fails
                _ok(),  # checkout original (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert "Could not checkout origin/main" in result["message"]

        err = capsys.readouterr().err
        assert "Could not checkout origin/main" in err

    def test_checkout_origin_main_failure_pops_stash_before_fallback(self, capsys):
        """When checkout origin/main fails and stash was created, pop before running setup."""
        call_order: list[str] = []
        setup_fn = MagicMock(side_effect=lambda: call_order.append("setup_fn"))

        git_responses = iter(
            [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after) — stash created
                _fail("error"),  # checkout origin/main --detach fails
                _ok(),  # stash pop (early, before setup_fn)
                _ok(),  # checkout original (finally)
            ]
        )

        def _run_git_side_effect(*args, **kwargs):
            if args[:2] == ("stash", "pop"):
                call_order.append("stash_pop")
            return next(git_responses)

        with patch(_RUN_GIT, side_effect=_run_git_side_effect):
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert "Could not checkout origin/main" in result["message"]

        # Verify stash pop was called before setup_fn via combined call order
        assert call_order.index("stash_pop") < call_order.index("setup_fn")

    def test_checkout_origin_main_failure_stash_pop_failure_emits_warning(self, capsys):
        """When stash pop fails in checkout-origin/main fallback, warn and clear did_stash."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after) — stash created
                _fail("error"),  # checkout origin/main --detach fails
                _fail("conflict"),  # stash pop FAILS (conflicts)
                _ok(),  # checkout original (finally) — branch restore succeeds
                # did_stash is now False — no second pop in finally
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        setup_fn.assert_called_once()
        assert result["success"] is True
        assert "Could not checkout origin/main" in result["message"]

        err = capsys.readouterr().err
        # The early-pop warning should appear
        assert "git stash pop" in err
        assert "still be stashed" in err
        # did_stash was cleared, so the finally block should NOT attempt
        # a second stash pop
        assert "Could not auto-restore stashed changes" not in err

    # ── Branch restore failure ─────────────────────────────────────────

    def test_branch_restore_failure_prints_warning(self, capsys):
        """When checkout of original branch fails in finally, tries emergency stash and retry."""
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
                _ok(""),  # stash list (before emergency)
                _fail("cannot stash"),  # emergency stash ALSO fails
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        err = capsys.readouterr().err
        assert "Could not restore branch" in err
        assert "feature/work" in err

    def test_branch_restore_emergency_stash_and_retry_success(self, capsys):
        """When checkout fails but emergency stash + retry succeeds, prints stash warning."""
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
                _fail("dirty tree"),  # checkout original branch FAILS (finally)
                _ok(""),  # stash list (before emergency)
                _ok(),  # emergency stash succeeds
                _ok("stash@{0}\n"),  # stash list (after emergency) — entry created
                _ok(),  # retry checkout succeeds
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        err = capsys.readouterr().err
        assert "Uncommitted setup changes were stashed" in err
        assert "feature/work" in err

    def test_branch_restore_emergency_stash_success_retry_fails(self, capsys):
        """When checkout fails, emergency stash works but retry checkout also fails."""
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
                _fail("dirty tree"),  # checkout original branch FAILS (finally)
                _ok(""),  # stash list (before emergency)
                _ok(),  # emergency stash succeeds
                _ok("stash@{0}\n"),  # stash list (after emergency) — entry created
                _fail("still fails"),  # retry checkout ALSO fails
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        err = capsys.readouterr().err
        assert "even after stashing" in err
        assert "feature/work" in err

    # ── Stash pop uses correct ref after emergency stash ───────────────

    def test_stash_pop_uses_stash_1_after_emergency_stash(self, capsys):
        """When emergency stash was created, stash pop targets stash@{1} (user's original)."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("feature/work\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after) — stash created
                _ok(),  # checkout origin/main --detach
                _ok(""),  # status --porcelain (no changes)
                _fail("dirty tree"),  # checkout original branch FAILS (finally)
                _ok("stash@{0}\n"),  # stash list (before emergency) — 1 entry
                _ok(),  # emergency stash succeeds
                _ok("stash@{0}\nstash@{1}\n"),  # stash list (after emergency) — 2 entries
                _ok(),  # retry checkout succeeds
                _ok(),  # stash pop stash@{1} (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        # Verify stash pop targets stash@{1}
        git_calls = [c.args for c in mock_git.call_args_list]
        assert ("stash", "pop", "stash@{1}") in [c[:3] for c in git_calls]

        err = capsys.readouterr().err
        assert "Uncommitted setup changes were stashed" in err

    def test_stash_pop_uses_stash_0_when_emergency_stash_noop(self, capsys):
        """When emergency stash returns 0 but creates no entry, stash pop targets stash@{0}."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("feature/work\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after) — stash created
                _ok(),  # checkout origin/main --detach
                _ok(""),  # status --porcelain (no changes)
                _fail("dirty tree"),  # checkout original branch FAILS (finally)
                _ok("stash@{0}\n"),  # stash list (before emergency) — 1 entry
                _ok(),  # emergency stash returns 0 (no-op, no changes)
                _ok("stash@{0}\n"),  # stash list (after emergency) — still 1 entry
                _ok(),  # retry checkout succeeds
                _ok(),  # stash pop stash@{0} (finally) — no offset needed
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        # Verify stash pop targets stash@{0} (not stash@{1})
        git_calls = [c.args for c in mock_git.call_args_list]
        assert ("stash", "pop", "stash@{0}") in [c[:3] for c in git_calls]
        # stash@{1} should NOT appear
        assert ("stash", "pop", "stash@{1}") not in [c[:3] for c in git_calls]

        # No misleading "were stashed" warning when emergency stash was a no-op
        err = capsys.readouterr().err
        assert "Uncommitted setup changes were stashed" not in err

    def test_emergency_stash_noop_retry_fails_prints_generic_warning(self, capsys):
        """When emergency stash is a no-op and retry also fails, prints generic warning."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("feature/work\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after) — stash created
                _ok(),  # checkout origin/main --detach
                _ok(""),  # status --porcelain (no changes)
                _fail("dirty tree"),  # checkout original branch FAILS (finally)
                _ok("stash@{0}\n"),  # stash list (before emergency) — 1 entry
                _ok(),  # emergency stash returns 0 (no-op)
                _ok("stash@{0}\n"),  # stash list (after emergency) — still 1 entry
                _fail("still fails"),  # retry checkout ALSO fails
                # NO stash pop — branch restore failed
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        err = capsys.readouterr().err
        # Generic warning (not "even after stashing" since nothing was stashed)
        assert "Could not restore branch 'feature/work'" in err
        assert "even after stashing" not in err
        assert "Skipping stash pop" in err

    def test_skips_stash_pop_when_branch_restore_fails(self, capsys):
        """When branch restore fails completely, stash pop is skipped to avoid wrong branch."""
        setup_fn = MagicMock()

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("feature/work\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after) — stash created
                _ok(),  # checkout origin/main --detach
                _ok(""),  # status --porcelain (no changes)
                _fail("dirty tree"),  # checkout original branch FAILS (finally)
                _ok("stash@{0}\n"),  # stash list (before emergency) — 1 entry
                _ok(),  # emergency stash succeeds
                _ok("stash@{0}\nstash@{1}\n"),  # stash list (after emergency) — 2 entries
                _fail("still fails"),  # retry checkout ALSO fails
                # NO stash pop — skipped because branch restore failed
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        # Verify NO stash pop was attempted
        git_calls = [c.args for c in mock_git.call_args_list]
        stash_pop_calls = [c for c in git_calls if len(c) >= 2 and c[:2] == ("stash", "pop")]
        assert len(stash_pop_calls) == 0

        err = capsys.readouterr().err
        assert "Skipping stash pop because the original branch could not be restored" in err
        assert "git stash list" in err

    # ── Checkout -b failure ────────────────────────────────────────────

    def test_checkout_b_failure_does_not_terminate(self, capsys):
        """checkout -b failure prints error and continues to restore."""
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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
                _fail(),  # rev-parse --verify → free
                _ok(""),  # ls-remote → free
                _fail("already exists"),  # checkout -b FAILS
                _ok(),  # checkout original (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] is None
        assert result["pr_created"] is False
        assert "Failed to create branch" in result["message"]

        err = capsys.readouterr().err
        assert "Could not create branch" in err

    # ── git add failure ────────────────────────────────────────────────

    def test_git_add_failure_does_not_terminate(self, capsys):
        """git add failure prints error and continues to restore."""
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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
                _fail(),  # rev-parse --verify → free
                _ok(""),  # ls-remote → free
                _ok(),  # checkout -b
                _fail("permission denied"),  # add . FAILS
                _ok(),  # checkout original (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] is None
        assert "Failed to stage" in result["message"]

        err = capsys.readouterr().err
        assert "git add" in err

    # ── git commit failure ─────────────────────────────────────────────

    def test_git_commit_failure_does_not_terminate(self, capsys):
        """git commit failure prints error and continues to restore."""
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
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
                _fail(),  # rev-parse --verify → free
                _ok(""),  # ls-remote → free
                _ok(),  # checkout -b
                _ok(),  # add .
                _fail("nothing to commit"),  # commit FAILS
                _ok(),  # checkout original (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] is None
        assert "Failed to commit" in result["message"]

        err = capsys.readouterr().err
        assert "git commit" in err

    # ── Idempotency add failure ────────────────────────────────────────

    def test_idempotency_add_failure_falls_through_to_branch_flow(self, capsys):
        """When the idempotency 'git add .' fails, skip the tree comparison and proceed to branch creation."""
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
                _fail("permission denied"),  # add . (idempotency probe FAILS)
                _ok(),  # reset HEAD (always called after probe)
                _fail(),  # rev-parse --verify → branch free
                _ok(""),  # ls-remote → branch free
                _ok(),  # checkout -b branch
                _fail("permission denied"),  # add . (branch flow also fails)
                _ok(),  # checkout original (finally)
            ]
            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

        assert result["success"] is True
        assert result["branch_created"] is None
        assert result["pr_created"] is False
        # Must NOT report "already merged"; must have fallen through to branch flow
        assert "already merged" not in result["message"]
        assert "Failed to stage" in result["message"]

        err = capsys.readouterr().err
        assert "git add" in err

    # ── SSL env var propagation ────────────────────────────────────────

    def test_no_verify_ssl_sets_azure_cli_env_var_during_pr_creation(self):
        """AGDT_NO_VERIFY_SSL=1 sets AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1 during create_pull_request()."""
        setup_fn = MagicMock()
        captured: dict[str, str | None] = {}

        def _capture_env():
            captured["during"] = os.environ.get("AZURE_CLI_DISABLE_CONNECTION_VERIFICATION")

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                _ok(" M some-file.txt\n"),  # status --porcelain (has changes)
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
                _fail(),  # rev-parse --verify (branch free)
                _ok(""),  # ls-remote (branch free)
                _ok(),  # checkout -b branch
                _ok(),  # add .
                _ok(),  # commit
                _ok(),  # push
                _ok(),  # checkout original branch (finally)
                _ok(),  # stash pop (finally)
            ]
            # Ensure AZURE_CLI_DISABLE_CONNECTION_VERIFICATION is absent before the run,
            # and AGDT_NO_VERIFY_SSL is set.
            clean_env = {
                k: v
                for k, v in os.environ.items()
                if k != "AZURE_CLI_DISABLE_CONNECTION_VERIFICATION"
            }
            clean_env["AGDT_NO_VERIFY_SSL"] = "1"
            with patch.dict(os.environ, clean_env, clear=True):
                with patch(_CREATE_PR, side_effect=_capture_env):
                    with patch(_SET_VALUE):
                        with patch(_GET_VALUE, return_value=None):
                            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

                # After the call, the var must be restored (removed since it was absent).
                assert "AZURE_CLI_DISABLE_CONNECTION_VERIFICATION" not in os.environ

        assert result["pr_created"] is True
        assert captured.get("during") == "1"

    def test_no_verify_ssl_restores_prior_azure_cli_env_var(self):
        """AZURE_CLI_DISABLE_CONNECTION_VERIFICATION is restored to its prior value after PR creation."""
        setup_fn = MagicMock()
        captured: dict[str, str | None] = {}

        def _capture_env():
            captured["during"] = os.environ.get("AZURE_CLI_DISABLE_CONNECTION_VERIFICATION")

        with patch(_RUN_GIT) as mock_git:
            mock_git.side_effect = [
                _ok(),  # fetch origin main
                _ok("main\n"),  # rev-parse --abbrev-ref HEAD
                _ok(""),  # stash list (before)
                _ok(),  # stash push
                _ok("stash@{0}\n"),  # stash list (after)
                _ok(),  # checkout origin/main --detach
                _ok(" M some-file.txt\n"),  # status --porcelain (has changes)
                _ok(),  # add . (idempotency staging)
                _ok("aaa111\n"),  # write-tree
                _ok("bbb222\n"),  # rev-parse origin/main^{tree} (different)
                _ok(),  # reset HEAD (unstage)
                _fail(),  # rev-parse --verify (branch free)
                _ok(""),  # ls-remote (branch free)
                _ok(),  # checkout -b branch
                _ok(),  # add .
                _ok(),  # commit
                _ok(),  # push
                _ok(),  # checkout original branch (finally)
                _ok(),  # stash pop (finally)
            ]
            env_overrides = {
                "AGDT_NO_VERIFY_SSL": "1",
                "AZURE_CLI_DISABLE_CONNECTION_VERIFICATION": "existing-value",
            }
            with patch.dict(os.environ, env_overrides):
                with patch(_CREATE_PR, side_effect=_capture_env):
                    with patch(_SET_VALUE):
                        with patch(_GET_VALUE, return_value=None):
                            result = run_setup_with_pr_workflow(setup_fn, "1.0.0")

                # Prior value must be restored after the call.
                assert os.environ.get("AZURE_CLI_DISABLE_CONNECTION_VERIFICATION") == "existing-value"

        assert result["pr_created"] is True
        # The var was already set to "existing-value"; AGDT_NO_VERIFY_SSL overwrites it to "1".
        assert captured.get("during") == "1"
