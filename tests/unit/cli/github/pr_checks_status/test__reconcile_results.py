"""Tests for _reconcile_results function."""

from agentic_devtools.cli.github.pr_checks_status import _reconcile_results


def _make_classification(**overrides):
    """Helper to build a classification dict with defaults."""
    base = {
        "passed": 0,
        "failed": 0,
        "pending": 0,
        "skipped": 0,
        "cancelled": 0,
        "total": 0,
        "failedChecks": [],
        "pendingChecks": [],
    }
    base.update(overrides)
    return base


class TestReconcileResults:
    """Tests for status reconciliation and override logic."""

    def test_all_pass_with_verified_suites(self):
        """All-pass with verified suites → status all-pass, checkSuitesVerified true."""
        classification = _make_classification(passed=5, total=5)
        result = _reconcile_results(classification, suites_verified=True, discrepancies=[], head_sha_available=True)
        assert result["status"] == "all-pass"
        assert result["checkSuitesVerified"] is True
        assert result["checkSuiteDiscrepancies"] == []

    def test_all_pass_with_discrepancy_failure(self):
        """All-pass with failure discrepancy → override to failed."""
        classification = _make_classification(passed=5, total=5)
        discs = [{"suiteId": 1, "app": "ci", "status": "completed", "conclusion": "failure"}]
        result = _reconcile_results(classification, suites_verified=False, discrepancies=discs, head_sha_available=True)
        assert result["status"] == "failed"
        assert result["checkSuitesVerified"] is False

    def test_all_pass_with_discrepancy_cancelled_conclusion(self):
        """All-pass with cancelled conclusion → override to failed."""
        classification = _make_classification(passed=5, total=5)
        discs = [{"suiteId": 1, "app": "ci", "status": "completed", "conclusion": "cancelled"}]
        result = _reconcile_results(classification, suites_verified=False, discrepancies=discs, head_sha_available=True)
        assert result["status"] == "failed"

    def test_all_pass_with_discrepancy_timed_out_conclusion(self):
        """All-pass with timed_out conclusion → override to failed."""
        classification = _make_classification(passed=5, total=5)
        discs = [{"suiteId": 1, "app": "ci", "status": "completed", "conclusion": "timed_out"}]
        result = _reconcile_results(classification, suites_verified=False, discrepancies=discs, head_sha_available=True)
        assert result["status"] == "failed"

    def test_all_pass_with_discrepancy_empty_conclusion(self):
        """All-pass with empty conclusion (completed but no result) → override to failed."""
        classification = _make_classification(passed=5, total=5)
        discs = [{"suiteId": 1, "app": "ci", "status": "completed", "conclusion": ""}]
        result = _reconcile_results(classification, suites_verified=False, discrepancies=discs, head_sha_available=True)
        assert result["status"] == "failed"

    def test_all_pass_with_discrepancy_pending(self):
        """All-pass with incomplete suite → override to pending."""
        classification = _make_classification(passed=5, total=5)
        discs = [{"suiteId": 1, "app": "ci", "status": "in_progress", "conclusion": ""}]
        result = _reconcile_results(classification, suites_verified=False, discrepancies=discs, head_sha_available=True)
        assert result["status"] == "pending"

    def test_failed_status_not_overridden(self):
        """Failed base status is not overridden by suites."""
        classification = _make_classification(passed=3, failed=2, total=5, failedChecks=["a", "b"])
        result = _reconcile_results(classification, suites_verified=True, discrepancies=[], head_sha_available=True)
        assert result["status"] == "failed"

    def test_pending_status_not_overridden(self):
        """Pending base status is not overridden by suites."""
        classification = _make_classification(passed=3, pending=2, total=5, pendingChecks=["a", "b"])
        result = _reconcile_results(classification, suites_verified=True, discrepancies=[], head_sha_available=True)
        assert result["status"] == "pending"

    def test_cancelled_status(self):
        """Cancelled checks with no pending/failed → cancelled status."""
        classification = _make_classification(passed=3, cancelled=1, total=4)
        result = _reconcile_results(classification, suites_verified=True, discrepancies=[], head_sha_available=True)
        assert result["status"] == "cancelled"

    def test_head_sha_not_available(self):
        """No head_sha → checkSuitesVerified false, no discrepancies."""
        classification = _make_classification(passed=5, total=5)
        result = _reconcile_results(classification, suites_verified=False, discrepancies=[], head_sha_available=False)
        assert result["status"] == "all-pass"
        assert result["checkSuitesVerified"] is False
        assert result["checkSuiteDiscrepancies"] == []

    def test_output_contains_all_counts(self):
        """Output dict contains all expected count fields."""
        classification = _make_classification(
            passed=3,
            failed=1,
            pending=1,
            skipped=2,
            cancelled=1,
            total=8,
            failedChecks=["x"],
            pendingChecks=["y"],
        )
        result = _reconcile_results(
            classification,
            suites_verified=False,
            discrepancies=[],
            head_sha_available=True,
        )
        assert result["totalChecks"] == 8
        assert result["passed"] == 3
        assert result["failed"] == 1
        assert result["pending"] == 1
        assert result["skipped"] == 2
        assert result["cancelled"] == 1
        assert result["failedChecks"] == ["x"]
        assert result["pendingChecks"] == ["y"]

    def test_pending_takes_priority_over_failed(self):
        """Pending status takes priority over failed."""
        classification = _make_classification(
            passed=1,
            failed=1,
            pending=1,
            total=3,
            failedChecks=["a"],
            pendingChecks=["b"],
        )
        result = _reconcile_results(
            classification,
            suites_verified=True,
            discrepancies=[],
            head_sha_available=True,
        )
        assert result["status"] == "pending"
