"""Tests for agentic_devtools.submission_manager.FailureReport."""

from agentic_devtools.submission_manager import FailedItemSummary, FailureReport


class TestFailureReport:
    """Tests for FailureReport dataclass."""

    def test_default_guidance(self):
        """Test default resubmission_guidance text."""
        report = FailureReport(failed_items=[])
        assert "enqueue()" in report.resubmission_guidance
        assert "resubmission" in report.resubmission_guidance

    def test_to_dict(self):
        """Test to_dict returns correct structure."""
        report = FailureReport(
            failed_items=[
                FailedItemSummary(
                    item_id="id-1",
                    file_path="/src/a.ts",
                    last_error="429",
                    attempts=4,
                ),
                FailedItemSummary(
                    item_id="id-2",
                    file_path="/src/b.ts",
                    last_error="timeout",
                    attempts=2,
                ),
            ]
        )
        d = report.to_dict()
        assert len(d["failed_items"]) == 2
        assert d["failed_items"][0]["file_path"] == "/src/a.ts"
        assert d["failed_items"][1]["last_error"] == "timeout"
        assert "resubmission_guidance" in d

    def test_to_text_contains_file_paths(self):
        """Test to_text contains file paths and errors."""
        report = FailureReport(
            failed_items=[
                FailedItemSummary(
                    item_id="id-1",
                    file_path="/src/app.ts",
                    last_error="503 Service Unavailable",
                    attempts=4,
                ),
            ]
        )
        text = report.to_text()
        assert "/src/app.ts" in text
        assert "503 Service Unavailable" in text
        assert "enqueue()" in text
        assert "id-1" in text

    def test_to_text_multiple_items(self):
        """Test to_text with multiple failed items."""
        report = FailureReport(
            failed_items=[
                FailedItemSummary(item_id="a", file_path="/f1.ts", last_error="err1", attempts=1),
                FailedItemSummary(item_id="b", file_path="/f2.ts", last_error="err2", attempts=3),
            ]
        )
        text = report.to_text()
        assert "/f1.ts" in text
        assert "/f2.ts" in text
        assert "err1" in text
        assert "err2" in text
