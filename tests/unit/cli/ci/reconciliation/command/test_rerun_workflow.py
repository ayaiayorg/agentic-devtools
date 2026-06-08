"""Tests for CIPlatformProvider.rerun_workflow() default behavior."""

import pytest

from agentic_devtools.cli.ci.ado_provider import AzureDevOpsProvider


class TestRerunWorkflowDefault:
    """Tests for CIPlatformProvider.rerun_workflow() raising NotImplementedError."""

    def test_ado_provider_raises_not_implemented(self) -> None:
        """AzureDevOpsProvider inherits default NotImplementedError."""
        provider = AzureDevOpsProvider()
        with pytest.raises(NotImplementedError, match="rerun_workflow"):
            provider.rerun_workflow(run_id=12345)
