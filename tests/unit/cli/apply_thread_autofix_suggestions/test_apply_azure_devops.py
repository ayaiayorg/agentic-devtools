"""Tests for _apply_azure_devops."""

from agentic_devtools.cli.apply_thread_autofix_suggestions import _apply_azure_devops


class TestApplyAzureDevOps:
    """Tests for Azure DevOps dispatch (stub)."""

    def test_returns_not_implemented(self) -> None:
        result = _apply_azure_devops(
            pr_number=1,
            repo="project/repo",
            comment_ids=None,
            message="test",
            resolve=True,
        )
        assert result["applied"] == 0
        assert "error" in result
