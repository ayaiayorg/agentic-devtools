"""Tests for _check_files_need_consolidation stub."""

from agentic_devtools.cli.review.dispatch import _check_files_need_consolidation


class TestCheckFilesNeedConsolidation:
    """Tests for _check_files_need_consolidation stub."""

    def test_returns_empty_list(self):
        """Stub returns empty list."""
        result = _check_files_need_consolidation(pr_id=123)
        assert result == []
