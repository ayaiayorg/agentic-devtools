"""Tests for list_pipelines_async function."""

from agentic_devtools.cli.azure_devops.async_commands import list_pipelines_async


class TestListPipelinesAsync:
    """Tests for list_pipelines_async function."""

    def test_function_exists(self):
        """Verify list_pipelines_async is importable and callable."""
        assert callable(list_pipelines_async)
