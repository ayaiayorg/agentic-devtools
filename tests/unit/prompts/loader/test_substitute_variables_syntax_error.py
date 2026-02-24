"""Tests for substitute_variables() TemplateSyntaxError fallback."""

from agentic_devtools.prompts.loader import substitute_variables


def test_malformed_template_falls_back_to_regex():
    """A template with invalid Jinja2 syntax falls back to regex substitution."""
    # {% with no closing tag makes Jinja2 raise TemplateSyntaxError
    template = "Hello {{name}} {% if unclosed"
    result = substitute_variables(template, {"name": "World"})
    assert "World" in result
