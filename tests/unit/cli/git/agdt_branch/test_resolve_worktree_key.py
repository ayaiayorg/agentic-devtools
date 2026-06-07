"""Tests for agentic_devtools.cli.git.agdt_branch.resolve_worktree_key."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.git.agdt_branch import resolve_worktree_key

_MOD = "agentic_devtools.cli.git.agdt_branch"


# ---------------------------------------------------------------------------
#  Explicit key passthrough
# ---------------------------------------------------------------------------


class TestResolveWorktreeKeyExplicit:
    """Tests for explicit key passthrough (no state lookup)."""

    def test_explicit_key_returned_directly(self):
        """Explicit non-empty key is returned without state lookup."""
        with patch(f"{_MOD}.get_value") as mock_get:
            result = resolve_worktree_key("PROJECT-1234")
        assert result == "PROJECT-1234"
        mock_get.assert_not_called()

    def test_explicit_key_stripped(self):
        """Leading/trailing whitespace is stripped from explicit key."""
        result = resolve_worktree_key("  PROJECT-1234  ")
        assert result == "PROJECT-1234"

    def test_explicit_key_with_pr_prefix(self):
        """Explicit key with PR prefix is returned as-is (passthrough)."""
        result = resolve_worktree_key("PR99999")
        assert result == "PR99999"


# ---------------------------------------------------------------------------
#  Auto-resolution from issue_key (provider-agnostic)
# ---------------------------------------------------------------------------


class TestResolveWorktreeKeyAutoFromIssueKey:
    """Tests for auto-resolution from top-level issue_key state."""

    @patch(f"{_MOD}.get_value")
    def test_resolves_from_issue_key(self, mock_get):
        """Auto-resolves from issue_key when no explicit key."""
        mock_get.side_effect = lambda k: "42" if k == "issue_key" else None
        result = resolve_worktree_key()
        assert result == "42"

    @patch(f"{_MOD}.get_value")
    def test_issue_key_takes_priority_over_jira_key(self, mock_get):
        """issue_key takes priority over jira.issue_key."""
        mock_get.side_effect = lambda k: {
            "issue_key": "#42",
            "jira.issue_key": "PROJECT-1234",
            "pull_request_id": 99999,
        }.get(k)
        result = resolve_worktree_key()
        assert result == "#42"

    @patch(f"{_MOD}.get_value")
    def test_issue_key_stripped(self, mock_get):
        """issue_key value is stripped of whitespace."""
        mock_get.side_effect = lambda k: "  42  " if k == "issue_key" else None
        result = resolve_worktree_key()
        assert result == "42"

    @patch(f"{_MOD}.get_value")
    def test_empty_issue_key_falls_through_to_jira(self, mock_get):
        """Empty issue_key falls through to jira.issue_key."""
        mock_get.side_effect = lambda k: {
            "issue_key": "",
            "jira.issue_key": "PROJECT-1234",
        }.get(k)
        result = resolve_worktree_key()
        assert result == "PROJECT-1234"

    @patch(f"{_MOD}.get_value")
    def test_whitespace_issue_key_falls_through_to_jira(self, mock_get):
        """Whitespace-only issue_key falls through to jira.issue_key."""
        mock_get.side_effect = lambda k: {
            "issue_key": "   ",
            "jira.issue_key": "PROJECT-1234",
        }.get(k)
        result = resolve_worktree_key()
        assert result == "PROJECT-1234"

    @patch(f"{_MOD}.get_value")
    def test_int_issue_key_stringified(self, mock_get):
        """Plain int issue_key is stringified (agdt-set JSON-parses to int)."""
        mock_get.side_effect = lambda k: 42 if k == "issue_key" else None
        result = resolve_worktree_key()
        assert result == "42"

    @patch(f"{_MOD}.get_value")
    def test_bool_issue_key_falls_through(self, mock_get):
        """Bool issue_key is ignored — falls through to jira.issue_key."""
        mock_get.side_effect = lambda k: {
            "issue_key": True,
            "jira.issue_key": "PROJECT-1234",
        }.get(k)
        result = resolve_worktree_key()
        assert result == "PROJECT-1234"

    @patch(f"{_MOD}.get_value")
    def test_dict_issue_key_falls_through(self, mock_get):
        """Dict issue_key is ignored — falls through to jira.issue_key."""
        mock_get.side_effect = lambda k: {
            "issue_key": {"bad": "value"},
            "jira.issue_key": "PROJECT-1234",
        }.get(k)
        result = resolve_worktree_key()
        assert result == "PROJECT-1234"

    @patch(f"{_MOD}.get_value")
    def test_list_issue_key_falls_through(self, mock_get):
        """List issue_key is ignored — falls through to pull_request_id."""
        mock_get.side_effect = lambda k: {
            "issue_key": [1, 2, 3],
            "pull_request_id": 99,
        }.get(k)
        result = resolve_worktree_key()
        assert result == "PR99"


# ---------------------------------------------------------------------------
#  Auto-resolution from jira.issue_key
# ---------------------------------------------------------------------------


class TestResolveWorktreeKeyAutoFromJira:
    """Tests for auto-resolution from jira.issue_key state."""

    @patch(f"{_MOD}.get_value")
    def test_resolves_from_jira_issue_key(self, mock_get):
        """Auto-resolves from jira.issue_key when no explicit key."""
        mock_get.side_effect = lambda k: "PROJECT-1234" if k == "jira.issue_key" else None
        result = resolve_worktree_key()
        assert result == "PROJECT-1234"

    @patch(f"{_MOD}.get_value")
    def test_jira_key_takes_priority_over_pr_id(self, mock_get):
        """jira.issue_key takes priority when both jira and PR are set."""
        mock_get.side_effect = lambda k: {
            "jira.issue_key": "PROJECT-1234",
            "pull_request_id": 12345,
        }.get(k)
        result = resolve_worktree_key()
        assert result == "PROJECT-1234"

    @patch(f"{_MOD}.get_value")
    def test_jira_key_stripped(self, mock_get):
        """jira.issue_key value is stripped of whitespace."""
        mock_get.side_effect = lambda k: "  PROJECT-1234  " if k == "jira.issue_key" else None
        result = resolve_worktree_key()
        assert result == "PROJECT-1234"


# ---------------------------------------------------------------------------
#  Auto-resolution from pull_request_id
# ---------------------------------------------------------------------------


class TestResolveWorktreeKeyAutoFromPR:
    """Tests for auto-resolution from pull_request_id state."""

    @patch(f"{_MOD}.get_value")
    def test_resolves_from_pull_request_id_int(self, mock_get):
        """Auto-resolves from integer pull_request_id with PR prefix."""
        mock_get.side_effect = lambda k: 12345 if k == "pull_request_id" else None
        result = resolve_worktree_key()
        assert result == "PR12345"

    @patch(f"{_MOD}.get_value")
    def test_resolves_from_pull_request_id_string(self, mock_get):
        """Auto-resolves from string pull_request_id with PR prefix."""
        mock_get.side_effect = lambda k: "67890" if k == "pull_request_id" else None
        result = resolve_worktree_key()
        assert result == "PR67890"

    @patch(f"{_MOD}.get_value")
    def test_pr_id_used_when_jira_key_empty(self, mock_get):
        """Falls through to pull_request_id when jira.issue_key is empty string."""
        mock_get.side_effect = lambda k: {
            "issue_key": None,
            "jira.issue_key": "",
            "pull_request_id": 12345,
        }.get(k)
        result = resolve_worktree_key()
        assert result == "PR12345"

    @patch(f"{_MOD}.get_value")
    def test_pr_id_used_when_jira_key_whitespace(self, mock_get):
        """Falls through to pull_request_id when jira.issue_key is whitespace-only."""
        mock_get.side_effect = lambda k: {
            "issue_key": None,
            "jira.issue_key": "   ",
            "pull_request_id": 12345,
        }.get(k)
        result = resolve_worktree_key()
        assert result == "PR12345"


# ---------------------------------------------------------------------------
#  Failure cases
# ---------------------------------------------------------------------------


class TestResolveWorktreeKeyFailure:
    """Tests for ValueError when resolution fails."""

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_raises_value_error_when_neither_set(self, _mock):
        """Raises ValueError when neither state key is set."""
        with pytest.raises(ValueError, match="Cannot resolve worktree key"):
            resolve_worktree_key()

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_raises_when_none_explicit_and_no_state(self, _mock):
        """Raises ValueError when explicit_key=None and no state."""
        with pytest.raises(ValueError):
            resolve_worktree_key(None)

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_raises_when_empty_string_explicit_and_no_state(self, _mock):
        """Raises ValueError when explicit_key='' and no state."""
        with pytest.raises(ValueError):
            resolve_worktree_key("")

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_raises_when_whitespace_explicit_and_no_state(self, _mock):
        """Raises ValueError when explicit_key is whitespace-only and no state."""
        with pytest.raises(ValueError):
            resolve_worktree_key("   ")

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_error_message_is_descriptive(self, _mock):
        """ValueError message mentions all state keys."""
        with pytest.raises(ValueError, match="issue_key") as exc_info:
            resolve_worktree_key()
        assert "pull_request_id" in str(exc_info.value)
        assert "jira.issue_key" in str(exc_info.value)

    @patch(f"{_MOD}.get_value")
    def test_raises_when_pr_id_is_whitespace_only(self, mock_get):
        """Raises ValueError when pull_request_id strips to empty string."""
        mock_get.side_effect = lambda k: {
            "issue_key": None,
            "jira.issue_key": None,
            "pull_request_id": "   ",
        }.get(k)
        with pytest.raises(ValueError, match="Cannot resolve worktree key"):
            resolve_worktree_key()


# ---------------------------------------------------------------------------
#  Integration: persist_workflow_state
# ---------------------------------------------------------------------------


class TestPersistWorkflowStateWorktreeKeyIntegration:
    """Tests for worktree_key auto-resolution in persist_workflow_state."""

    @patch(f"{_MOD}.resolve_worktree_key", return_value="PROJECT-1234")
    @patch(f"{_MOD}._discover_workflow_files", return_value={})
    @patch(f"{_MOD}._get_repo_root")
    def test_persist_auto_resolves_worktree_key(self, _root, _disc, mock_resolve):
        """persist_workflow_state calls resolve_worktree_key with None."""
        from agentic_devtools.cli.git.agdt_branch import persist_workflow_state

        result = persist_workflow_state("feat", worktree_key=None)
        mock_resolve.assert_called_once_with(None)
        assert result.worktree_key == "PROJECT-1234"

    @patch(
        f"{_MOD}.resolve_worktree_key",
        side_effect=ValueError("Cannot resolve worktree key"),
    )
    def test_persist_returns_failure_when_resolution_fails(self, _mock):
        """persist_workflow_state returns PersistResult(success=False) on ValueError."""
        from agentic_devtools.cli.git.agdt_branch import persist_workflow_state

        result = persist_workflow_state("feat", worktree_key=None)
        assert result.success is False
        assert "Cannot resolve worktree key" in result.error
        assert result.branch_name == "feat-agdt"
        assert result.worktree_key == ""

    @patch(f"{_MOD}.resolve_worktree_key", return_value="EXPLICIT")
    @patch(f"{_MOD}._discover_workflow_files", return_value={})
    @patch(f"{_MOD}._get_repo_root")
    def test_persist_passes_explicit_key_through(self, _root, _disc, mock_resolve):
        """persist_workflow_state forwards explicit key to resolve_worktree_key."""
        from agentic_devtools.cli.git.agdt_branch import persist_workflow_state

        persist_workflow_state("feat", worktree_key="EXPLICIT")
        mock_resolve.assert_called_once_with("EXPLICIT")


# ---------------------------------------------------------------------------
#  Integration: load_workflow_artifacts
# ---------------------------------------------------------------------------


class TestLoadWorkflowArtifactsWorktreeKeyIntegration:
    """Tests for worktree_key auto-resolution in load_workflow_artifacts."""

    @patch(f"{_MOD}.read_blob", return_value='{"k": "v"}')
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={".agdt/workflows/default/PROJECT-1234/state.json": "sha1"},
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    @patch(f"{_MOD}.resolve_worktree_key", return_value="PROJECT-1234")
    def test_load_auto_resolves_worktree_key(self, mock_resolve, _loc, _tree, _blob):
        """load_workflow_artifacts proceeds when resolve_worktree_key succeeds."""
        from agentic_devtools.cli.git.agdt_branch import load_workflow_artifacts

        result = load_workflow_artifacts("feat", worktree_key=None)
        mock_resolve.assert_called_once_with(None)
        assert result is not None

    @patch(
        f"{_MOD}.resolve_worktree_key",
        side_effect=ValueError("Cannot resolve"),
    )
    def test_load_returns_none_when_resolution_fails(self, _mock):
        """load_workflow_artifacts returns None when resolve_worktree_key raises."""
        from agentic_devtools.cli.git.agdt_branch import load_workflow_artifacts

        result = load_workflow_artifacts("feat", worktree_key=None)
        assert result is None
