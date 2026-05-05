"""Tests for pass_e2.reporter — render_findings."""

from agentic_devtools.cli.speckit.pass_e2.models import TestCoverageFinding as _TestCoverageFinding
from agentic_devtools.cli.speckit.pass_e2.reporter import render_findings


class TestRenderFindings:
    """Verify FR-008 findings rendering."""

    def test_renders_fr_scoped_finding(self) -> None:
        findings = [
            _TestCoverageFinding(
                key="FR-001:no-happy-path",
                severity="CRITICAL",
                fr_id="FR-001",
                description="FR-001 (P1) has no happy-path test.",
                recommendation="Add a happy-path test task for FR-001.",
            )
        ]
        output = render_findings(findings)
        assert "CRITICAL" in output
        assert "FR-001:no-happy-path" in output
        assert "Add a happy-path test task" in output

    def test_renders_task_scoped_finding_in_subsection(self) -> None:
        findings = [
            _TestCoverageFinding(
                key="TASK:unmapped-test-task",
                severity="LOW",
                description="Task T005 is unmapped.",
                recommendation="Add FR reference.",
            )
        ]
        output = render_findings(findings)
        assert "Unmapped Tasks" in output
        assert "LOW" in output

    def test_empty_findings(self) -> None:
        output = render_findings([])
        assert output == ""

    def test_all_findings_have_recommendation(self) -> None:
        findings = [
            _TestCoverageFinding(
                key="FR-001:no-test-task",
                severity="HIGH",
                fr_id="FR-001",
                description="FR-001 has no test task.",
                recommendation="Add a test task for FR-001.",
            ),
            _TestCoverageFinding(
                key="TASK:ambiguous-task",
                severity="LOW",
                description="Task T003 is ambiguous.",
                recommendation="Split into separate tasks.",
            ),
        ]
        output = render_findings(findings)
        assert "Add a test task for FR-001" in output
        assert "Split into separate tasks" in output
