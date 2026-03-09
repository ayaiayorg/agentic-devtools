"""Tests for _print_dispatch_plan."""

from agentic_devtools.cli.azure_devops.review_config import (
    ConsensusConfig,
    ConsolidationConfig,
    FileFilterConfig,
    ReviewConfig,
    ReviewerConfig,
)
from agentic_devtools.cli.review.dispatch import _print_dispatch_plan


class TestPrintDispatchPlan:
    """Tests for _print_dispatch_plan."""

    def test_prints_plan_with_consolidation(self, capsys):
        """Plan shows consolidator info when configured."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
            ],
            consolidation=ConsolidationConfig(model_id="claude-opus-4-6"),
            consensus=ConsensusConfig(strategy="majority"),
        )
        _print_dispatch_plan(config, 123, "ai-review")
        captured = capsys.readouterr()
        assert "Consolidator: claude-opus-4-6" in captured.out

    def test_prints_plan_skip_consolidation(self, capsys):
        """Plan shows skip note when consolidation is skipped."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
            ],
            skip_consolidation=True,
        )
        _print_dispatch_plan(config, 123, "ai-review")
        captured = capsys.readouterr()
        assert "SKIPPED" in captured.out

    def test_prints_plan_no_consolidation_configured(self, capsys):
        """Plan shows 'not configured' when no consolidation."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
            ],
        )
        _print_dispatch_plan(config, 123, "ai-review")
        captured = capsys.readouterr()
        assert "not configured" in captured.out

    def test_prints_file_filters(self, capsys):
        """Plan shows include/exclude patterns when present."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
            ],
            file_filters=FileFilterConfig(
                include=["src/**"],
                exclude=["**/*.test.ts"],
            ),
        )
        _print_dispatch_plan(config, 123, "ai-review")
        captured = capsys.readouterr()
        assert "Include patterns:" in captured.out
        assert "Exclude patterns:" in captured.out
