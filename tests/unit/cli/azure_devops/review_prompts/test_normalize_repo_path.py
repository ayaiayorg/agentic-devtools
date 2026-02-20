"""
Tests for review_prompts module.
"""


class TestNormalizeRepoPath:
    """Tests for normalize_repo_path function."""

    def test_returns_none_for_empty_path(self):
        """Test that empty paths return None."""
        from agentic_devtools.cli.azure_devops.review_helpers import normalize_repo_path

        assert normalize_repo_path("") is None
        assert normalize_repo_path("   ") is None
        assert normalize_repo_path("/") is None
        assert normalize_repo_path("  /  ") is None
