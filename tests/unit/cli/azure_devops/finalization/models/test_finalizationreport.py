"""Tests for FinalizationReport data class."""

from agentic_devtools.cli.azure_devops.finalization.models import FinalizationReport


class TestFinalizationReport:
    """Tests for FinalizationReport."""

    def test_to_dict_default_values(self):
        """Should serialize default values correctly."""
        report = FinalizationReport(status="no-op")
        d = report.to_dict()
        assert d["status"] == "no-op"
        assert d["repaired"] == 0
        assert d["skipped"] == 0
        assert d["unchanged"] == 0
        assert d["failed"] == 0
        assert d["details"] == []
        assert d["duration_ms"] == 0

    def test_to_dict_with_values(self):
        """Should serialize populated values correctly."""
        report = FinalizationReport(
            status="success",
            repaired=3,
            skipped=1,
            unchanged=5,
            failed=0,
            details=["repaired file-summary", "repaired overall-summary"],
            duration_ms=1234,
        )
        d = report.to_dict()
        assert d["status"] == "success"
        assert d["repaired"] == 3
        assert d["skipped"] == 1
        assert d["unchanged"] == 5
        assert d["failed"] == 0
        assert len(d["details"]) == 2
        assert d["duration_ms"] == 1234
