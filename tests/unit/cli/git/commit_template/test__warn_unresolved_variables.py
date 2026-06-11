"""Tests for _warn_unresolved_variables."""

from agentic_devtools.cli.git.commit_template import _warn_unresolved_variables


class TestWarnUnresolvedVariables:
    """Tests for _warn_unresolved_variables."""

    def test_no_warnings_when_all_resolved(self, capsys):
        """No warnings emitted when all template variables are in context."""
        context = {"issueType": "feat", "issueKey": "42"}
        template = "{{ issueType }}: {{ issueKey }}"
        _warn_unresolved_variables(context, template)
        assert capsys.readouterr().err == ""

    def test_warns_for_single_unresolved(self, capsys):
        """Emits warning for a single unresolved variable."""
        context = {"issueType": "feat"}
        template = "{{ issueType }}: {{ issueKey }}"
        _warn_unresolved_variables(context, template)
        err = capsys.readouterr().err
        assert "issueKey" in err
        assert "unresolved" in err

    def test_warns_for_multiple_unresolved(self, capsys):
        """Emits one warning per unresolved variable, sorted alphabetically."""
        context = {}
        template = "{{ issueType }}({{ issueKey }}): {{ commitMessageTitle }}"
        _warn_unresolved_variables(context, template)
        err = capsys.readouterr().err
        lines = [line for line in err.strip().split("\n") if line.strip()]
        assert len(lines) == 3
        # Sorted alphabetically
        assert "commitMessageTitle" in lines[0]
        assert "issueKey" in lines[1]
        assert "issueType" in lines[2]

    def test_handles_syntax_error_gracefully(self, capsys):
        """Does not crash on template with syntax errors."""
        context = {"issueKey": "42"}
        template = "{% if x %}"  # invalid template
        _warn_unresolved_variables(context, template)
        # Should not raise and should not emit warnings
        assert capsys.readouterr().err == ""

    def test_detects_variables_in_filters(self, capsys):
        """Detects variables used with Jinja2 filters."""
        context = {}
        template = "{{ issueKey | upper }}"
        _warn_unresolved_variables(context, template)
        err = capsys.readouterr().err
        assert "issueKey" in err

    def test_warnings_go_to_stderr(self, capsys):
        """Warnings are emitted to stderr, not stdout."""
        context = {}
        template = "{{ issueKey }}"
        _warn_unresolved_variables(context, template)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "issueKey" in captured.err

    def test_no_warnings_for_jinja2_builtin_globals(self, capsys):
        """No warnings for Jinja2 built-in globals like range, dict, cycler."""
        context = {}
        # range, dict, cycler, namespace are all Jinja2 env.globals
        template = "{% for i in range(3) %}{{ i }}{% endfor %}"
        _warn_unresolved_variables(context, template)
        assert capsys.readouterr().err == ""
