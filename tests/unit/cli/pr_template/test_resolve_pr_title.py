"""Tests for agentic_devtools.cli.pr_template.resolve_pr_title."""

from unittest.mock import patch

from agentic_devtools.cli import pr_template

# The resolve functions are imported inside resolve_pr_title from git.commit_template
_COMMIT_TEMPLATE_MOD = "agentic_devtools.cli.git.commit_template"


class TestResolvePrTitle:
    """Tests for resolve_pr_title()."""

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_commit_title")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_type")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_key")
    def test_renders_title_from_template(self, mock_key, mock_type, mock_title, mock_path, tmp_path):
        """Happy path: renders title from template with all variables."""
        template_file = tmp_path / "pr-title-template.j2"
        template_file.write_text("{{ issueType }}({{ issueKey }}): {{ commitMessageTitle }}\n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_key.return_value = ("DFLY-3029", "DFLY-3029")
        mock_type.return_value = "feature"
        mock_title.return_value = "Add admin E2E pipeline integration"

        result = pr_template.resolve_pr_title()
        assert result == "feature(DFLY-3029): Add admin E2E pipeline integration"

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    def test_returns_none_when_template_missing(self, mock_path, tmp_path):
        """Returns None when template file does not exist."""
        mock_path.return_value = tmp_path / "nonexistent.j2"

        result = pr_template.resolve_pr_title()
        assert result is None

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_commit_title")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_type")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_key")
    def test_returns_none_when_issue_key_missing(self, mock_key, mock_type, mock_title, mock_path, tmp_path):
        """Returns None when issueKey cannot be resolved."""
        template_file = tmp_path / "pr-title-template.j2"
        template_file.write_text("{{ issueType }}({{ issueKey }}): {{ commitMessageTitle }}\n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_key.return_value = (None, None)
        mock_type.return_value = "feat"
        mock_title.return_value = "some title"

        result = pr_template.resolve_pr_title()
        assert result is None

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_commit_title")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_type")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_key")
    def test_returns_none_when_issue_type_missing(self, mock_key, mock_type, mock_title, mock_path, tmp_path):
        """Returns None when issueType cannot be resolved."""
        template_file = tmp_path / "pr-title-template.j2"
        template_file.write_text("{{ issueType }}({{ issueKey }}): {{ commitMessageTitle }}\n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_key.return_value = ("PROJ-123", "PROJ-123")
        mock_type.return_value = None
        mock_title.return_value = "some title"

        result = pr_template.resolve_pr_title()
        assert result is None

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_commit_title")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_type")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_key")
    def test_returns_none_when_commit_title_missing(self, mock_key, mock_type, mock_title, mock_path, tmp_path):
        """Returns None when commitMessageTitle cannot be resolved."""
        template_file = tmp_path / "pr-title-template.j2"
        template_file.write_text("{{ issueType }}({{ issueKey }}): {{ commitMessageTitle }}\n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_key.return_value = ("PROJ-123", "PROJ-123")
        mock_type.return_value = "feat"
        mock_title.return_value = None

        result = pr_template.resolve_pr_title()
        assert result is None

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_commit_title")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_type")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_key")
    def test_renders_when_unused_variable_unresolvable(self, mock_key, mock_type, mock_title, mock_path, tmp_path):
        """Renders successfully when a template variable can't be resolved but isn't referenced."""
        template_file = tmp_path / "pr-title-template.j2"
        # Template does not reference issueType — so issueType=None should not cause a failure
        template_file.write_text("{{ issueKey }}: {{ commitMessageTitle }}\n", encoding="utf-8")
        mock_path.return_value = template_file
        mock_key.return_value = ("PROJ-123", "PROJ-123")
        mock_type.return_value = None  # Can't be resolved, but template doesn't use it
        mock_title.return_value = "my commit title"

        result = pr_template.resolve_pr_title()
        assert result == "PROJ-123: my commit title"

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    def test_returns_none_when_template_empty(self, mock_path, tmp_path):
        """Returns None when template is empty."""
        template_file = tmp_path / "pr-title-template.j2"
        template_file.write_text("", encoding="utf-8")
        mock_path.return_value = template_file

        result = pr_template.resolve_pr_title()
        assert result is None

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    def test_returns_none_on_read_error(self, mock_path, tmp_path, capsys):
        """Returns None and warns when template cannot be read."""
        from unittest.mock import MagicMock

        mock_template = MagicMock()
        mock_template.exists.return_value = True
        mock_template.read_text.side_effect = OSError("permission denied")
        mock_path.return_value = mock_template

        result = pr_template.resolve_pr_title()
        assert result is None
        captured = capsys.readouterr()
        assert "Cannot read PR title template" in captured.err

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_commit_title")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_type")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_key")
    def test_returns_none_on_syntax_error(self, mock_key, mock_type, mock_title, mock_path, tmp_path, capsys):
        """Returns None and warns on Jinja2 syntax error."""
        template_file = tmp_path / "pr-title-template.j2"
        template_file.write_text("{{ unclosed", encoding="utf-8")
        mock_path.return_value = template_file
        mock_key.return_value = ("PROJ-123", "PROJ-123")
        mock_type.return_value = "feat"
        mock_title.return_value = "title"

        result = pr_template.resolve_pr_title()
        assert result is None
        captured = capsys.readouterr()
        assert "PR title template rendering failed" in captured.err

    @patch("agentic_devtools.cli.pr_template.get_pr_title_template_path")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_commit_title")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_type")
    @patch(f"{_COMMIT_TEMPLATE_MOD}._resolve_issue_key")
    def test_returns_none_when_rendered_empty(self, mock_key, mock_type, mock_title, mock_path, tmp_path):
        """Returns None when template renders to whitespace-only."""
        template_file = tmp_path / "pr-title-template.j2"
        # Template with Jinja2 that renders to empty
        template_file.write_text("{% if false %}content{% endif %}", encoding="utf-8")
        mock_path.return_value = template_file
        mock_key.return_value = ("PROJ-123", "PROJ-123")
        mock_type.return_value = "feat"
        mock_title.return_value = "title"

        result = pr_template.resolve_pr_title()
        assert result is None
