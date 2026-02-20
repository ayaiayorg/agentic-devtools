"""Tests for get_prompts_output_dir function."""


class TestGetPromptsOutputDir:
    """Tests for get_prompts_output_dir function."""

    def test_returns_path_to_temp_pr_review_prompts(self):
        """Test that the function returns the correct path."""
        from agentic_devtools.cli.azure_devops.review_prompts import (
            get_prompts_output_dir,
        )

        result = get_prompts_output_dir()
        assert result.name == "pr-review-prompts"
        assert result.parent.name == "temp"
