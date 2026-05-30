"""Tests for _normalize_path_for_comparison function."""

from typing import cast


class TestNormalizePathForComparison:
    """Tests for _normalize_path_for_comparison."""

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty string.

        Covers line 290 (falsy path early return).
        """
        from agentic_devtools.cli.azure_devops.review_commands import (
            _normalize_path_for_comparison,
        )

        assert _normalize_path_for_comparison("") == ""

    def test_none_returns_empty(self):
        """Test None returns empty string.

        Covers line 290 (falsy path early return).
        """
        from agentic_devtools.cli.azure_devops.review_commands import (
            _normalize_path_for_comparison,
        )

        assert _normalize_path_for_comparison(cast(str, None)) == ""

    def test_strips_leading_slash(self):
        """Test strips leading slash."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            _normalize_path_for_comparison,
        )

        assert _normalize_path_for_comparison("/src/file.ts") == "src/file.ts"

    def test_normalizes_backslashes(self):
        """Test normalizes backslashes to forward slashes."""
        from agentic_devtools.cli.azure_devops.review_commands import (
            _normalize_path_for_comparison,
        )

        assert _normalize_path_for_comparison("src\\file.ts") == "src/file.ts"
