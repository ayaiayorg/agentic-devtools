"""
Tests for prompt template loader.
"""

from agdt_ai_helpers.prompts import loader


class TestSubstituteVariables:
    """Tests for substitute_variables function."""

    def test_substitute_single_variable(self):
        """Test substituting a single variable."""
        template = "Hello {{name}}"
        result = loader.substitute_variables(template, {"name": "World"})
        assert result == "Hello World"

    def test_substitute_multiple_variables(self):
        """Test substituting multiple variables."""
        template = "Issue {{key}} in {{project}}"
        result = loader.substitute_variables(template, {"key": "DFLY-1234", "project": "Dragonfly"})
        assert result == "Issue DFLY-1234 in Dragonfly"

    def test_substitute_duplicate_variable(self):
        """Test substituting a variable that appears multiple times."""
        template = "{{name}} says hello, {{name}} waves goodbye"
        result = loader.substitute_variables(template, {"name": "Alice"})
        assert result == "Alice says hello, Alice waves goodbye"

    def test_substitute_missing_variable_becomes_empty(self):
        """Test that missing variables render as empty strings."""
        template = "Hello {{name}}"
        result = loader.substitute_variables(template, {})
        # With Jinja2's SilentUndefined, missing variables render as empty strings
        assert result == "Hello "

    def test_substitute_preserves_extra_context(self):
        """Test that extra context keys don't affect substitution."""
        template = "Hello {{name}}"
        result = loader.substitute_variables(template, {"name": "World", "unused": "value"})
        assert result == "Hello World"

    def test_conditional_with_truthy_variable(self):
        """Test that {% if %} blocks are included when variable is truthy."""
        template = "Start{% if jira_key %} - Issue: {{jira_key}}{% endif %} End"
        result = loader.substitute_variables(template, {"jira_key": "DFLY-1234"})
        assert result == "Start - Issue: DFLY-1234 End"

    def test_conditional_with_falsy_empty_string(self):
        """Test that {% if %} blocks are removed when variable is empty string."""
        template = "Start{% if jira_key %} - Issue: {{jira_key}}{% endif %} End"
        result = loader.substitute_variables(template, {"jira_key": ""})
        assert result == "Start End"

    def test_conditional_with_missing_variable(self):
        """Test that {% if %} blocks are removed when variable is missing."""
        template = "Start{% if jira_key %} - Issue: {{jira_key}}{% endif %} End"
        result = loader.substitute_variables(template, {})
        assert result == "Start End"

    def test_conditional_multiline_content(self):
        """Test that {% if %} blocks work with multiline content."""
        template = """Header
{% if show_details %}
- Detail 1
- Detail 2: {{value}}
{% endif %}
Footer"""
        result = loader.substitute_variables(template, {"show_details": True, "value": "test"})
        assert "Detail 1" in result
        assert "Detail 2: test" in result

    def test_conditional_multiline_removed_when_falsy(self):
        """Test that multiline {% if %} blocks are removed when variable is falsy."""
        template = """Header
{% if show_details %}
- Detail 1
- Detail 2: {{value}}
{% endif %}
Footer"""
        result = loader.substitute_variables(template, {"show_details": False, "value": "test"})
        assert "Detail" not in result
        assert "Header" in result
        assert "Footer" in result
