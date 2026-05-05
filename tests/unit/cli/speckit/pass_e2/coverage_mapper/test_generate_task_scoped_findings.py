"""Tests for pass_e2.coverage_mapper — generate_task_scoped_findings."""

from agentic_devtools.cli.speckit.pass_e2.coverage_mapper import generate_task_scoped_findings
from agentic_devtools.cli.speckit.pass_e2.models import TestTask as _TestTask


class TestGenerateTaskScopedFindings:
    """Verify LOW-severity findings for task-scoped issues."""

    def test_invalid_us_ref_generates_finding(self) -> None:
        """Task referencing non-existent US → LOW finding."""
        task = _TestTask(
            task_id="T001",
            description="Test for [US5]",
            us_labels=[5],
        )
        us_to_fr = {1: ["FR-001"], 2: ["FR-002"]}

        findings = generate_task_scoped_findings(
            test_tasks=[task],
            unmapped_tasks=[],
            us_to_fr=us_to_fr,
        )

        invalid_us = [f for f in findings if f.key == "TASK:invalid-us-ref"]
        assert len(invalid_us) == 1
        assert invalid_us[0].severity == "LOW"
        assert "T001" in invalid_us[0].description
        assert "US5" in invalid_us[0].description

    def test_unmapped_task_generates_finding(self) -> None:
        """Unmapped test task → LOW finding."""
        task = _TestTask(
            task_id="T002",
            description="Write some tests",
        )
        us_to_fr = {1: ["FR-001"]}

        findings = generate_task_scoped_findings(
            test_tasks=[],
            unmapped_tasks=[task],
            us_to_fr=us_to_fr,
        )

        unmapped = [f for f in findings if f.key == "TASK:unmapped-test-task"]
        assert len(unmapped) == 1
        assert unmapped[0].severity == "LOW"
        assert "T002" in unmapped[0].description

    def test_ambiguous_task_generates_finding(self) -> None:
        """Ambiguous task (both impl and test keywords) → LOW finding."""
        task = _TestTask(
            task_id="T003",
            description="Implement and verify the feature",
            is_ambiguous=True,
        )
        us_to_fr = {1: ["FR-001"]}

        findings = generate_task_scoped_findings(
            test_tasks=[task],
            unmapped_tasks=[],
            us_to_fr=us_to_fr,
        )

        ambiguous = [f for f in findings if f.key == "TASK:ambiguous-task"]
        assert len(ambiguous) == 1
        assert ambiguous[0].severity == "LOW"
        assert "T003" in ambiguous[0].description

    def test_no_issues_empty_findings(self) -> None:
        """Clean tasks produce no findings."""
        task = _TestTask(
            task_id="T001",
            description="Test FR-001",
            us_labels=[1],
        )
        us_to_fr = {1: ["FR-001"]}

        findings = generate_task_scoped_findings(
            test_tasks=[task],
            unmapped_tasks=[],
            us_to_fr=us_to_fr,
        )

        assert findings == []

    def test_empty_us_to_fr_with_us_label(self) -> None:
        """Task with US label but empty us_to_fr mapping → invalid-us-ref."""
        task = _TestTask(
            task_id="T004",
            description="Test [US1]",
            us_labels=[1],
        )

        findings = generate_task_scoped_findings(
            test_tasks=[task],
            unmapped_tasks=[],
            us_to_fr={},
        )

        # max_us is 0, so any us_num > 0 triggers the finding
        invalid_us = [f for f in findings if f.key == "TASK:invalid-us-ref"]
        assert len(invalid_us) == 1
