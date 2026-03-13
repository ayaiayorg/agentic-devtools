"""Tests for _load_from_branch helper function."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli import activity_log as al_module
from agentic_devtools.cli.activity_log import _load_from_branch

# The _load_from_branch function uses lazy imports inside the function body,
# so we patch at the agdt_branch module level (where the functions live).
_AGDT = "agentic_devtools.cli.git.agdt_branch"


class TestLoadFromBranch:
    """Tests for the _load_from_branch helper function."""

    def test_returns_none_when_import_fails(self):
        """Test that _load_from_branch returns None when agdt_branch import fails."""
        import builtins

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if "agdt_branch" in name:
                raise ImportError("simulated")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=failing_import):
            result = _load_from_branch(None, None)

        assert result is None

    def test_returns_none_when_no_branch_resolvable(self):
        """Test returns None when source_branch is None and state has no branch."""
        with patch.object(al_module, "get_value", return_value=None):
            result = _load_from_branch(None, None)

        assert result is None

    def test_returns_none_when_branch_is_whitespace(self):
        """Test returns None when resolved branch is whitespace-only."""

        def side_effect(key):
            if key == "sourceCodeHostingPlatform.pullRequest.sourceBranch":
                return "   "
            return None

        with patch.object(al_module, "get_value", side_effect=side_effect):
            result = _load_from_branch(None, None)

        assert result is None

    def test_resolves_source_branch_from_pr_state(self):
        """Test source_branch resolution from sourceCodeHostingPlatform.pullRequest.sourceBranch."""
        mock_artifacts = {".agdt/workflows/default/KEY/activity-log/activity-log.json": {"postedCommits": {}}}

        def get_value_side(key):
            if key == "sourceCodeHostingPlatform.pullRequest.sourceBranch":
                return "feature/X"
            return None

        with patch.object(al_module, "get_value", side_effect=get_value_side):
            with patch(f"{_AGDT}.load_workflow_artifacts", return_value=mock_artifacts):
                with patch(f"{_AGDT}.resolve_worktree_key", return_value="KEY"):
                    result = _load_from_branch(None, None)

        assert result == {"postedCommits": {}}

    def test_resolves_source_branch_from_current_branch_state(self):
        """Test falls back to versionControl.currentBranch when PR branch missing."""
        mock_artifacts = {".agdt/workflows/default/KEY/activity-log/activity-log.json": {"postedCommits": {}}}

        def get_value_side(key):
            if key == "sourceCodeHostingPlatform.pullRequest.sourceBranch":
                return None
            if key == "versionControl.currentBranch":
                return "develop"
            return None

        with patch.object(al_module, "get_value", side_effect=get_value_side):
            with patch(f"{_AGDT}.load_workflow_artifacts", return_value=mock_artifacts):
                with patch(f"{_AGDT}.resolve_worktree_key", return_value="KEY"):
                    result = _load_from_branch(None, None)

        assert result is not None

    def test_returns_none_when_worktree_key_unresolvable(self):
        """Test returns None when resolve_worktree_key raises ValueError."""
        with patch(f"{_AGDT}.resolve_worktree_key", side_effect=ValueError("no key")):
            result = _load_from_branch("feature/X", None)

        assert result is None

    def test_returns_none_when_artifacts_is_none(self):
        """Test returns None when load_workflow_artifacts returns None."""
        with patch(f"{_AGDT}.load_workflow_artifacts", return_value=None):
            result = _load_from_branch("feature/X", "KEY")

        assert result is None

    def test_returns_dict_content_directly(self):
        """Test that dict content from artifacts is returned directly."""
        log_data = {"postedCommits": {"abc": {"postedUtc": "2026-01-01T00:00:00Z"}}}
        mock_artifacts = {".agdt/workflows/default/KEY/activity-log/activity-log.json": log_data}

        with patch(f"{_AGDT}.load_workflow_artifacts", return_value=mock_artifacts):
            result = _load_from_branch("feature/X", "KEY")

        assert result == log_data

    def test_returns_parsed_string_content(self):
        """Test that string content from artifacts is JSON-parsed."""
        log_data = {"postedCommits": {}}
        mock_artifacts = {".agdt/workflows/default/KEY/activity-log/activity-log.json": json.dumps(log_data)}

        with patch(f"{_AGDT}.load_workflow_artifacts", return_value=mock_artifacts):
            result = _load_from_branch("feature/X", "KEY")

        assert result == log_data

    def test_returns_none_when_no_matching_file_in_artifacts(self):
        """Test returns None when artifacts exist but no activity-log.json file."""
        mock_artifacts = {".agdt/workflows/default/KEY/other/file.json": {"some": "data"}}

        with patch(f"{_AGDT}.load_workflow_artifacts", return_value=mock_artifacts):
            result = _load_from_branch("feature/X", "KEY")

        assert result is None

    def test_returns_none_on_git_plumbing_error(self):
        """Test returns None when GitPlumbingError is raised."""
        from agentic_devtools.cli.git.agdt_branch import GitPlumbingError

        with patch(
            f"{_AGDT}.load_workflow_artifacts",
            side_effect=GitPlumbingError("fail"),
        ):
            result = _load_from_branch("feature/X", "KEY")

        assert result is None

    def test_uses_explicit_source_branch(self):
        """Test that explicit source_branch is used without state lookup."""
        mock_load = MagicMock(return_value=None)

        with patch(f"{_AGDT}.load_workflow_artifacts", mock_load):
            _load_from_branch("explicit/branch", "KEY")

        mock_load.assert_called_once_with(
            source_branch="explicit/branch",
            worktree_key="KEY",
            workflow_type="activity-log",
        )

    def test_uses_explicit_worktree_key(self):
        """Test that explicit worktree_key is used without resolve_worktree_key."""
        mock_resolve = MagicMock()

        with patch(f"{_AGDT}.load_workflow_artifacts", return_value=None):
            with patch(f"{_AGDT}.resolve_worktree_key", mock_resolve):
                _load_from_branch("feature/X", "EXPLICIT-KEY")

        mock_resolve.assert_not_called()
