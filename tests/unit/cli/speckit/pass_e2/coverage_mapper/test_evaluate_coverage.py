"""Tests for pass_e2.coverage_mapper — evaluate_coverage."""

from agentic_devtools.cli.speckit.pass_e2.coverage_mapper import evaluate_coverage
from agentic_devtools.cli.speckit.pass_e2.models import FRInfo
from agentic_devtools.cli.speckit.pass_e2.models import TestTask as _TestTask


class TestEvaluateCoverage:
    """Verify FR-004 and FR-005 coverage evaluation."""

    def test_p1_fr_no_tasks_critical(self) -> None:
        """P1 FR with no test tasks → CRITICAL (FR-005 subsumes FR-004)."""
        fr_infos = [FRInfo(fr_id="FR-001", priority=1)]
        fr_to_tasks: dict[str, list[_TestTask]] = {"FR-001": []}

        coverage, findings = evaluate_coverage(fr_infos, fr_to_tasks)
        assert not coverage["FR-001"].is_covered
        assert len(findings) == 1
        assert findings[0].severity == "CRITICAL"
        assert findings[0].key == "FR-001:no-happy-path"

    def test_p2_fr_no_tasks_high(self) -> None:
        """Non-P1 FR with no test tasks → HIGH (FR-004)."""
        fr_infos = [FRInfo(fr_id="FR-002", priority=2)]
        fr_to_tasks: dict[str, list[_TestTask]] = {"FR-002": []}

        coverage, findings = evaluate_coverage(fr_infos, fr_to_tasks)
        assert not coverage["FR-002"].is_covered
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"
        assert findings[0].key == "FR-002:no-test-task"

    def test_p1_fr_no_happy_path_critical(self) -> None:
        """P1 FR with test tasks but no happy-path → CRITICAL (FR-005)."""
        fr_infos = [FRInfo(fr_id="FR-001", priority=1)]
        task = _TestTask(
            task_id="T001",
            description="Infrastructure test",
            test_types=["infrastructure"],
        )
        fr_to_tasks: dict[str, list[_TestTask]] = {"FR-001": [task]}

        coverage, findings = evaluate_coverage(fr_infos, fr_to_tasks)
        assert coverage["FR-001"].is_covered
        assert not coverage["FR-001"].has_happy_path
        assert len(findings) == 1
        assert findings[0].severity == "CRITICAL"
        assert "no-happy-path" in findings[0].key

    def test_fully_covered_no_findings(self) -> None:
        """FR with happy-path test → no findings."""
        fr_infos = [FRInfo(fr_id="FR-001", priority=1)]
        task = _TestTask(
            task_id="T001",
            description="Happy path test",
            test_types=["happy-path"],
        )
        fr_to_tasks: dict[str, list[_TestTask]] = {"FR-001": [task]}

        coverage, findings = evaluate_coverage(fr_infos, fr_to_tasks)
        assert coverage["FR-001"].is_covered
        assert coverage["FR-001"].has_happy_path
        assert findings == []

    def test_p3_fr_no_test_high_not_critical(self) -> None:
        """P3 FR with no test → HIGH, not CRITICAL."""
        fr_infos = [FRInfo(fr_id="FR-004", priority=3)]
        fr_to_tasks: dict[str, list[_TestTask]] = {"FR-004": []}

        _, findings = evaluate_coverage(fr_infos, fr_to_tasks)
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"
