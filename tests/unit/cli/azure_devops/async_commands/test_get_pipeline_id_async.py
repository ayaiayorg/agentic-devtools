"""Tests for get_pipeline_id_async function."""

from agentic_devtools.cli.azure_devops.async_commands import get_pipeline_id_async


class TestGetPipelineIdAsync:
    """Tests for get_pipeline_id_async function."""

    def test_function_exists(self):
        """Verify get_pipeline_id_async is importable and callable."""
        assert callable(get_pipeline_id_async)
