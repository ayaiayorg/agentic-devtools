"""Tests for create_pipeline_async function."""

from agentic_devtools.cli.azure_devops.async_commands import create_pipeline_async


class TestCreatePipelineAsync:
    """Tests for create_pipeline_async function."""

    def test_function_exists(self):
        """Verify create_pipeline_async is importable and callable."""
        assert callable(create_pipeline_async)
