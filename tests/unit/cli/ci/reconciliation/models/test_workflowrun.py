"""Tests for WorkflowRun dataclass."""

from agentic_devtools.cli.ci.reconciliation.models import WorkflowRun


class TestWorkflowRun:
    """Tests for WorkflowRun dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """WorkflowRun can be created with all required fields."""
        run = WorkflowRun(
            id=123,
            name="CI Build",
            conclusion="failure",
            run_attempt=1,
            created_at="2024-01-15T10:00:00Z",
            event="push",
            head_branch="main",
        )
        assert run.id == 123
        assert run.name == "CI Build"
        assert run.conclusion == "failure"
        assert run.run_attempt == 1
        assert run.created_at == "2024-01-15T10:00:00Z"
        assert run.event == "push"
        assert run.head_branch == "main"

    def test_optional_fields_default_to_empty(self) -> None:
        """Optional fields default to empty strings."""
        run = WorkflowRun(
            id=1,
            name="test",
            conclusion="success",
            run_attempt=1,
            created_at="2024-01-01T00:00:00Z",
            event="push",
            head_branch="main",
        )
        assert run.html_url == ""
        assert run.triggering_actor == ""
        assert run.repository_full_name == ""

    def test_frozen(self) -> None:
        """WorkflowRun is immutable."""
        run = WorkflowRun(
            id=1,
            name="test",
            conclusion="success",
            run_attempt=1,
            created_at="2024-01-01T00:00:00Z",
            event="push",
            head_branch="main",
        )
        import pytest

        with pytest.raises(AttributeError):
            run.id = 999  # type: ignore[misc]
