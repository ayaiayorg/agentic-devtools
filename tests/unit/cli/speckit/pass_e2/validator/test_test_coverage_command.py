"""Tests for pass_e2.validator — test_coverage_command CLI."""

import json
from unittest.mock import patch

from agentic_devtools.cli.speckit.pass_e2.validator import (
    test_coverage_command as _test_coverage_command,
)


class TestTestCoverageCommand:
    """Verify CLI entry point behavior."""

    def test_json_output(self, tmp_path, capsys) -> None:
        spec_file = tmp_path / "spec.md"
        tasks_file = tmp_path / "tasks.md"
        spec_file.write_text(
            """
### User Story 1 - Feature (Priority: P1)

FR-001 is the core feature.

## Requirements

- **FR-001**: Must work.
""",
            encoding="utf-8",
        )
        tasks_file.write_text(
            """
- [ ] T001 Implement feature (FR-001)
- [ ] T002 [US1] Verify happy-path scenario for FR-001
""",
            encoding="utf-8",
        )
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
        spec_file.write_text("FR-001 spec content", encoding="utf-8")
        tasks_file.write_text("- [ ] T001 Implement something", encoding="utf-8")

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
        spec_file.write_text("FR-001 spec", encoding="utf-8")

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

    def test_human_output_mode(self, tmp_path, capsys) -> None:
        """Without --json, produces human-readable output."""
        spec_file = tmp_path / "spec.md"
        tasks_file = tmp_path / "tasks.md"
        spec_file.write_text(
            """
### User Story 1 - Feature (Priority: P1)

FR-001 is the core feature.
""",
            encoding="utf-8",
        )
        tasks_file.write_text(
            """
- [ ] T001 Implement feature (FR-001)
- [ ] T002 [US1] Verify happy-path scenario for FR-001
""",
            encoding="utf-8",
        )
        try:
            _test_coverage_command(
                [
                    "--spec-file",
                    str(spec_file),
                    "--tasks-file",
                    str(tasks_file),
                ]
            )
        except SystemExit as e:
            assert e.code == 0

        output = capsys.readouterr().out
        assert "SpecKit E.2 Test Coverage Validation" in output

    def test_spec_file_not_found_warning(self, tmp_path, capsys) -> None:
        """Non-existent spec file prints warning and treats as empty."""
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("- [ ] T001 Write tests for FR-001", encoding="utf-8")

        try:
            _test_coverage_command(
                [
                    "--spec-file",
                    str(tmp_path / "nonexistent_spec.md"),
                    "--tasks-file",
                    str(tasks_file),
                    "--json",
                ]
            )
        except SystemExit as e:
            # Tasks exist but spec is empty → no FRs found → no findings → exit 0
            assert e.code == 0

        stderr_output = capsys.readouterr().err
        assert "not found" in stderr_output

    def test_spec_file_read_error(self, tmp_path) -> None:
        """Unreadable spec file → exit code 2."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("content", encoding="utf-8")
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("- [ ] T001 Test", encoding="utf-8")

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # os.path.isfile still returns True because we don't patch it
            with patch("os.path.isfile", return_value=True):
                try:
                    _test_coverage_command(
                        [
                            "--spec-file",
                            str(spec_file),
                            "--tasks-file",
                            str(tasks_file),
                        ]
                    )
                except SystemExit as e:
                    assert e.code == 2

    def test_tasks_file_read_error(self, tmp_path) -> None:
        """Unreadable tasks file → exit code 2."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("FR-001 spec", encoding="utf-8")
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("content", encoding="utf-8")

        original_open = open

        def mock_open(path, *args, **kwargs):
            if "tasks.md" in str(path):
                raise OSError("Permission denied")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            with patch("os.path.isfile", return_value=True):
                try:
                    _test_coverage_command(
                        [
                            "--spec-file",
                            str(spec_file),
                            "--tasks-file",
                            str(tasks_file),
                        ]
                    )
                except SystemExit as e:
                    assert e.code == 2

    def test_validate_exception_exit_code_2(self, tmp_path) -> None:
        """Exception during validation → exit code 2."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("FR-001 in spec", encoding="utf-8")
        tasks_file = tmp_path / "tasks.md"
        tasks_file.write_text("- [ ] T001 Test FR-001", encoding="utf-8")

        with patch(
            "agentic_devtools.cli.speckit.pass_e2.validator.validate_test_coverage",
            side_effect=RuntimeError("Unexpected error"),
        ):
            try:
                _test_coverage_command(
                    [
                        "--spec-file",
                        str(spec_file),
                        "--tasks-file",
                        str(tasks_file),
                    ]
                )
            except SystemExit as e:
                assert e.code == 2
