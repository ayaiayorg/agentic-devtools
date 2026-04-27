"""Tests for ``validate_frs_command()`` CLI entry point."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.cli.speckit.validate_frs import validate_frs_command


def _write_file(directory: Path, name: str, content: str) -> Path:
    p = directory / name
    p.write_text(content, encoding="utf-8")
    return p


class TestValidateFrsCommandJson:
    """JSON output mode (--json)."""

    def test_all_covered_exit_0(self, tmp_path: Path) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001 and FR-002.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001 task. FR-002 task.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                    "--json",
                ]
            )
        assert exc_info.value.code == 0

    def test_uncovered_frs_exit_1(self, tmp_path: Path) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001 and FR-002.")
        tasks = _write_file(tmp_path, "tasks.md", "Only FR-001.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                    "--json",
                ]
            )
        assert exc_info.value.code == 1

    def test_json_output_schema(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001 and FR-002.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001 task. FR-002 task.")
        with pytest.raises(SystemExit):
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                    "--json",
                ]
            )
        output = json.loads(capsys.readouterr().out)
        assert "covered" in output
        assert "uncovered" in output
        assert "total" in output
        assert "max_retries" in output

    def test_no_frs_warning_exit_0(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec = _write_file(tmp_path, "spec.md", "No FRs here.")
        tasks = _write_file(tmp_path, "tasks.md", "Some tasks.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                    "--json",
                ]
            )
        assert exc_info.value.code == 0
        output = json.loads(capsys.readouterr().out)
        assert "warning" in output


class TestValidateFrsCommandHuman:
    """Human-readable output (default, no --json)."""

    def test_pass_output(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001 done.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                ]
            )
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "✅" in out

    def test_fail_output(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001 and FR-002.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001 only.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                ]
            )
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "FAIL" in out
        assert "❌" in out
        assert "FR-002" in out

    def test_warning_output(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec = _write_file(tmp_path, "spec.md", "No FRs.")
        tasks = _write_file(tmp_path, "tasks.md", "Tasks.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                ]
            )
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "WARNING" in out


class TestValidateFrsCommandEdgeCases:
    """Edge cases: missing files, empty files, exit code 2."""

    def test_missing_spec_file_warns_and_passes(self, tmp_path: Path) -> None:
        tasks = _write_file(tmp_path, "tasks.md", "FR-001 task.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(tmp_path / "nonexistent.md"),
                    "--tasks-file",
                    str(tasks),
                ]
            )
        # Empty spec → no FRs → warning + pass
        assert exc_info.value.code == 0

    def test_missing_tasks_file_with_frs_exits_1(self, tmp_path: Path) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tmp_path / "nonexistent.md"),
                ]
            )
        # FRs extracted but tasks empty → all uncovered → exit 1
        assert exc_info.value.code == 1

    def test_empty_spec_file_warns_and_passes(self, tmp_path: Path) -> None:
        spec = _write_file(tmp_path, "spec.md", "")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001 task.")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                ]
            )
        assert exc_info.value.code == 0

    def test_empty_tasks_file_with_frs_exits_1(self, tmp_path: Path) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        tasks = _write_file(tmp_path, "tasks.md", "")
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                ]
            )
        assert exc_info.value.code == 1


class TestValidateFrsCommandMaxRetries:
    """--max-retries precedence: CLI > env > default."""

    def test_default_max_retries(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001.")
        env = {k: v for k, v in os.environ.items() if k != "SPECKIT_VALIDATE_MAX_RETRIES"}
        with patch.dict(os.environ, env, clear=True), pytest.raises(SystemExit):
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                    "--json",
                ]
            )
        output = json.loads(capsys.readouterr().out)
        assert output["max_retries"] == 2

    def test_env_var_overrides_default(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001.")
        with patch.dict(os.environ, {"SPECKIT_VALIDATE_MAX_RETRIES": "5"}), pytest.raises(SystemExit):
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                    "--json",
                ]
            )
        output = json.loads(capsys.readouterr().out)
        assert output["max_retries"] == 5

    def test_cli_flag_overrides_env(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001.")
        with patch.dict(os.environ, {"SPECKIT_VALIDATE_MAX_RETRIES": "5"}), pytest.raises(SystemExit):
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                    "--json",
                    "--max-retries",
                    "3",
                ]
            )
        output = json.loads(capsys.readouterr().out)
        assert output["max_retries"] == 3

    def test_json_sort_order(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """FR-011: covered/uncovered sorted by numeric suffix ascending."""
        spec = _write_file(tmp_path, "spec.md", "FR-003, FR-001, FR-002.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-003 and FR-001.")
        with pytest.raises(SystemExit):
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                    "--json",
                ]
            )
        output = json.loads(capsys.readouterr().out)
        assert output["covered"] == ["FR-001", "FR-003"]
        assert output["uncovered"] == ["FR-002"]


class TestValidateFrsCommandFileReadErrors:
    """OSError / UnicodeDecodeError when reading spec or tasks files → exit code 2."""

    def test_spec_file_read_oserror_exits_2(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """OSError reading spec file → stderr message + exit code 2."""
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001 task.")
        with (
            patch("builtins.open", side_effect=OSError("disk error")),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate_frs_command(
                ["--spec-file", str(spec), "--tasks-file", str(tasks)]
            )
        assert exc_info.value.code == 2
        assert "disk error" in capsys.readouterr().err

    def test_tasks_file_read_oserror_exits_2(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """OSError reading tasks file → stderr message + exit code 2."""
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001 task.")

        real_open = open
        call_count = 0

        def open_side_effect(path, *args, **kwargs):
            nonlocal call_count
            # Let the first open (spec file) succeed, fail on the second (tasks file)
            call_count += 1
            if call_count >= 2:
                raise OSError("tasks disk error")
            return real_open(path, *args, **kwargs)

        with (
            patch("builtins.open", side_effect=open_side_effect),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate_frs_command(
                ["--spec-file", str(spec), "--tasks-file", str(tasks)]
            )
        assert exc_info.value.code == 2
        assert "tasks disk error" in capsys.readouterr().err


class TestValidateFrsCommandArgparseErrors:
    """Argparse usage errors exit with code 2."""

    def test_missing_required_args_exits_2(self) -> None:
        """Missing --spec-file and --tasks-file → exit code 2."""
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command([])
        assert exc_info.value.code == 2

    def test_unknown_flag_exits_2(self) -> None:
        """Unknown flag → exit code 2."""
        with pytest.raises(SystemExit) as exc_info:
            validate_frs_command(["--spec-file", "x", "--tasks-file", "y", "--bogus"])
        assert exc_info.value.code == 2


class TestValidateFrsCommandValidationException:
    """Exception in validate_frs() → exit code 2."""

    def test_validation_exception_exits_2(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Exception raised by validate_frs → stderr message + exit code 2."""
        spec = _write_file(tmp_path, "spec.md", "FR-001.")
        tasks = _write_file(tmp_path, "tasks.md", "FR-001.")
        with (
            patch(
                "agentic_devtools.cli.speckit.validate_frs.validate_frs",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            validate_frs_command(
                [
                    "--spec-file",
                    str(spec),
                    "--tasks-file",
                    str(tasks),
                ]
            )
        assert exc_info.value.code == 2
        assert "boom" in capsys.readouterr().err
