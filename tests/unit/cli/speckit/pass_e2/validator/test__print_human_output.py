"""Tests for pass_e2.validator — _print_human_output."""

from agentic_devtools.cli.speckit.pass_e2.models import (
    FRCoverage,
    FRInfo,
)
from agentic_devtools.cli.speckit.pass_e2.models import (
    TestCoverageFinding as _TestCoverageFinding,
)
from agentic_devtools.cli.speckit.pass_e2.models import (
    TestCoverageResult as _TestCoverageResult,
)
from agentic_devtools.cli.speckit.pass_e2.models import (
    TestTask as _TestTask,
)
from agentic_devtools.cli.speckit.pass_e2.validator import _print_human_output


class TestPrintHumanOutput:
    """Verify human-readable output rendering."""

    def test_no_coverage_no_findings(self, capsys) -> None:
        """Empty result produces 'no findings' message."""
        result = _TestCoverageResult(findings=[], coverage={})
        _print_human_output(result)
        output = capsys.readouterr().out
        assert "No FRs found or no findings generated." in output

    def test_with_findings(self, capsys) -> None:
        """Findings are printed with severity and key."""
        result = _TestCoverageResult(
            findings=[
                _TestCoverageFinding(
                    key="FR-001:no-test-task",
                    severity="HIGH",
                    description="FR-001 has no associated test task.",
                )
            ],
            coverage={
                "FR-001": FRCoverage(
                    fr_info=FRInfo(fr_id="FR-001", priority=2),
                )
            },
        )
        _print_human_output(result)
        output = capsys.readouterr().out
        assert "[HIGH]" in output
        assert "FR-001:no-test-task" in output
        assert "1 finding(s) detected" in output

    def test_all_covered_no_findings(self, capsys) -> None:
        """All FRs covered prints success message."""
        task = _TestTask(task_id="T001", description="Test FR-001", test_types=["happy-path"])
        result = _TestCoverageResult(
            findings=[],
            coverage={
                "FR-001": FRCoverage(
                    fr_info=FRInfo(fr_id="FR-001", priority=1),
                    test_tasks=[task],
                    test_types=["happy-path"],
                    has_happy_path=True,
                )
            },
            summary_table="| FR | Status |\n|---|---|\n| FR-001 | Covered |",
        )
        _print_human_output(result)
        output = capsys.readouterr().out
        assert "All FRs have associated test tasks" in output
        assert "FR-001" in output

    def test_with_finding_recommendation(self, capsys) -> None:
        """Finding with a recommendation prints the recommendation line."""
        result = _TestCoverageResult(
            findings=[
                _TestCoverageFinding(
                    key="FR-001:no-test-task",
                    severity="HIGH",
                    description="FR-001 has no associated test task.",
                    recommendation="Add a test task referencing FR-001.",
                )
            ],
            coverage={
                "FR-001": FRCoverage(
                    fr_info=FRInfo(fr_id="FR-001", priority=2),
                )
            },
        )
        _print_human_output(result)
        output = capsys.readouterr().out
        assert "Add a test task referencing FR-001." in output

    def test_with_summary_table(self, capsys) -> None:
        """Summary table is printed when available."""
        result = _TestCoverageResult(
            findings=[
                _TestCoverageFinding(
                    key="FR-001:no-test-task",
                    severity="HIGH",
                    description="Missing test.",
                )
            ],
            coverage={
                "FR-001": FRCoverage(
                    fr_info=FRInfo(fr_id="FR-001", priority=2),
                )
            },
            summary_table="SUMMARY TABLE CONTENT",
        )
        _print_human_output(result)
        output = capsys.readouterr().out
        assert "SUMMARY TABLE CONTENT" in output
