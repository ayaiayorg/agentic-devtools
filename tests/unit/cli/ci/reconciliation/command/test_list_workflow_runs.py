"""Tests for CIPlatformProvider.list_workflow_runs() default behavior."""

import pytest

from agentic_devtools.cli.ci.ado_provider import AzureDevOpsProvider


class TestListWorkflowRunsDefault:
    """Tests for CIPlatformProvider.list_workflow_runs() raising NotImplementedError."""

    def test_ado_provider_raises_not_implemented(self) -> None:
        """AzureDevOpsProvider inherits default NotImplementedError."""
        provider = AzureDevOpsProvider()
        with pytest.raises(NotImplementedError, match="list_workflow_runs"):
            provider.list_workflow_runs(workflow_id="ci.yml")

    def test_ado_provider_with_window_hours(self) -> None:
        """AzureDevOpsProvider raises even with window_hours parameter."""
        provider = AzureDevOpsProvider()
        with pytest.raises(NotImplementedError):
            provider.list_workflow_runs(workflow_id="ci.yml", window_hours=48)
