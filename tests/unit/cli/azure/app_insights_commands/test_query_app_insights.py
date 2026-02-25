"""Tests for query_app_insights function."""

from agentic_devtools.cli.azure.app_insights_commands import query_app_insights


class TestQueryAppInsights:
    """Tests for query_app_insights function."""

    def test_function_exists(self):
        """Verify query_app_insights is importable and callable."""
        assert callable(query_app_insights)
