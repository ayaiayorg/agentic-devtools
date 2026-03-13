"""Tests for _load_from_branch in applied_suggestions module."""

from unittest.mock import patch

from agentic_devtools import state as state_module
from agentic_devtools.cli.workflows.applied_suggestions import _load_from_branch


class TestLoadFromBranch:
    """Tests for _load_from_branch function."""

    def test_returns_none_when_import_fails(self):
        """Test returns None when agdt_branch cannot be imported."""
        import builtins

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if "agdt_branch" in name:
                raise ImportError("simulated")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=failing_import):
            result = _load_from_branch("feature/TEST-1", "TEST-1")
        assert result is None

    def test_returns_none_when_no_branch(self):
        """Test returns None when no source branch can be resolved."""
        # _load_from_branch accesses get_value through _state_module.get_value()
        # (see applied_suggestions.py line 15: ``from ... import state as _state_module``),
        # so patch on the actual state module, not on the applied_suggestions module.
        with patch.object(state_module, "get_value", return_value=None):
            result = _load_from_branch(None, "KEY")
        assert result is None

    def test_returns_none_when_worktree_unresolvable(self):
        """Test returns None when worktree key cannot be resolved."""
        with patch(
            "agentic_devtools.cli.git.agdt_branch.resolve_worktree_key",
            side_effect=ValueError("no key"),
        ):
            # Patch get_value on the state module since _load_from_branch
            # accesses it through _state_module.get_value()
            # (see applied_suggestions.py line 15).
            with patch.object(state_module, "get_value", return_value=None):
                result = _load_from_branch("feature/TEST-1", None)
        assert result is None

    @patch("agentic_devtools.cli.git.agdt_branch.read_blob", return_value='{"prId": 100}')
    @patch(
        "agentic_devtools.cli.git.agdt_branch.read_branch_tree",
        return_value={
            ".agdt/workflows/default/KEY/apply-suggestions/applied-suggestions.json": "sha1",
        },
    )
    @patch("agentic_devtools.cli.git.agdt_branch._branch_exists_locally", return_value=True)
    def test_returns_dict_when_found(self, _loc, _tree, _blob):
        """Test returns parsed dict when artifact is found on branch."""
        result = _load_from_branch("feature/TEST-1", "KEY")
        assert result is not None
        assert result["prId"] == 100

    @patch("agentic_devtools.cli.git.agdt_branch.read_blob", return_value="not json")
    @patch(
        "agentic_devtools.cli.git.agdt_branch.read_branch_tree",
        return_value={
            ".agdt/workflows/default/KEY/apply-suggestions/applied-suggestions.json": "sha1",
        },
    )
    @patch("agentic_devtools.cli.git.agdt_branch._branch_exists_locally", return_value=True)
    def test_returns_none_when_artifact_is_not_json(self, _loc, _tree, _blob):
        """Test returns None when artifact content is not valid JSON."""
        result = _load_from_branch("feature/TEST-1", "KEY")
        assert result is None

    @patch(
        "agentic_devtools.cli.git.agdt_branch.read_branch_tree",
        return_value=None,
    )
    @patch("agentic_devtools.cli.git.agdt_branch._branch_exists_locally", return_value=True)
    def test_returns_none_when_no_artifacts(self, _loc, _tree):
        """Test returns None when no artifacts found on branch."""
        result = _load_from_branch("feature/TEST-1", "KEY")
        assert result is None

    @patch(
        "agentic_devtools.cli.git.agdt_branch.read_branch_tree",
        side_effect=KeyError("bad key"),
    )
    @patch("agentic_devtools.cli.git.agdt_branch._branch_exists_locally", return_value=True)
    def test_returns_none_and_warns_on_plumbing_error(self, _loc, _tree, capsys):
        """Test returns None and prints warning when git plumbing fails."""
        result = _load_from_branch("feature/TEST-1", "KEY")
        assert result is None
        captured = capsys.readouterr()
        assert "Warning: failed to load from -agdt branch:" in captured.err
