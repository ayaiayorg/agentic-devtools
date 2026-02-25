"""Tests for query_app_insights_async function."""

from agentic_devtools.cli.azure.app_insights_commands import query_app_insights_async


class TestQueryAppInsightsAsync:
    """Tests for query_app_insights_async function."""

    def test_function_exists(self):
        """Verify query_app_insights_async is importable and callable."""
        assert callable(query_app_insights_async)
