"""Tests for build_finalization_report function."""

from agentic_devtools.cli.azure_devops.finalization.reporting import build_finalization_report


class TestBuildFinalizationReport:
    """Tests for build_finalization_report."""

    def test_builds_report_with_counts(self):
        """Should create a report with correct counts."""
        report = build_finalization_report(
            status="success",
            repaired=3,
            skipped=1,
            unchanged=5,
            failed=0,
            details=["detail1"],
            duration_ms=500,
        )
        assert report.status == "success"
        assert report.repaired == 3
        assert report.skipped == 1
        assert report.unchanged == 5
        assert report.failed == 0
        assert report.duration_ms == 500

    def test_noop_report(self):
        """Should create a no-op report."""
        report = build_finalization_report(
            status="no-op",
            repaired=0,
            skipped=0,
            unchanged=10,
            failed=0,
            details=[],
            duration_ms=100,
        )
        assert report.status == "no-op"
        assert report.unchanged == 10

    def test_failure_report(self):
        """Should create a failure report."""
        report = build_finalization_report(
            status="failure",
            repaired=0,
            skipped=0,
            unchanged=0,
            failed=3,
            details=["error1", "error2"],
            duration_ms=2000,
        )
        assert report.status == "failure"
        assert report.failed == 3
        assert len(report.details) == 2

    def test_dry_run_report(self):
        """Should distinguish dry-run report."""
        report = build_finalization_report(
            status="success",
            repaired=5,
            skipped=0,
            unchanged=0,
            failed=0,
            details=["Dry run: 5 comments would be repaired"],
            duration_ms=50,
        )
        assert report.repaired == 5
        assert "Dry run" in report.details[0]
