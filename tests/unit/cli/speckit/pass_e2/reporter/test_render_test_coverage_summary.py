"""Tests for pass_e2.reporter — render_test_coverage_summary."""

from agentic_devtools.cli.speckit.pass_e2.models import FRCoverage, FRInfo
from agentic_devtools.cli.speckit.pass_e2.models import TestTask as _TestTask
from agentic_devtools.cli.speckit.pass_e2.reporter import render_test_coverage_summary


class TestRenderTestCoverageSummary:
    """Verify FR-007 Test Coverage Summary table rendering."""

    def test_renders_table_with_covered_fr(self) -> None:
        coverage = {
            "FR-001": FRCoverage(
                fr_info=FRInfo(fr_id="FR-001", priority=1, user_story=1),
                test_tasks=[_TestTask(task_id="T002", description="test")],
                test_types=["happy-path"],
                has_happy_path=True,
            ),
        }
        table = render_test_coverage_summary(coverage)
        assert "FR-001" in table
        assert "US1" in table
        assert "T002" in table
        assert "happy-path" in table
        assert "✅ Covered" in table

    def test_renders_table_with_uncovered_fr(self) -> None:
        coverage = {
            "FR-002": FRCoverage(
                fr_info=FRInfo(fr_id="FR-002", priority=2, user_story=None),
                test_tasks=[],
                test_types=[],
            ),
        }
        table = render_test_coverage_summary(coverage)
        assert "FR-002" in table
        assert "N/A" in table
        assert "None" in table
        assert "❌ Missing" in table

    def test_table_has_header(self) -> None:
        coverage = {
            "FR-001": FRCoverage(
                fr_info=FRInfo(fr_id="FR-001", priority=1, user_story=1),
                test_tasks=[],
                test_types=[],
            ),
        }
        table = render_test_coverage_summary(coverage)
        assert "Test Coverage Summary" in table
        assert "| FR |" in table
