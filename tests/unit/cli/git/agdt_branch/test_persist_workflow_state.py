"""Tests for agentic_devtools.cli.git.agdt_branch.persist_workflow_state."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.agdt_branch import (
    GitPlumbingError,
    persist_workflow_state,
)

# Patch target prefix
_MOD = "agentic_devtools.cli.git.agdt_branch"


def _ok(stdout="", stderr=""):
    return MagicMock(returncode=0, stdout=stdout, stderr=stderr)


def _fail(stderr="error", stdout=""):
    return MagicMock(returncode=1, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
#  Validation
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateValidation:
    """Validation and defaults tests."""

    def test_worktree_key_none_returns_failure(self):
        """worktree_key=None must return PersistResult(success=False)."""
        result = persist_workflow_state("feature/x", worktree_key=None)
        assert result.success is False
        assert "worktree_key is required" in result.error

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="ccc111")
    @patch(f"{_MOD}.build_tree", return_value="ttt111")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(f"{_MOD}._discover_workflow_files", return_value={"f": "sha"})
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_identity_defaults_to_default(
        self,
        mock_root,
        mock_discover,
        _loc,
        _rem,
        _read,
        _build,
        _commit,
        _update,
        _push,
        _get_val,
    ):
        """When identity=None, the discovery path must use 'default'."""
        persist_workflow_state(
            "feat",
            worktree_key="KEY",
            identity=None,
        )
        mock_discover.assert_called_once_with(Path("/repo"), "default", "KEY")

    def test_double_suffix_prevention(self):
        """source_branch ending with -agdt must not be double-suffixed."""
        # Even though there are no files, the branch_name in the result
        # should show the prevention.
        with patch(f"{_MOD}._get_repo_root", return_value=Path("/r")):
            with patch(f"{_MOD}._discover_workflow_files", return_value={}):
                result = persist_workflow_state("feat-agdt", worktree_key="K")
        assert result.branch_name == "feat-agdt"
        # And a non -agdt source should append the suffix.
        with patch(f"{_MOD}._get_repo_root", return_value=Path("/r")):
            with patch(f"{_MOD}._discover_workflow_files", return_value={}):
                result = persist_workflow_state("feat", worktree_key="K")
        assert result.branch_name == "feat-agdt"


# ---------------------------------------------------------------------------
#  New branch creation
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateNewBranch:
    """Tests for creating a brand-new -agdt branch."""

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.push_branch")
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="commit_aaa")
    @patch(f"{_MOD}.build_tree", return_value="tree_aaa")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=False)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={".agdt/workflows/default/K/f.json": "blobsha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_new_branch_creation_from_source(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _build,
        mock_commit,
        mock_update,
        mock_push,
        _get_val,
    ):
        """New branch: commit with source HEAD as parent, push called."""
        # _run_plumbing is called for rev-parse of source_branch
        mock_plumbing.return_value = _ok(stdout="source_head_sha\n")
        mock_push.return_value = _ok()

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is True
        assert result.branch_name == "feat-agdt"
        assert result.commit_hash == "commit_aaa"
        # create_commit should receive source HEAD as parent
        mock_commit.assert_called_once()
        call_args = mock_commit.call_args
        assert call_args[0][1] == "source_head_sha"  # parent_sha

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="ccc")
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}.read_branch_tree", return_value={"old": "sha"})
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=True)
    @patch(f"{_MOD}._branch_exists_locally", return_value=False)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_new_branch_from_remote(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _read,
        _build,
        _commit,
        _update,
        _push,
        _get_val,
    ):
        """Remote exists, local doesn't: fetch first then proceed."""
        # _run_plumbing calls: fetch, rev-parse target_branch
        mock_plumbing.return_value = _ok(stdout="head_sha\n")

        result = persist_workflow_state("feat", worktree_key="K")
        assert result.success is True

        # Verify fetch was called (first _run_plumbing call)
        first_call_args = mock_plumbing.call_args_list[0][0]
        assert "fetch" in first_call_args


# ---------------------------------------------------------------------------
#  Amend vs new commit
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateAmend:
    """Tests for amend (matching Run-Id) vs new-commit behaviour."""

    @patch(f"{_MOD}.get_value", return_value="abc123")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}.push_branch")
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="new_commit")
    @patch(f"{_MOD}.build_tree", return_value="tree_sha")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._has_matching_run_id", return_value=True)
    @patch(f"{_MOD}._get_parent_sha", return_value="grandparent")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_amend_when_run_id_matches(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_parent,
        mock_match,
        _read,
        _build,
        mock_commit,
        _update,
        _push,
        mock_plumbing,
        _get_val,
    ):
        """Matching Run-Id: parent = HEAD's parent, force-with-lease push."""
        # _run_plumbing: rev-parse target_branch → head SHA
        mock_plumbing.return_value = _ok(stdout="head_sha\n")
        # push via _run_plumbing (force-with-lease path)
        # The last _run_plumbing call is the push itself

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is True
        # create_commit called with grandparent as parent (amend)
        mock_commit.assert_called_once()
        assert mock_commit.call_args[0][1] == "grandparent"
        # Push should use --force-with-lease (via _run_plumbing, not push_branch)
        force_calls = [c for c in mock_plumbing.call_args_list if "--force-with-lease" in c[0]]
        assert len(force_calls) >= 1

    @patch(f"{_MOD}.get_value", return_value="new_id")
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="new_commit")
    @patch(f"{_MOD}.build_tree", return_value="tree_sha")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._has_matching_run_id", return_value=False)
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_new_commit_when_run_id_differs(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _match,
        _read,
        _build,
        mock_commit,
        _update,
        mock_push,
        _get_val,
    ):
        """Different Run-Id: parent = HEAD, normal push."""
        mock_plumbing.return_value = _ok(stdout="head_sha\n")

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is True
        # Parent should be HEAD itself (not HEAD's parent)
        mock_commit.assert_called_once()
        assert mock_commit.call_args[0][1] == "head_sha"
        # push_branch (normal) should be used
        mock_push.assert_called_once()

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="new_commit")
    @patch(f"{_MOD}.build_tree", return_value="tree_sha")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_new_commit_when_no_run_id_in_state(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _read,
        _build,
        mock_commit,
        _update,
        mock_push,
        _get_val,
    ):
        """No agdt_run_id in state: no trailer, new commit on top of HEAD."""
        mock_plumbing.return_value = _ok(stdout="head_sha\n")

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is True
        # No Run-Id trailer in commit message
        msg = mock_commit.call_args[0][2]
        assert "Run-Id:" not in msg


# ---------------------------------------------------------------------------
#  Push retry
# ---------------------------------------------------------------------------


class TestPersistWorkflowStatePushRetry:
    """Tests for push rejection and retry logic."""

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="commit_sha")
    @patch(f"{_MOD}.build_tree", return_value="tree_sha")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._read_tree_for_commit", return_value={})
    @patch(f"{_MOD}.push_branch")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_push_retry_on_rejection(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        mock_push,
        _read_commit_tree,
        _read,
        _build,
        mock_commit,
        _update,
        _get_val,
    ):
        """First push fails, second succeeds after fetch + rebase."""
        mock_plumbing.return_value = _ok(stdout="head_sha\n")
        mock_push.side_effect = [
            _fail(stderr="rejected"),  # first push fails
            _ok(),  # second push succeeds
        ]

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is True
        assert mock_push.call_count == 2

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="commit_sha")
    @patch(f"{_MOD}.build_tree", return_value="tree_sha")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._read_tree_for_commit", return_value={})
    @patch(f"{_MOD}.push_branch")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_push_fails_after_3_attempts(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        mock_push,
        _read_commit_tree,
        _read,
        _build,
        _commit,
        _update,
        _get_val,
    ):
        """All 3 pushes fail → PersistResult(success=False)."""
        mock_plumbing.return_value = _ok(stdout="head_sha\n")
        mock_push.return_value = _fail(stderr="rejected")

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is False
        assert "Push failed after 3 attempts" in result.error


# ---------------------------------------------------------------------------
#  File discovery
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateFileDiscovery:
    """Tests for file discovery edge cases."""

    @patch(f"{_MOD}._get_repo_root")
    def test_no_files_returns_failure(self, mock_root, tmp_path):
        """No files under .agdt/workflows/ returns failure."""
        mock_root.return_value = tmp_path
        result = persist_workflow_state("feat", worktree_key="K")
        assert result.success is False
        assert "No workflow files found" in result.error

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="ccc")
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(f"{_MOD}.hash_object", return_value="blob_aaa")
    @patch(f"{_MOD}._get_repo_root")
    def test_files_discovered_and_hashed(
        self,
        mock_root,
        mock_hash,
        _loc,
        _rem,
        mock_plumbing,
        _read,
        mock_build,
        _commit,
        _update,
        _push,
        _get_val,
        tmp_path,
    ):
        """Files under .agdt/workflows/default/K/ are discovered and hashed."""
        mock_root.return_value = tmp_path
        mock_plumbing.return_value = _ok(stdout="head\n")

        # Create workflow files on disk
        wf_dir = tmp_path / ".agdt" / "workflows" / "default" / "K"
        wf_dir.mkdir(parents=True)
        (wf_dir / "state.json").write_text("{}")
        (wf_dir / "review.json").write_text("{}")

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is True
        # build_tree must receive the correct path→sha dict
        build_call_entries = mock_build.call_args[0][0]
        expected_paths = {
            ".agdt/workflows/default/K/review.json",
            ".agdt/workflows/default/K/state.json",
        }
        assert set(build_call_entries.keys()) == expected_paths
        for v in build_call_entries.values():
            assert v == "blob_aaa"


# ---------------------------------------------------------------------------
#  Error handling
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateErrorHandling:
    """Tests for error paths and safety guarantees."""

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    @patch(
        f"{_MOD}.build_tree",
        side_effect=GitPlumbingError("tree failed"),
    )
    def test_git_plumbing_error_returns_failure(
        self,
        _build,
        _root,
        _discover,
        _loc,
        _rem,
        _read,
        _get_val,
    ):
        """GitPlumbingError is caught and returned as PersistResult."""
        result = persist_workflow_state("feat", worktree_key="K")
        assert result.success is False
        assert "tree failed" in result.error

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="ccc")
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_never_calls_sys_exit(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _read,
        _build,
        _commit,
        _update,
        _push,
        _get_val,
    ):
        """sys.exit is never called during persist."""
        mock_plumbing.return_value = _ok(stdout="sha\n")
        with patch.object(sys, "exit", side_effect=AssertionError("sys.exit called")) as mock_exit:
            result = persist_workflow_state("feat", worktree_key="K")
            mock_exit.assert_not_called()
        assert result.success is True

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit")
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_commit_message_auto_generated(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _read,
        _build,
        mock_commit,
        _update,
        _push,
        _get_val,
    ):
        """Empty commit_message auto-generates with workflow_type and worktree_key."""
        mock_plumbing.return_value = _ok(stdout="sha\n")
        mock_commit.return_value = "ccc"

        persist_workflow_state(
            "feat",
            worktree_key="DFLY-1234",
            workflow_type="review",
            commit_message="",
        )

        msg = mock_commit.call_args[0][2]
        assert "agdt: persist review state for DFLY-1234" in msg

    @patch(f"{_MOD}.get_value", return_value="abc123")
    @patch(f"{_MOD}._has_matching_run_id", return_value=False)
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="ccc")
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_run_id_trailer_appended(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _read,
        _build,
        mock_commit,
        _update,
        _push,
        _match,
        _get_val,
    ):
        """When agdt_run_id is set, Run-Id trailer is appended."""
        mock_plumbing.return_value = _ok(stdout="sha\n")

        persist_workflow_state("feat", worktree_key="K")

        msg = mock_commit.call_args[0][2]
        assert msg.endswith("\n\nRun-Id: abc123")

    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(
        f"{_MOD}.build_tree",
        side_effect=RuntimeError("unexpected"),
    )
    def test_generic_exception_returns_failure(
        self,
        _build,
        _read,
        _rem,
        _loc,
        _discover,
        _root,
    ):
        """A non-GitPlumbingError exception is caught and returned as PersistResult."""
        result = persist_workflow_state("feat", worktree_key="K")
        assert result.success is False
        assert "unexpected" in result.error


# ---------------------------------------------------------------------------
#  Fetch failure
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateFetchFailure:
    """Tests for fetch error handling."""

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=True)
    @patch(f"{_MOD}._branch_exists_locally", return_value=False)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_fetch_failure_returns_error(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _get_val,
    ):
        """If fetching the remote branch fails, return PersistResult with error."""
        mock_plumbing.return_value = _fail(stderr="auth failed")

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is False
        assert "fetch origin" in result.error


# ---------------------------------------------------------------------------
#  Stale artifact filtering
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateStaleArtifacts:
    """Tests for snapshot semantics (stale file removal)."""

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.push_branch", return_value=_ok())
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="ccc")
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}.read_branch_tree")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_stale_files_removed_from_tree(
        self,
        _root,
        _loc,
        _rem,
        mock_plumbing,
        mock_read_tree,
        mock_build,
        _commit,
        _update,
        _push,
        _get_val,
    ):
        """Deleted workflow files are removed from the tree (snapshot semantics)."""
        mock_plumbing.return_value = _ok(stdout="sha\n")
        # Existing tree has two files in the workflow dir plus one outside.
        mock_read_tree.return_value = {
            ".agdt/workflows/default/K/old.json": "old_sha",
            ".agdt/workflows/default/K/kept.json": "kept_sha",
            "README.md": "readme_sha",
        }

        # Discovery only finds kept.json (old.json was deleted on disk).
        updates = {".agdt/workflows/default/K/kept.json": "new_sha"}
        with patch(
            f"{_MOD}._discover_workflow_files",
            return_value=updates,
        ):
            result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is True
        # build_tree should receive: kept.json (updated), README.md (preserved),
        # but NOT old.json (stale — removed).
        built = mock_build.call_args[0][0]
        assert "README.md" in built
        assert ".agdt/workflows/default/K/kept.json" in built
        assert ".agdt/workflows/default/K/old.json" not in built


# ---------------------------------------------------------------------------
#  Push retry edge cases
# ---------------------------------------------------------------------------


class TestPersistWorkflowStatePushRetryEdgeCases:
    """Tests for push retry edge cases."""

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="commit_sha")
    @patch(f"{_MOD}.build_tree", return_value="tree_sha")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._read_tree_for_commit", return_value={})
    @patch(f"{_MOD}.push_branch")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_retry_skips_when_remote_head_unresolvable(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        mock_push,
        _read_commit_tree,
        _read,
        _build,
        _commit,
        _update,
        _get_val,
    ):
        """When remote HEAD can't be resolved, retry continues to next attempt."""
        # First _run_plumbing: rev-parse target_branch (for parent detection)
        # Subsequent: fetch ok, rev-parse origin/target FAIL, then repeat
        call_count = [0]
        rev_parse_origin_fail = _fail(stderr="not found")

        def plumbing_side_effect(*args, **kwargs):
            call_count[0] += 1
            if "origin/" in str(args):
                return rev_parse_origin_fail
            return _ok(stdout="head_sha\n")

        mock_plumbing.side_effect = plumbing_side_effect
        mock_push.return_value = _fail(stderr="rejected")

        result = persist_workflow_state("feat", worktree_key="K")
        assert result.success is False
        assert "Push failed after 3 attempts" in result.error

    @patch(f"{_MOD}.get_value", return_value="run123")
    @patch(f"{_MOD}.update_ref")
    @patch(f"{_MOD}.create_commit", return_value="commit_sha")
    @patch(f"{_MOD}.build_tree", return_value="tree_sha")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._read_tree_for_commit", return_value={})
    @patch(f"{_MOD}._has_matching_run_id", return_value=True)
    @patch(f"{_MOD}._get_parent_sha", return_value="grandparent")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_amend_retry_uses_remote_parent(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _parent,
        _match,
        _read_commit_tree,
        _read,
        _build,
        mock_commit,
        _update,
        _get_val,
    ):
        """Amend retry uses _get_parent_sha(remote_head) as parent."""
        push_calls = [0]

        def plumbing_side_effect(*args, **kwargs):
            if "--force-with-lease" in args:
                push_calls[0] += 1
                if push_calls[0] == 1:
                    return _fail(stderr="rejected")
                return _ok()
            return _ok(stdout="remote_head_sha\n")

        mock_plumbing.side_effect = plumbing_side_effect

        result = persist_workflow_state("feat", worktree_key="K")
        assert result.success is True


# ---------------------------------------------------------------------------
#  Source/target branch resolution failures
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateBranchResolution:
    """Tests for hard failure when source/target branches are unresolvable."""

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=False)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_source_branch_revparse_failure_returns_error(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _build,
        _get_val,
    ):
        """When source branch rev-parse fails, return PersistResult(success=False)."""
        mock_plumbing.return_value = _fail(stderr="unknown revision")

        result = persist_workflow_state("nonexistent", worktree_key="K")

        assert result.success is False
        assert "Failed to resolve source branch HEAD" in result.error
        assert "nonexistent" in result.error

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=False)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_source_branch_empty_sha_returns_error(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _build,
        _get_val,
    ):
        """When source branch rev-parse succeeds but returns empty output."""
        mock_plumbing.return_value = _ok(stdout="")

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is False
        assert "has no HEAD commit" in result.error

    @patch(f"{_MOD}.get_value", return_value=None)
    @patch(f"{_MOD}.build_tree", return_value="ttt")
    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._run_plumbing")
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(
        f"{_MOD}._discover_workflow_files",
        return_value={"f": "sha"},
    )
    @patch(f"{_MOD}._get_repo_root", return_value=Path("/repo"))
    def test_target_branch_revparse_failure_returns_error(
        self,
        _root,
        _discover,
        _loc,
        _rem,
        mock_plumbing,
        _read,
        _build,
        _get_val,
    ):
        """When existing target branch rev-parse fails, return error."""
        mock_plumbing.return_value = _fail(stderr="corrupt ref")

        result = persist_workflow_state("feat", worktree_key="K")

        assert result.success is False
        assert "Failed to resolve existing target branch" in result.error
