"""
Tests for prompt template loader.
"""

from agdt_ai_helpers.prompts import loader


class TestGetRequiredVariables:
    """Tests for get_required_variables function."""

    def test_extract_single_variable(self):
        """Test extracting a single variable."""
        template = "Hello {{name}}"
        variables = loader.get_required_variables(template)
        assert variables == {"name"}

    def test_extract_multiple_variables(self):
        """Test extracting multiple variables."""
        template = "Issue {{jira_issue_key}} in project {{project_name}}"
        variables = loader.get_required_variables(template)
        assert variables == {"jira_issue_key", "project_name"}

    def test_no_variables(self):
        """Test template with no variables."""
        template = "This is plain text"
        variables = loader.get_required_variables(template)
        assert variables == set()

    def test_duplicate_variables(self):
        """Test that duplicate variables are deduplicated."""
        template = "{{name}} and {{name}} again"
        variables = loader.get_required_variables(template)
        assert variables == {"name"}

    def test_complex_variable_names(self):
        """Test variables with underscores."""
        template = "{{pull_request_id}} and {{jira_issue_key}}"
        variables = loader.get_required_variables(template)
        assert variables == {"pull_request_id", "jira_issue_key"}
