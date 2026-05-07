"""Tests for _print_human_output() function."""

from __future__ import annotations

from agentic_devtools.cli.speckit.validate_checklists import (
    AggregateResult,
    FileClassification,
    FileResult,
    Severity,
    _print_human_output,
)


class TestPrintHumanOutput:
    """Tests for _print_human_output formatting."""

    def test_warning_output(self, capsys) -> None:
        result = AggregateResult(files=[], passed=True, warning="No checklist files found to validate")
        _print_human_output(result)
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "PASS" in captured.out

    def test_valid_file_output(self, capsys) -> None:
        result = AggregateResult(
            files=[
                FileResult(
                    path="/path/to/file.md",
                    checkbox_count=5,
                    classification=FileClassification.valid,
                    severity=Severity.NONE,
                    explanation="File contains 5 checkbox items (≥3 required) — valid",
                )
            ],
            passed=True,
        )
        _print_human_output(result)
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "PASS" in captured.out
        assert "/path/to/file.md" in captured.out

    def test_failed_output_shows_severity(self, capsys) -> None:
        result = AggregateResult(
            files=[
                FileResult(
                    path="/path/to/prose.md",
                    checkbox_count=0,
                    classification=FileClassification.prose_only,
                    severity=Severity.MEDIUM,
                    explanation="File contains 0 checkbox items — prose-only",
                )
            ],
            passed=False,
        )
        _print_human_output(result)
        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "MEDIUM" in captured.out
        assert "FAIL" in captured.out

    def test_remediated_file_shows_note(self, capsys) -> None:
        result = AggregateResult(
            files=[
                FileResult(
                    path="/path/to/fixed.md",
                    checkbox_count=3,
                    classification=FileClassification.valid,
                    severity=Severity.NONE,
                    explanation="File contains 3 checkbox items (≥3 required) — valid",
                    remediated=True,
                    retries_used=1,
                )
            ],
            passed=True,
        )
        _print_human_output(result)
        captured = capsys.readouterr()
        assert "(remediated)" in captured.out
