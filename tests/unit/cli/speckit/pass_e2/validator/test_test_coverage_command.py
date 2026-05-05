"""Tests for pass_e2.validator — test_coverage_command CLI."""

import json

from agentic_devtools.cli.speckit.pass_e2.validator import (
    test_coverage_command as _test_coverage_command,
)


class TestTestCoverageCommand:
    """Verify CLI entry point behavior."""

    def test_json_output(self, tmp_path, capsys) -> None:
        spec_file = tmp_path / "spec.md"
        tasks_file = tmp_path / "tasks.md"
        spec_file.write_text("""
### User Story 1 — Feature (Priority: P1)

FR-001 is the core feature.

## Requirements

- **FR-001**: Must work.
""")
        tasks_file.write_text("""
- [ ] T001 Implement feature (FR-001)
- [ ] T002 [US1] Verify happy-path scenario for FR-001
""")
        try:
            _test_coverage_command(
                [
                    "--spec-file",
                    str(spec_file),
                    "--tasks-file",
                    str(tasks_file),
                    "--json",
                ]
            )
        except SystemExit as e:
            assert e.code == 0

        output = json.loads(capsys.readouterr().out)
        assert "findings" in output
        assert "coverage" in output
        assert "summary" in output

    def test_exit_code_1_on_findings(self, tmp_path) -> None:
        spec_file = tmp_path / "spec.md"
        tasks_file = tmp_path / "tasks.md"
        spec_file.write_text("FR-001 spec content")
        tasks_file.write_text("- [ ] T001 Implement something")

        try:
            _test_coverage_command(
                [
                    "--spec-file",
                    str(spec_file),
                    "--tasks-file",
                    str(tasks_file),
                    "--json",
                ]
            )
        except SystemExit as e:
            # Should exit 1 because FR-001 has no test task
            assert e.code == 1

    def test_exit_code_1_missing_tasks(self, tmp_path) -> None:
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("FR-001 spec")

        try:
            _test_coverage_command(
                [
                    "--spec-file",
                    str(spec_file),
                    "--tasks-file",
                    str(tmp_path / "nonexistent.md"),
                    "--json",
                ]
            )
        except SystemExit as e:
            # FR-009: missing tasks → CRITICAL finding → exit 1
            assert e.code == 1
