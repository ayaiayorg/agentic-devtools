"""Tests for agentic_devtools.cli.pr_template.resolve_pr_body."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli import pr_template


class TestResolvePrBody:
    """Tests for resolve_pr_body()."""

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_template_with_placeholder_happy_path(self, mock_resolve, mock_path, tmp_path):
        """Happy path: template with placeholder gets commit message injected (FR-003)."""
        template_file = tmp_path / "template.md"
        template_file.write_text("# PR\n\n## Info\n\n{{fullCommitMessage}}\n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_resolve.return_value = "feat: my feature"

        result = pr_template.resolve_pr_body()
        assert "feat: my feature" in result
        assert "# PR" in result
        assert "{{fullCommitMessage}}" not in result

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_template_preserves_markdown_content(self, mock_resolve, mock_path, tmp_path):
        """Template markdown content is preserved verbatim (FR-009)."""
        content = "# Title\n\n- [ ] checkbox\n- [x] done\n\n{{fullCommitMessage}}\n"
        template_file = tmp_path / "template.md"
        template_file.write_text(content, encoding="utf-8")
        mock_path.return_value = template_file
        mock_resolve.return_value = "msg"

        result = pr_template.resolve_pr_body()
        assert "- [ ] checkbox" in result
        assert "- [x] done" in result

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    def test_template_without_placeholder_renders_as_is(self, mock_path, tmp_path):
        """Template without placeholder returned as-is (FR-007)."""
        template_file = tmp_path / "template.md"
        template_file.write_text("# Just a template\n\nNo placeholder here.\n", encoding="utf-8")
        mock_path.return_value = template_file

        result = pr_template.resolve_pr_body()
        assert result == "# Just a template\n\nNo placeholder here.\n"

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_empty_template_returns_commit_message(self, mock_resolve, mock_path, tmp_path):
        """Empty template returns commit message (FR-007)."""
        template_file = tmp_path / "template.md"
        template_file.write_text("", encoding="utf-8")
        mock_path.return_value = template_file
        mock_resolve.return_value = "fallback msg"

        result = pr_template.resolve_pr_body()
        assert result == "fallback msg"

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_whitespace_only_template_returns_commit_message(self, mock_resolve, mock_path, tmp_path):
        """Whitespace-only template returns commit message."""
        template_file = tmp_path / "template.md"
        template_file.write_text("   \n  \n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_resolve.return_value = "fallback msg"

        result = pr_template.resolve_pr_body()
        assert result == "fallback msg"

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_missing_template_warns_and_returns_commit_message(self, mock_resolve, mock_path, tmp_path, capsys):
        """Missing template emits warning and returns commit message (FR-006)."""
        mock_path.return_value = tmp_path / "nonexistent.md"
        mock_resolve.return_value = "commit msg"

        result = pr_template.resolve_pr_body()
        assert result == "commit msg"
        captured = capsys.readouterr()
        assert "agdt-init-pr-template" in captured.err

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_markdown_special_chars_preserved_in_interpolation(self, mock_resolve, mock_path, tmp_path):
        """Commit messages with markdown special chars preserved (FR-009)."""
        template_file = tmp_path / "template.md"
        template_file.write_text("Body:\n{{fullCommitMessage}}\n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_resolve.return_value = "feat: use `backticks` | pipes | [brackets]"

        result = pr_template.resolve_pr_body()
        assert "feat: use `backticks` | pipes | [brackets]" in result

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_placeholder_at_different_positions(self, mock_resolve, mock_path, tmp_path):
        """Placeholder works regardless of position in template (FR-003)."""
        template_file = tmp_path / "template.md"
        template_file.write_text("{{fullCommitMessage}}\n\n---\n\nFooter\n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_resolve.return_value = "Header commit"

        result = pr_template.resolve_pr_body()
        assert result.startswith("Header commit")
        assert "Footer" in result

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_unreadable_template_warns_and_returns_commit_message(self, mock_resolve, mock_path, capsys):
        """Unreadable template (OSError) emits warning and falls back to commit message."""
        mock_template = MagicMock()
        mock_template.exists.return_value = True
        mock_template.read_text.side_effect = OSError("permission denied")
        mock_path.return_value = mock_template
        mock_resolve.return_value = "fallback commit msg"

        result = pr_template.resolve_pr_body()

        assert result == "fallback commit msg"
        captured = capsys.readouterr()
        assert "Could not read PR template" in captured.err
        assert "permission denied" in captured.err

    @patch("agentic_devtools.cli.pr_template.get_template_path")
    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_non_utf8_template_warns_and_returns_commit_message(self, mock_resolve, mock_path, capsys):
        """Invalid UTF-8 template emits warning and falls back to commit message."""
        mock_template = MagicMock()
        mock_template.exists.return_value = True
        mock_template.read_text.side_effect = UnicodeDecodeError(
            "utf-8",
            b"\x80",
            0,
            1,
            "invalid start byte",
        )
        mock_path.return_value = mock_template
        mock_resolve.return_value = "fallback commit msg"

        result = pr_template.resolve_pr_body()

        assert result == "fallback commit msg"
        captured = capsys.readouterr()
        assert "Could not read PR template" in captured.err
        assert "invalid start byte" in captured.err
