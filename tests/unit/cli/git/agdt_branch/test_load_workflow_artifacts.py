"""Tests for agentic_devtools.cli.git.agdt_branch.load_workflow_artifacts."""

from unittest.mock import patch

from agentic_devtools.cli.git.agdt_branch import load_workflow_artifacts

_MOD = "agentic_devtools.cli.git.agdt_branch"


# ---------------------------------------------------------------------------
#  Validation
# ---------------------------------------------------------------------------


class TestLoadWorkflowArtifactsValidation:
    """Validation and defaults tests."""

    def test_worktree_key_none_returns_none(self):
        """worktree_key=None returns None without any git calls."""
        result = load_workflow_artifacts("feat", worktree_key=None)
        assert result is None

    @patch(f"{_MOD}.read_blob", return_value='{"k": "v"}')
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={".agdt/workflows/default/KEY/review/state.json": "sha1"},
    )
    @patch(f"{_MOD}._fetch_branch", return_value=True)
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_identity_defaults_to_default(self, _loc, _rem, _fetch, mock_tree, _blob):
        """When identity=None, files under .agdt/workflows/default/ are matched."""
        result = load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review", identity=None)
        assert result is not None
        assert ".agdt/workflows/default/KEY/review/state.json" in result

    @patch(f"{_MOD}.read_blob", return_value='{"k": "v"}')
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={".agdt/workflows/default/KEY/review/state.json": "sha1"},
    )
    @patch(f"{_MOD}._fetch_branch", return_value=True)
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_double_suffix_prevention(self, mock_loc, _rem, _fetch, _tree, _blob):
        """source_branch ending with -agdt is NOT double-suffixed."""
        load_workflow_artifacts("feat-agdt", worktree_key="KEY", workflow_type="review")
        # _branch_exists_locally should have been called with "feat-agdt", not "feat-agdt-agdt"
        mock_loc.assert_called_once_with("feat-agdt")


# ---------------------------------------------------------------------------
#  Branch Existence
# ---------------------------------------------------------------------------


class TestLoadWorkflowArtifactsBranchExistence:
    """Branch existence and fetching tests."""

    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=False)
    def test_returns_none_when_branch_not_found(self, _loc, _rem):
        """Returns None when branch doesn't exist locally or remotely."""
        result = load_workflow_artifacts("feat", worktree_key="KEY")
        assert result is None

    @patch(f"{_MOD}.read_blob", return_value="{}")
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={".agdt/workflows/default/KEY/review/f.json": "sha"},
    )
    @patch(f"{_MOD}._fetch_branch", return_value=True)
    @patch(f"{_MOD}._branch_exists_remotely", return_value=True)
    @patch(f"{_MOD}._branch_exists_locally", return_value=False)
    def test_fetches_remote_branch_when_local_missing(self, _loc, _rem, mock_fetch, _tree, _blob):
        """Fetches from remote when local branch is missing."""
        result = load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review")
        mock_fetch.assert_called_once_with("feat-agdt")
        assert result is not None

    @patch(f"{_MOD}._fetch_branch", return_value=False)
    @patch(f"{_MOD}._branch_exists_remotely", return_value=True)
    @patch(f"{_MOD}._branch_exists_locally", return_value=False)
    def test_returns_none_when_fetch_fails(self, _loc, _rem, _fetch):
        """Returns None when fetch from remote fails."""
        result = load_workflow_artifacts("feat", worktree_key="KEY")
        assert result is None

    @patch(f"{_MOD}.read_blob", return_value="{}")
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={".agdt/workflows/default/KEY/review/f.json": "sha"},
    )
    @patch(f"{_MOD}._branch_exists_remotely", return_value=False)
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_skips_remote_check_when_local_exists(self, _loc, mock_rem, _tree, _blob):
        """Does not check remote when local branch exists."""
        load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review")
        mock_rem.assert_not_called()


# ---------------------------------------------------------------------------
#  Path Filtering
# ---------------------------------------------------------------------------


class TestLoadWorkflowArtifactsPathFiltering:
    """Path prefix filtering tests."""

    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={"other/file.txt": "sha"},
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_returns_none_when_no_matching_paths(self, _loc, _tree):
        """Returns None when no tree entries match the prefix."""
        result = load_workflow_artifacts("feat", worktree_key="KEY")
        assert result is None

    @patch(f"{_MOD}.read_blob", return_value='{"ok": true}')
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={
            ".agdt/workflows/default/KEY/review/state.json": "sha1",
            ".agdt/workflows/default/KEY/impl/plan.json": "sha2",
        },
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_filters_by_workflow_type(self, _loc, _tree, mock_blob):
        """Only files matching the specified workflow_type are returned."""
        result = load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review")
        assert result is not None
        assert ".agdt/workflows/default/KEY/review/state.json" in result
        assert ".agdt/workflows/default/KEY/impl/plan.json" not in result

    @patch(f"{_MOD}.read_blob", return_value='{"ok": true}')
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={
            ".agdt/workflows/default/KEY/review/state.json": "sha1",
            ".agdt/workflows/default/KEY/impl/plan.json": "sha2",
        },
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_loads_all_types_when_workflow_type_none(self, _loc, _tree, _blob):
        """All workflow types are loaded when workflow_type is None."""
        result = load_workflow_artifacts("feat", worktree_key="KEY")
        assert result is not None
        assert ".agdt/workflows/default/KEY/review/state.json" in result
        assert ".agdt/workflows/default/KEY/impl/plan.json" in result

    @patch(f"{_MOD}.read_branch_tree", return_value={})
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_returns_none_when_tree_is_empty(self, _loc, _tree):
        """Returns None when read_branch_tree returns an empty dict."""
        result = load_workflow_artifacts("feat", worktree_key="KEY")
        assert result is None


# ---------------------------------------------------------------------------
#  Content Parsing
# ---------------------------------------------------------------------------


class TestLoadWorkflowArtifactsContentParsing:
    """JSON parsing and raw string fallback tests."""

    @patch(f"{_MOD}.read_blob", return_value='{"key": "value"}')
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={".agdt/workflows/default/KEY/review/state.json": "sha1"},
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_parses_json_content(self, _loc, _tree, _blob):
        """Valid JSON content is parsed into a Python dict."""
        result = load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review")
        assert result is not None
        val = result[".agdt/workflows/default/KEY/review/state.json"]
        assert val == {"key": "value"}
        assert isinstance(val, dict)

    @patch(f"{_MOD}.read_blob", return_value="not json content")
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={".agdt/workflows/default/KEY/review/notes.txt": "sha1"},
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_returns_raw_string_for_invalid_json(self, _loc, _tree, _blob):
        """Non-JSON content is stored as a raw string."""
        result = load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review")
        assert result is not None
        assert result[".agdt/workflows/default/KEY/review/notes.txt"] == "not json content"

    @patch(f"{_MOD}.read_blob")
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={
            ".agdt/workflows/default/KEY/review/state.json": "sha1",
            ".agdt/workflows/default/KEY/review/notes.txt": "sha2",
        },
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_mixed_json_and_non_json_files(self, _loc, _tree, mock_blob):
        """JSON files are parsed; non-JSON files are returned as strings."""
        mock_blob.side_effect = lambda sha: '{"parsed": true}' if sha == "sha1" else "plain text"
        result = load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review")
        assert result is not None
        assert result[".agdt/workflows/default/KEY/review/state.json"] == {"parsed": True}
        assert result[".agdt/workflows/default/KEY/review/notes.txt"] == "plain text"

    @patch(f"{_MOD}.read_blob", return_value="[1, 2, 3]")
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={".agdt/workflows/default/KEY/review/items.json": "sha1"},
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_parses_json_array(self, _loc, _tree, _blob):
        """JSON arrays are correctly parsed."""
        result = load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review")
        assert result is not None
        assert result[".agdt/workflows/default/KEY/review/items.json"] == [1, 2, 3]


# ---------------------------------------------------------------------------
#  Integration
# ---------------------------------------------------------------------------


class TestLoadWorkflowArtifactsIntegration:
    """End-to-end integration tests."""

    @patch(f"{_MOD}.read_blob")
    @patch(
        f"{_MOD}.read_branch_tree",
        return_value={
            ".agdt/workflows/default/KEY/review/state.json": "sha1",
            ".agdt/workflows/default/KEY/review/queue.json": "sha2",
            "README.md": "readme_sha",
        },
    )
    @patch(f"{_MOD}._branch_exists_locally", return_value=True)
    def test_full_flow_returns_correct_dict(self, _loc, _tree, mock_blob):
        """Full flow: branch exists, tree has matching and non-matching files."""
        mock_blob.side_effect = lambda sha: {
            "sha1": '{"status": "active"}',
            "sha2": '{"files": ["a.ts", "b.ts"]}',
        }[sha]

        result = load_workflow_artifacts("feat", worktree_key="KEY", workflow_type="review")
        assert result is not None
        assert len(result) == 2
        assert result[".agdt/workflows/default/KEY/review/state.json"] == {"status": "active"}
        assert result[".agdt/workflows/default/KEY/review/queue.json"] == {"files": ["a.ts", "b.ts"]}
        # README.md should NOT be in the result
        assert "README.md" not in result
