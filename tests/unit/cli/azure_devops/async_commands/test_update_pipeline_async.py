"""Tests for update_pipeline_async function."""

from agentic_devtools.cli.azure_devops.async_commands import update_pipeline_async


class TestUpdatePipelineAsync:
    """Tests for update_pipeline_async function."""

    def test_function_exists(self):
        """Verify update_pipeline_async is importable and callable."""
        assert callable(update_pipeline_async)
