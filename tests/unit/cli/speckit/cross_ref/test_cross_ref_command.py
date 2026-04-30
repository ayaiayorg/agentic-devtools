"""Test cross_ref_command CLI entry point."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.cli.speckit.cross_ref import cross_ref_command


def test_plan_file_not_found(capsys):
    """Exit 2 when plan file does not exist."""
    with pytest.raises(SystemExit) as exc_info:
        cross_ref_command(["--plan-file", "nonexistent_plan.md"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "not found" in captured.err


def test_plan_file_read_error(tmp_path, capsys):
    """Exit 2 when plan file cannot be read (e.g. binary garbage)."""
    plan = tmp_path / "plan.md"
    # Write bytes that can't be decoded as UTF-8
    plan.write_bytes(b"\x80\x81\x82\x83" * 100)
    # The read_text with encoding="utf-8" should raise UnicodeDecodeError
    # Actually Python's read_text with utf-8 may replace or raise depending on errors param
    # Let's test with an unreadable file instead - mock the read to raise
    with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
        with pytest.raises(SystemExit) as exc_info:
            cross_ref_command(["--plan-file", str(plan)])
        assert exc_info.value.code == 2


def test_valid_plan_no_high_findings_exits_zero(tmp_path):
    """Exit 0 when plan has no HIGH severity findings."""
    plan = tmp_path / "plan.md"
    plan.write_text("# Plan\n\nNo code references here.\n")

    with pytest.raises(SystemExit) as exc_info:
        cross_ref_command(["--plan-file", str(plan), "--repo-root", str(tmp_path)])
    assert exc_info.value.code == 0


def test_invalid_references_exit_one(tmp_path):
    """Exit 1 when plan has INVALID references with no candidates."""
    plan = tmp_path / "plan.md"
    plan.write_text("# Plan\n\nUse `totally_nonexistent_function_xyz` in the code.\n")

    with pytest.raises(SystemExit) as exc_info:
        cross_ref_command(["--plan-file", str(plan), "--repo-root", str(tmp_path)])
    assert exc_info.value.code == 1


def test_json_output_flag(tmp_path, capsys):
    """JSON output mode produces valid JSON."""
    plan = tmp_path / "plan.md"
    plan.write_text("# Plan\n\nNo references.\n")

    with pytest.raises(SystemExit) as exc_info:
        cross_ref_command(["--plan-file", str(plan), "--repo-root", str(tmp_path), "--json"])
    assert exc_info.value.code == 0

    import json

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["pass"] == "G"


def test_markdown_output_default(tmp_path, capsys):
    """Default output mode produces Markdown."""
    plan = tmp_path / "plan.md"
    plan.write_text("# Plan\n\nNo references.\n")

    with pytest.raises(SystemExit) as exc_info:
        cross_ref_command(["--plan-file", str(plan), "--repo-root", str(tmp_path)])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "Pass G" in captured.out


def test_pipeline_extracts_references_and_classifies(tmp_path, capsys):
    """Full pipeline: extract, build inventory, classify."""
    # Create a Python file in the repo
    src = tmp_path / "module.py"
    src.write_text("def existing_func():\n    pass\n")

    # Plan references the existing function and a nonexistent one
    plan = tmp_path / "plan.md"
    plan.write_text(
        "# Plan\n\n"
        "Use `existing_func` for processing.\n"
        "Also call `totally_nonexistent_xyz_abc` for cleanup.\n"
    )

    # Mock git ls-files to return our file
    with patch("agentic_devtools.cli.speckit.pass_g.inventory._discover_files") as mock_discover:
        mock_discover.return_value = ["module.py"]
        with pytest.raises(SystemExit) as exc_info:
            cross_ref_command(["--plan-file", str(plan), "--repo-root", str(tmp_path)])

    # Should exit 1 because of the invalid reference
    assert exc_info.value.code == 1
