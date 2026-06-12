"""Tests for agentic_devtools.cli.pr_template._render_j2_body_template."""

from unittest.mock import patch

from agentic_devtools.cli.pr_template import _render_j2_body_template


class TestRenderJ2BodyTemplate:
    """Tests for _render_j2_body_template()."""

    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_renders_simple_template(self, mock_resolve):
        """Renders a simple template with fullCommitMessage variable."""
        mock_resolve.return_value = "feat: add feature"
        content = "# PR\n\n{{ fullCommitMessage }}\n"

        result = _render_j2_body_template(content)
        assert result == "# PR\n\nfeat: add feature\n"

    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_preserves_multiline_commit_message(self, mock_resolve):
        """Preserves newlines in the commit message."""
        mock_resolve.return_value = "feat: title\n\n- bullet 1\n- bullet 2"
        content = "Body:\n{{ fullCommitMessage }}\n"

        result = _render_j2_body_template(content)
        assert "- bullet 1\n- bullet 2" in result

    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_syntax_error_returns_commit_message(self, mock_resolve, capsys):
        """Returns commit message on Jinja2 syntax error."""
        mock_resolve.return_value = "fallback msg"
        content = "{{ unclosed"

        result = _render_j2_body_template(content)
        assert result == "fallback msg"
        captured = capsys.readouterr()
        assert "syntax error" in captured.err

    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_undefined_variable_renders_empty(self, mock_resolve):
        """Undefined variables render as empty string (not error)."""
        mock_resolve.return_value = "msg"
        content = "{{ fullCommitMessage }} {{ someUndefined }}\n"

        result = _render_j2_body_template(content)
        assert "msg" in result
        # Undefined renders as empty, no error

    @patch("agentic_devtools.cli.pr_template.resolve_full_commit_message")
    def test_keeps_trailing_newline(self, mock_resolve):
        """Keeps trailing newline from template."""
        mock_resolve.return_value = "msg"
        content = "Header\n{{ fullCommitMessage }}\n"

        result = _render_j2_body_template(content)
        assert result.endswith("\n")
