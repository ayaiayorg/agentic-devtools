"""Tests for generate_review_prompts_async function."""

from agentic_devtools.cli.azure_devops.async_commands import generate_review_prompts_async


class TestGenerateReviewPromptsAsync:
    """Tests for generate_review_prompts_async function."""

    def test_function_exists(self):
        """Verify generate_review_prompts_async is importable and callable."""
        assert callable(generate_review_prompts_async)
