"""Tests for PipelineRunSummary dataclass."""

from agentic_devtools.cli.ci.pipeline.models import (
    ActionDecision,
    ActionResult,
    PipelineRunSummary,
)
from agentic_devtools.cli.ci.pipeline.snapshot import PRStateSnapshot


class TestPipelineRunSummary:
    """Tests for PipelineRunSummary construction and fields."""

    def test_default_construction(self) -> None:
        summary = PipelineRunSummary()
        assert summary.results == []
        assert summary.snapshot is None
        assert summary.run_url == ""
        assert summary.timestamp == ""
        assert summary.trigger_reason == ""

    def test_full_construction(self) -> None:
        snapshot = PRStateSnapshot(pr_number=42, head_sha="abc123")
        result = ActionResult(name="guards", decision=ActionDecision.EXECUTE)
        summary = PipelineRunSummary(
            results=[result],
            snapshot=snapshot,
            run_url="https://github.com/org/repo/actions/runs/123",
            timestamp="2024-01-01T00:00:00Z",
            trigger_reason="ci_completion",
        )
        assert len(summary.results) == 1
        assert summary.snapshot is not None
        assert summary.snapshot.pr_number == 42
        assert summary.run_url.endswith("/123")
        assert summary.trigger_reason == "ci_completion"
