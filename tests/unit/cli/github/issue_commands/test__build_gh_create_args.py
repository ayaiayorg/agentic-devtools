"""Tests for _build_gh_create_args helper."""

from unittest.mock import patch

from agentic_devtools.cli.github import issue_commands
from agentic_devtools.cli.github.issue_commands import AGDT_REPO, _build_gh_create_args


class TestBuildGhCreateArgs:
    """Tests for _build_gh_create_args."""

    def test_minimal_args(self):
        """Minimal call includes gh, issue, create, --repo, --title, --body."""
        args = _build_gh_create_args(title="My title", body="My body")
        assert "gh" in args
        assert "issue" in args
        assert "create" in args
        assert "--repo" in args
        assert AGDT_REPO in args
        assert "--title" in args
        assert "My title" in args
        assert "--body" in args
        assert "My body" in args

    def test_labels_added(self):
        """Labels are added as --label flags."""
        args = _build_gh_create_args(title="T", body="B", labels=["bug", "enhancement"])
        label_indices = [i for i, a in enumerate(args) if a == "--label"]
        assert len(label_indices) == 2
        assert args[label_indices[0] + 1] == "bug"
        assert args[label_indices[1] + 1] == "enhancement"

    def test_issue_type_normalized_when_supported(self):
        """Issue type 'bug' is normalized to 'Bug' when --type is supported."""
        with patch.object(issue_commands, "_gh_supports_issue_type", return_value=True):
            args = _build_gh_create_args(title="T", body="B", issue_type="bug")
        assert "--type" in args
        type_idx = args.index("--type")
        assert args[type_idx + 1] == "Bug"

    def test_issue_type_passthrough_when_unknown_and_supported(self):
        """Unknown issue type is passed through as-is when --type is supported."""
        with patch.object(issue_commands, "_gh_supports_issue_type", return_value=True):
            args = _build_gh_create_args(title="T", body="B", issue_type="Custom")
        assert "--type" in args
        type_idx = args.index("--type")
        assert args[type_idx + 1] == "Custom"

    def test_issue_type_skipped_when_not_supported(self):
        """--type flag is omitted when gh CLI does not support it."""
        with patch.object(issue_commands, "_gh_supports_issue_type", return_value=False):
            args = _build_gh_create_args(title="T", body="B", issue_type="Bug")
        assert "--type" not in args

    def test_assignees_added(self):
        """Assignees are added as --assignee flags."""
        args = _build_gh_create_args(title="T", body="B", assignees=["alice", "bob"])
        assignee_indices = [i for i, a in enumerate(args) if a == "--assignee"]
        assert len(assignee_indices) == 2

    def test_milestone_added(self):
        """Milestone is added with --milestone flag."""
        args = _build_gh_create_args(title="T", body="B", milestone="v1.0")
        assert "--milestone" in args
        ms_idx = args.index("--milestone")
        assert args[ms_idx + 1] == "v1.0"

    def test_no_optional_flags_when_none(self):
        """No optional flags appear when all optionals are None."""
        args = _build_gh_create_args(title="T", body="B")
        assert "--label" not in args
        assert "--type" not in args
        assert "--assignee" not in args
        assert "--milestone" not in args
