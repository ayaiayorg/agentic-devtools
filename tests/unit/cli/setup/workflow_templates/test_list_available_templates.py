"""Tests for agentic_devtools.cli.setup.workflow_templates.list_available_templates."""

from agentic_devtools.cli.setup.workflow_templates import TemplateInfo, list_available_templates


class TestListAvailableTemplates:
    """Tests for the list_available_templates function."""

    def test_returns_a_list(self):
        """Return type is list, not tuple."""
        result = list_available_templates()
        assert isinstance(result, list)

    def test_length_is_three(self):
        """Exactly three bundled templates are available."""
        assert len(list_available_templates()) == 3

    def test_entries_are_template_info(self):
        """Every entry is a TemplateInfo instance."""
        for entry in list_available_templates():
            assert isinstance(entry, TemplateInfo)

    def test_expected_filenames(self):
        """The expected filenames are present."""
        filenames = {t.filename for t in list_available_templates()}
        assert filenames == {"work-on-issue.py", "review-pr.py", "README.md"}

    def test_returns_new_list(self):
        """Mutating the returned list does not affect subsequent calls."""
        first = list_available_templates()
        first.clear()
        second = list_available_templates()
        assert len(second) == 3
