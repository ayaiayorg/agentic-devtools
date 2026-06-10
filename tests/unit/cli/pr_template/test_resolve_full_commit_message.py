"""Tests for agentic_devtools.cli.pr_template.resolve_full_commit_message."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli import pr_template


class TestResolveFullCommitMessage:
    """Tests for resolve_full_commit_message()."""

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    def test_returns_state_value_when_set(self, mock_ref, mock_get_value):
        """Happy path: returns state value when git.last_commit_message is set."""
        mock_get_value.return_value = "feat: my commit message"
        result = pr_template.resolve_full_commit_message()
        assert result == "feat: my commit message"
        mock_ref.assert_not_called()

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_returns_single_commit_from_git_log(self, mock_run_git, mock_ref, mock_get_value):
        """Returns single commit message from git log."""
        mock_get_value.return_value = None
        mock_ref.return_value = "origin/main"
        mock_run_git.return_value = MagicMock(returncode=0, stdout="feat: add feature\n\nBody text\n\x1e")
        result = pr_template.resolve_full_commit_message()
        assert result == "feat: add feature\n\nBody text"

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_multi_commit_aggregation_with_separator(self, mock_run_git, mock_ref, mock_get_value):
        """Multiple commits joined with --- separator (FR-005)."""
        mock_get_value.return_value = None
        mock_ref.return_value = "origin/main"
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="fix: second commit\n\x1efeat: first commit\n\x1e",
        )
        result = pr_template.resolve_full_commit_message()
        assert "fix: second commit" in result
        assert "feat: first commit" in result
        assert "\n\n---\n\n" in result

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_empty_branch_falls_through_to_fallback(self, mock_run_git, mock_ref, mock_get_value):
        """Empty git log output returns fallback message."""
        mock_get_value.return_value = None
        mock_ref.return_value = "origin/main"
        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        result = pr_template.resolve_full_commit_message()
        assert result == pr_template.FALLBACK_MESSAGE

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_git_failure_falls_through_to_fallback(self, mock_run_git, mock_ref, mock_get_value):
        """Git log failure returns fallback message."""
        mock_get_value.return_value = None
        mock_ref.return_value = "origin/main"
        mock_run_git.return_value = MagicMock(returncode=1, stdout="")
        result = pr_template.resolve_full_commit_message()
        assert result == pr_template.FALLBACK_MESSAGE

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    def test_no_main_ref_falls_through_to_fallback(self, mock_ref, mock_get_value):
        """No main ref available returns fallback message."""
        mock_get_value.return_value = None
        mock_ref.return_value = None
        result = pr_template.resolve_full_commit_message()
        assert result == pr_template.FALLBACK_MESSAGE

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    def test_whitespace_only_state_falls_through(self, mock_ref, mock_get_value):
        """Whitespace-only state value falls through to git log."""
        mock_get_value.return_value = "   "
        mock_ref.return_value = None
        result = pr_template.resolve_full_commit_message()
        assert result == pr_template.FALLBACK_MESSAGE

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_subject_only_commits_no_excessive_blanks(self, mock_run_git, mock_ref, mock_get_value):
        """Subject-only commits (no body) are joined cleanly."""
        mock_get_value.return_value = None
        mock_ref.return_value = "main"
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="fix: typo\n\x1efeat: add thing\n\x1e",
        )
        result = pr_template.resolve_full_commit_message()
        assert result == "fix: typo\n\n---\n\nfeat: add thing"

    @patch("agentic_devtools.cli.pr_template.get_value")
    @patch("agentic_devtools.cli.pr_template.resolve_main_ref")
    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_preserves_leading_newline_in_commit_body(self, mock_run_git, mock_ref, mock_get_value):
        """rstrip removes only trailing newlines; leading blank lines in the body are preserved."""
        mock_get_value.return_value = None
        mock_ref.return_value = "origin/main"
        # Simulate a commit entry that has a leading blank line before the body
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="\nfeat: message with leading newline\n\x1e",
        )
        result = pr_template.resolve_full_commit_message()
        # Leading newline is preserved; trailing newline stripped
        assert result == "\nfeat: message with leading newline"
