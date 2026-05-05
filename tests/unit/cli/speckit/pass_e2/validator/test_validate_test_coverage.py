"""Tests for pass_e2.validator — validate_test_coverage end-to-end."""

from agentic_devtools.cli.speckit.pass_e2.validator import validate_test_coverage


class TestValidateTestCoverage:
    """End-to-end validation tests."""

    def test_missing_tasks_file_critical(self) -> None:
        """FR-009: Missing tasks.md → CRITICAL finding."""
        result = validate_test_coverage("FR-001 spec", None)
        assert len(result.findings) == 1
        assert result.findings[0].key == "TASK:missing-tasks-file"
        assert result.findings[0].severity == "CRITICAL"

    def test_empty_tasks_file_critical(self) -> None:
        """FR-009: Empty tasks.md → CRITICAL finding."""
        result = validate_test_coverage("FR-001 spec", "# Tasks\n\nNo tasks here.")
        assert len(result.findings) == 1
        assert result.findings[0].key == "TASK:empty-tasks-file"
        assert result.findings[0].severity == "CRITICAL"

    def test_no_frs_in_spec_returns_empty(self) -> None:
        """Tasks exist but spec has no FR references → empty result."""
        spec = "This spec has no functional requirements defined."
        tasks = "- [ ] T001 Implement the feature\n- [ ] T002 Write tests for the module"
        result = validate_test_coverage(spec, tasks)
        assert result.findings == []
        assert result.coverage == {}

    def test_all_frs_covered(self) -> None:
        """All FRs have test tasks → no coverage findings."""
        spec = """
### User Story 1 — Feature (Priority: P1)

FR-001 is the core feature.

## Requirements

- **FR-001**: Must work.
"""
        tasks = """
- [ ] T001 Implement feature (FR-001)
- [ ] T002 [US1] Write happy-path tests verifying FR-001 works correctly
"""
        result = validate_test_coverage(spec, tasks)
        # Should have no HIGH/CRITICAL findings for coverage
        coverage_findings = [
            f
            for f in result.findings
            if f.severity in ("HIGH", "CRITICAL") and ("no-test-task" in f.key or "no-happy-path" in f.key)
        ]
        assert coverage_findings == []

    def test_p1_fr_no_happy_path_critical(self) -> None:
        """FR-005: P1 FR with test tasks but no happy-path → CRITICAL."""
        spec = """
### User Story 1 — Feature (Priority: P1)

FR-001 is the core feature.

## Requirements

- **FR-001**: Must work.
"""
        tasks = """
- [ ] T001 Implement feature (FR-001)
- [ ] T002 [US1] Write infrastructure setup tests for CI pipeline scaffolding
"""
        result = validate_test_coverage(spec, tasks)
        critical_findings = [f for f in result.findings if f.severity == "CRITICAL"]
        assert len(critical_findings) == 1
        assert "FR-001" in critical_findings[0].key
        assert "no-happy-path" in critical_findings[0].key

    def test_non_p1_fr_no_test_high(self) -> None:
        """FR-004: Non-P1 FR with no test task → HIGH."""
        spec = """
### User Story 1 — Feature (Priority: P2)

FR-001 is a P2 feature.

## Requirements

- **FR-001**: Must work.
"""
        tasks = """
- [ ] T001 Implement feature (FR-001)
"""
        result = validate_test_coverage(spec, tasks)
        high_findings = [f for f in result.findings if f.severity == "HIGH"]
        assert len(high_findings) == 1
        assert "FR-001:no-test-task" == high_findings[0].key

    def test_sc001_fixture(self) -> None:
        """SC-001: P1 FR-001 with no happy-path test → CRITICAL."""
        import os

        fixtures_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
            "..",
            "specs",
            "1202-speckit-pipeline-validate-each",
            "fixtures",
            "sc-001",
        )
        spec_path = os.path.join(fixtures_dir, "spec.md")
        tasks_path = os.path.join(fixtures_dir, "tasks.md")

        if not os.path.isfile(spec_path):
            import pytest

            pytest.skip("Fixture file not available: specs/1202-speckit-pipeline-validate-each/fixtures/sc-001/spec.md")

        with open(spec_path, encoding="utf-8") as f:
            spec = f.read()
        with open(tasks_path, encoding="utf-8") as f:
            tasks = f.read()

        result = validate_test_coverage(spec, tasks)
        # FR-001 is P1 with no happy-path test → should be CRITICAL
        critical = [f for f in result.findings if f.severity == "CRITICAL"]
        assert len(critical) >= 1
        fr001_critical = [f for f in critical if f.fr_id == "FR-001"]
        assert len(fr001_critical) == 1
        assert "no-happy-path" in fr001_critical[0].key
