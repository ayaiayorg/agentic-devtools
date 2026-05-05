"""Tests for pass_e2.models — data class behavior."""

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


class TestTaskModel:
    """TestTask data class."""

    def test_fields(self) -> None:
        t = _TestTask(task_id="T001", description="Test something")
        assert t.task_id == "T001"
        assert t.fr_refs == []
        assert t.us_labels == []
        assert t.test_types == []
        assert t.is_ambiguous is False


class TestFRInfo:
    """FRInfo data class."""

    def test_fields(self) -> None:
        info = FRInfo(fr_id="FR-001", priority=1, user_story=1)
        assert info.fr_id == "FR-001"
        assert info.priority == 1
        assert info.priority_ambiguous is False


class TestFRCoverage:
    """FRCoverage data class."""

    def test_is_covered_with_tasks(self) -> None:
        cov = FRCoverage(
            fr_info=FRInfo(fr_id="FR-001", priority=1),
            test_tasks=[_TestTask(task_id="T001", description="test")],
        )
        assert cov.is_covered is True

    def test_is_not_covered_without_tasks(self) -> None:
        cov = FRCoverage(
            fr_info=FRInfo(fr_id="FR-001", priority=1),
            test_tasks=[],
        )
        assert cov.is_covered is False


class TestCoverageFindingModel:
    """TestCoverageFinding data class."""

    def test_to_dict(self) -> None:
        f = _TestCoverageFinding(
            key="FR-001:no-test-task",
            severity="HIGH",
            fr_id="FR-001",
            description="No test task.",
            recommendation="Add one.",
        )
        d = f.to_dict()
        assert d["key"] == "FR-001:no-test-task"
        assert d["severity"] == "HIGH"
        assert d["fr_id"] == "FR-001"


class TestCoverageResultModel:
    """TestCoverageResult data class."""

    def test_to_dict_empty(self) -> None:
        r = _TestCoverageResult()
        d = r.to_dict()
        assert d["findings"] == []
        assert d["summary"]["total_frs"] == 0
