"""Tests for ``validate_frs()`` orchestrator."""

from agentic_devtools.cli.speckit.validate_frs import validate_frs


class TestValidateFrs:
    """validate_frs: orchestration of extract + coverage + sort."""

    def test_full_pass_all_covered(self) -> None:
        spec = "FR-001 and FR-002 are specified."
        tasks = "Task for FR-001. Task for FR-002."
        result = validate_frs(spec, tasks)
        assert result.passed is True
        assert result.total == 2
        assert set(result.covered) == {"FR-001", "FR-002"}
        assert result.uncovered == []
        assert result.warning is None

    def test_partial_fail_some_uncovered(self) -> None:
        spec = "FR-001, FR-002, FR-003."
        tasks = "Only FR-001 is in tasks."
        result = validate_frs(spec, tasks)
        assert result.passed is False
        assert result.total == 3
        assert result.covered == ["FR-001"]
        assert result.uncovered == ["FR-002", "FR-003"]

    def test_no_frs_found_warning_and_pass(self) -> None:
        spec = "No functional requirements here."
        tasks = "Some tasks."
        result = validate_frs(spec, tasks)
        assert result.passed is True
        assert result.total == 0
        assert result.warning is not None
        assert "No FR identifiers" in result.warning

    def test_empty_tasks_all_uncovered(self) -> None:
        spec = "FR-001 and FR-002."
        tasks = ""
        result = validate_frs(spec, tasks)
        assert result.passed is False
        assert result.total == 2
        assert result.covered == []
        assert set(result.uncovered) == {"FR-001", "FR-002"}

    def test_empty_spec_warning_and_pass(self) -> None:
        spec = ""
        tasks = "Tasks with FR-001."
        result = validate_frs(spec, tasks)
        assert result.passed is True
        assert result.total == 0
        assert result.warning is not None

    def test_covered_and_uncovered_are_sorted(self) -> None:
        spec = "FR-003, FR-001, FR-002."
        tasks = "FR-003 and FR-001."
        result = validate_frs(spec, tasks)
        assert result.covered == ["FR-001", "FR-003"]
        assert result.uncovered == ["FR-002"]
