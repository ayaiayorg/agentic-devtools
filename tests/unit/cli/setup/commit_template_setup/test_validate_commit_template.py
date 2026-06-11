"""Tests for validate_commit_template."""

from agentic_devtools.cli.git.commit_template import TEMPLATE_PATH
from agentic_devtools.cli.setup.commit_template_setup import (
    DEFAULT_TEMPLATE,
    validate_commit_template,
)


class TestValidateCommitTemplate:
    """Tests for validate_commit_template."""

    def test_valid_template_no_warnings(self, tmp_path):
        """No warnings when all required variables are present (FR-006)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text(DEFAULT_TEMPLATE, encoding="utf-8")
        warnings = validate_commit_template(tmp_path)
        assert warnings == []

    def test_missing_variable_warns(self, tmp_path):
        """Warns when a required variable is missing from template (FR-006)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        # Template missing issueLink
        content = "{{ issueType }}({{ issueKey }}): {{ commitMessageTitle }}\n{{ commitMessageBody }}"
        template_file.write_text(content, encoding="utf-8")
        warnings = validate_commit_template(tmp_path)
        assert len(warnings) == 1
        assert "issueLink" in warnings[0]

    def test_extra_variables_no_error(self, tmp_path):
        """Extra custom variables do not produce errors (FR-006)."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        # All required + extra
        content = DEFAULT_TEMPLATE + "\n{{ customVar }}"
        template_file.write_text(content, encoding="utf-8")
        warnings = validate_commit_template(tmp_path)
        assert warnings == []

    def test_returns_empty_when_no_file(self, tmp_path):
        """Returns empty list when template file does not exist."""
        warnings = validate_commit_template(tmp_path)
        assert warnings == []

    def test_empty_file_warns(self, tmp_path):
        """Warns when template file is empty."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("", encoding="utf-8")
        warnings = validate_commit_template(tmp_path)
        assert len(warnings) == 1
        assert "empty" in warnings[0]

    def test_syntax_error_warns(self, tmp_path):
        """Warns when template has Jinja2 syntax error."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("{% if x %}", encoding="utf-8")
        warnings = validate_commit_template(tmp_path)
        assert len(warnings) == 1
        assert "syntax error" in warnings[0]

    def test_multiple_missing_variables(self, tmp_path):
        """Reports all missing required variables."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        # Only has issueKey
        template_file.write_text("{{ issueKey }}", encoding="utf-8")
        warnings = validate_commit_template(tmp_path)
        # Should warn about issueType, issueLink, commitMessageTitle, commitMessageBody
        assert len(warnings) == 4

    def test_read_error_warns(self, tmp_path):
        """Returns warning when file cannot be read."""
        template_file = tmp_path / TEMPLATE_PATH
        template_file.parent.mkdir(parents=True)
        template_file.write_text("content", encoding="utf-8")
        template_file.chmod(0o000)
        try:
            warnings = validate_commit_template(tmp_path)
            assert len(warnings) == 1
            assert "Cannot read" in warnings[0]
        finally:
            template_file.chmod(0o644)
