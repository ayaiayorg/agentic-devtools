"""
Tests for prompt template loader.
"""

from agdt_ai_helpers.prompts import loader


class TestGetTemplatePath:
    """Tests for get_template_path function."""

    def test_default_template_path(self, temp_prompts_dir):
        """Test generating default template path."""
        path = loader.get_template_path("pull-request-review", "initiate")
        assert path.parent.name == "pull-request-review"
        assert path.name == "default-initiate-prompt.md"

    def test_override_template_path(self, temp_prompts_dir):
        """Test generating override template path."""
        path = loader.get_template_path("pull-request-review", "initiate", is_default=False)
        assert path.parent.name == "pull-request-review"
        assert path.name == "initiate-prompt.md"

    def test_step_template_path(self, temp_prompts_dir):
        """Test generating step template path."""
        path = loader.get_template_path("work-on-jira-issue", "planning")
        assert path.parent.name == "work-on-jira-issue"
        assert path.name == "default-planning-prompt.md"
