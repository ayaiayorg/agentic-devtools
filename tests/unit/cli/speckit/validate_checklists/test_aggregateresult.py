"""Tests for AggregateResult dataclass."""

from __future__ import annotations

from agentic_devtools.cli.speckit.validate_checklists import (
    AggregateResult,
    FileClassification,
    FileResult,
    Severity,
)


class TestAggregateResult:
    """Tests for AggregateResult.to_json()."""

    def test_empty_result_to_json(self) -> None:
        result = AggregateResult(files=[], passed=True, warning="No files")
        json_out = result.to_json()
        assert json_out["passed"] is True
        assert json_out["files"] == []
        assert json_out["warning"] == "No files"

    def test_to_json_includes_all_fields(self) -> None:
        result = AggregateResult(
            files=[
                FileResult(
                    path="/file.md",
                    checkbox_count=5,
                    classification=FileClassification.valid,
                    severity=Severity.NONE,
                    explanation="valid",
                    remediated=True,
                    retries_used=1,
                )
            ],
            passed=True,
        )
        json_out = result.to_json()
        file_data = json_out["files"][0]
        assert file_data["path"] == "/file.md"
        assert file_data["checkbox_count"] == 5
        assert file_data["classification"] == "valid"
        assert file_data["severity"] == "NONE"
        assert file_data["explanation"] == "valid"
        assert file_data["remediated"] is True
        assert file_data["retries_used"] == 1

    def test_to_json_warning_none(self) -> None:
        result = AggregateResult(files=[], passed=True)
        json_out = result.to_json()
        assert json_out["warning"] is None
