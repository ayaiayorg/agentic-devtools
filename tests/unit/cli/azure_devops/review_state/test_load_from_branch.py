"""Tests for _load_from_branch helper function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.review_state import _load_from_branch

_AGDT_MOD = "agentic_devtools.cli.git.agdt_branch"
_STATE_MOD = "agentic_devtools.state"


class TestLoadFromBranch:
    """Tests for _load_from_branch function."""

    def test_returns_none_when_no_source_branch(self):
        """Returns None when source_branch is None and state has no branch."""
        with patch(f"{_STATE_MOD}.get_value", return_value=None):
            result = _load_from_branch(None, None)
        assert result is None

    def test_returns_none_when_no_worktree_key(self):
        """Returns None when worktree_key is None and resolve raises ValueError."""
        with patch(f"{_STATE_MOD}.get_value", return_value="main"):
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", side_effect=ValueError("Cannot resolve")):
                result = _load_from_branch(None, None)
        assert result is None

    def test_returns_parsed_dict_on_success(self):
        """Returns the parsed dict when artifacts contain review-state.json."""
        artifacts = {
            ".agdt/workflows/default/KEY/reviews/review-state.json": {
                "prId": 42,
                "repoId": "r",
                "repoName": "repo",
                "project": "P",
                "organization": "O",
                "latestIterationId": 1,
                "scaffoldedUtc": "2026-01-01T00:00:00Z",
                "overallSummary": {"threadId": 1, "commentId": 1, "status": "unreviewed"},
                "commitHash": "abc123",
            }
        }
        with patch(f"{_STATE_MOD}.get_value", return_value="main"):
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", return_value="KEY"):
                with patch(f"{_AGDT_MOD}.load_workflow_artifacts", return_value=artifacts):
                    result = _load_from_branch(None, None)
        assert result is not None
        assert result["prId"] == 42

    def test_returns_none_when_artifacts_none(self):
        """Returns None when load_workflow_artifacts returns None."""
        with patch(f"{_STATE_MOD}.get_value", return_value="main"):
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", return_value="KEY"):
                with patch(f"{_AGDT_MOD}.load_workflow_artifacts", return_value=None):
                    result = _load_from_branch("main", "KEY")
        assert result is None

    def test_returns_none_on_import_error(self):
        """Returns None when agdt_branch import fails."""
        import builtins

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if "agdt_branch" in name:
                raise ImportError("simulated")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=failing_import):
            result = _load_from_branch("main", "KEY")
        assert result is None

    def test_returns_none_on_git_plumbing_error(self):
        """Returns None when load_workflow_artifacts raises GitPlumbingError."""
        from agentic_devtools.cli.git.agdt_branch import GitPlumbingError

        with patch(f"{_STATE_MOD}.get_value", return_value="main"):
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", return_value="KEY"):
                with patch(
                    f"{_AGDT_MOD}.load_workflow_artifacts",
                    side_effect=GitPlumbingError("fail"),
                ):
                    result = _load_from_branch("main", "KEY")
        assert result is None

    def test_resolves_source_branch_from_state(self):
        """Resolves source_branch from state when not passed explicitly."""
        with patch(f"{_STATE_MOD}.get_value", return_value="feature/PROJECT-1234") as mock_get:
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", return_value="PROJECT-1234"):
                with patch(f"{_AGDT_MOD}.load_workflow_artifacts", return_value=None) as mock_load:
                    _load_from_branch(None, None)
        mock_get.assert_called_once_with("versionControl.currentBranch")
        mock_load.assert_called_once_with(
            source_branch="feature/PROJECT-1234",
            worktree_key="PROJECT-1234",
            workflow_type="reviews",
        )

    def test_resolves_worktree_key_from_state(self):
        """Resolves worktree_key via resolve_worktree_key when not passed."""
        with patch(f"{_STATE_MOD}.get_value", return_value="main"):
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", return_value="PROJECT-1234") as mock_resolve:
                with patch(f"{_AGDT_MOD}.load_workflow_artifacts", return_value=None) as mock_load:
                    _load_from_branch(None, None)
        mock_resolve.assert_called_once()
        mock_load.assert_called_once_with(
            source_branch="main",
            worktree_key="PROJECT-1234",
            workflow_type="reviews",
        )

    def test_uses_explicit_source_branch_over_state(self):
        """Uses explicit source_branch and skips state lookup."""
        with patch(f"{_STATE_MOD}.get_value") as mock_get:
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", return_value="KEY"):
                with patch(f"{_AGDT_MOD}.load_workflow_artifacts", return_value=None) as mock_load:
                    _load_from_branch("explicit", "KEY")
        mock_get.assert_not_called()
        mock_load.assert_called_once_with(
            source_branch="explicit",
            worktree_key="KEY",
            workflow_type="reviews",
        )

    def test_returns_none_when_empty_source_branch_in_state(self):
        """Returns None when state has empty/whitespace-only branch."""
        with patch(f"{_STATE_MOD}.get_value", return_value="  "):
            result = _load_from_branch(None, None)
        assert result is None

    def test_parses_string_content_as_json(self):
        """Parses raw string content returned by load_workflow_artifacts."""
        import json

        artifacts = {
            ".agdt/workflows/default/KEY/reviews/review-state.json": json.dumps({"prId": 99, "commitHash": "x"})
        }
        with patch(f"{_STATE_MOD}.get_value", return_value="main"):
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", return_value="KEY"):
                with patch(f"{_AGDT_MOD}.load_workflow_artifacts", return_value=artifacts):
                    result = _load_from_branch("main", "KEY")
        assert result is not None
        assert result["prId"] == 99

    def test_returns_none_when_no_matching_filename(self):
        """Returns None when artifacts exist but none end with review-state.json."""
        artifacts = {".agdt/workflows/default/KEY/reviews/other-file.json": {"key": "value"}}
        with patch(f"{_STATE_MOD}.get_value", return_value="main"):
            with patch(f"{_AGDT_MOD}.resolve_worktree_key", return_value="KEY"):
                with patch(f"{_AGDT_MOD}.load_workflow_artifacts", return_value=artifacts):
                    result = _load_from_branch("main", "KEY")
        assert result is None
