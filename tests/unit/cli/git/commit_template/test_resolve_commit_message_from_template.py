"""Tests for resolve_commit_message_from_template."""

from unittest.mock import Mock, patch

from agentic_devtools.cli.git.commit_template import (
    TEMPLATE_PATH,
    resolve_commit_message_from_template,
)

_MOD = "agentic_devtools.cli.git.commit_template"


class TestResolveCommitMessageFromTemplate:
    """Tests for resolve_commit_message_from_template."""

    def test_returns_rendered_message(self, tmp_path):
        """Returns rendered commit message on success."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("feat({{ issueKey }}): {{ commitMessageTitle }}", encoding="utf-8")
        ctx = {"issueKey": "42", "commitMessageTitle": "add feature"}
        with patch(f"{_MOD}._build_render_context", return_value=ctx):
            result = resolve_commit_message_from_template(tmp_path)
        assert result == "feat(42): add feature"

    def test_returns_none_when_no_template(self, tmp_path):
        """Returns None when template file does not exist (FR-005 fallback)."""
        result = resolve_commit_message_from_template(tmp_path)
        assert result is None

    def test_returns_none_for_syntax_error(self, tmp_path, capsys):
        """Returns None when template has syntax error (FR-007 fallback)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("{% if x %}", encoding="utf-8")
        result = resolve_commit_message_from_template(tmp_path)
        assert result is None

    def test_returns_none_when_rendered_empty(self, tmp_path, capsys):
        """Returns None when template renders to empty string."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("{{ missing }}", encoding="utf-8")
        with patch(f"{_MOD}._build_render_context", return_value={}):
            # Missing variables render as empty string with jinja2.Undefined
            result = resolve_commit_message_from_template(tmp_path)
        assert result is None

    @patch(f"{_MOD}._discover_git_root", return_value=None)
    def test_returns_none_when_not_in_git_repo(self, mock_discover):
        """Returns None when git_root is None and cannot be discovered."""
        result = resolve_commit_message_from_template(None)
        assert result is None

    @patch(f"{_MOD}._discover_git_root")
    def test_discovers_git_root_when_none(self, mock_discover, tmp_path):
        """Discovers git root when not provided."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("{{ issueType }}: msg", encoding="utf-8")
        mock_discover.return_value = tmp_path
        with patch(f"{_MOD}._build_render_context", return_value={"issueType": "feat"}):
            result = resolve_commit_message_from_template(None)
        assert result == "feat: msg"

    def test_strips_trailing_whitespace(self, tmp_path):
        """Strips trailing whitespace from rendered message."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("feat: title   \n\n\n", encoding="utf-8")
        with patch(f"{_MOD}._build_render_context", return_value={}):
            result = resolve_commit_message_from_template(tmp_path)
        assert result == "feat: title"

    def test_undefined_variables_render_empty(self, tmp_path, capsys):
        """Template with undefined variables renders them as empty strings when not hard-required."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        # Use only commitMessageBody (soft-required) as the undefined var so we
        # don't hit the hard-required guard and can verify jinja2.Undefined behaviour.
        template_file.write_text("feat: {{ commitMessageTitle }}\n\n{{ commitMessageBody }}", encoding="utf-8")
        ctx = {"commitMessageTitle": "add feature"}
        with patch(f"{_MOD}._build_render_context", return_value=ctx):
            result = resolve_commit_message_from_template(tmp_path)
        # commitMessageBody is soft-required; rendering proceeds with it empty
        assert result == "feat: add feature"
        # A warning should still be emitted for the unresolved soft-required var
        err = capsys.readouterr().err
        assert "commitMessageBody" in err
        assert "unresolved" in err.lower()

    def test_returns_none_when_hard_required_vars_missing(self, tmp_path, capsys):
        """Returns None when hard-required variables are referenced but unresolved."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text(
            "{{ issueType }}([#{{ issueKey }}]({{ issueLink }})): {{ commitMessageTitle }}",
            encoding="utf-8",
        )
        with patch(f"{_MOD}._build_render_context", return_value={}):
            result = resolve_commit_message_from_template(tmp_path)
        assert result is None
        err = capsys.readouterr().err
        assert "falling back" in err.lower()
        # All four hard-required vars should be mentioned
        for var in ("issueType", "issueKey", "issueLink", "commitMessageTitle"):
            assert var in err

    def test_returns_none_on_render_syntax_error(self, tmp_path, capsys):
        """Returns None when env.from_string raises TemplateSyntaxError."""
        import jinja2

        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("valid content", encoding="utf-8")
        _sandboxed = "jinja2.sandbox.SandboxedEnvironment.from_string"
        with patch(f"{_MOD}._build_render_context", return_value={}):
            with patch(_sandboxed, side_effect=jinja2.TemplateSyntaxError("bad", 1)):
                result = resolve_commit_message_from_template(tmp_path)
        assert result is None
        assert "syntax error" in capsys.readouterr().err

    def test_returns_none_on_undefined_error(self, tmp_path, capsys):
        """Returns None when template render raises UndefinedError."""
        import jinja2

        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("valid content", encoding="utf-8")
        mock_tmpl = type("MockTemplate", (), {"render": staticmethod(lambda **_kw: None)})()
        mock_tmpl.render = lambda _ctx=None, **_kw: (_ for _ in ()).throw(jinja2.UndefinedError("x is undefined"))
        with patch(f"{_MOD}._build_render_context", return_value={}):
            with patch("jinja2.sandbox.SandboxedEnvironment.from_string", return_value=mock_tmpl):
                result = resolve_commit_message_from_template(tmp_path)
        assert result is None
        assert "undefined variable" in capsys.readouterr().err

    def test_returns_none_on_template_runtime_error(self, tmp_path, capsys):
        """Returns None when template render raises TemplateRuntimeError."""
        import jinja2

        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("valid content", encoding="utf-8")
        mock_tmpl = Mock()
        mock_tmpl.render.side_effect = jinja2.TemplateRuntimeError("runtime boom")
        with patch(f"{_MOD}._build_render_context", return_value={}):
            with patch("jinja2.sandbox.SandboxedEnvironment.from_string", return_value=mock_tmpl):
                result = resolve_commit_message_from_template(tmp_path)
        assert result is None
        assert "runtime error" in capsys.readouterr().err

    def test_returns_none_on_unexpected_render_error(self, tmp_path, capsys):
        """Returns None when template rendering raises an unexpected error."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("valid content", encoding="utf-8")
        mock_tmpl = Mock()
        mock_tmpl.render.side_effect = RuntimeError("boom")
        with patch(f"{_MOD}._build_render_context", return_value={}):
            with patch("jinja2.sandbox.SandboxedEnvironment.from_string", return_value=mock_tmpl):
                result = resolve_commit_message_from_template(tmp_path)
        assert result is None
        assert "unexpected commit template rendering error" in capsys.readouterr().err.lower()
