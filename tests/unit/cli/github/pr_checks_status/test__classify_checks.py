"""Tests for _classify_checks function."""

from agentic_devtools.cli.github.pr_checks_status import _classify_checks


class TestClassifyChecks:
    """Tests for bucket-based check classification."""

    def test_all_pass(self):
        """All checks with bucket 'pass' are counted as passed."""
        checks = [
            {"name": "build", "bucket": "pass"},
            {"name": "lint", "bucket": "pass"},
            {"name": "test", "bucket": "pass"},
        ]
        result = _classify_checks(checks)
        assert result["passed"] == 3
        assert result["failed"] == 0
        assert result["pending"] == 0
        assert result["skipped"] == 0
        assert result["cancelled"] == 0
        assert result["total"] == 3
        assert result["failedChecks"] == []
        assert result["pendingChecks"] == []

    def test_mixed_pass_fail(self):
        """Mixed pass and fail checks are classified correctly."""
        checks = [
            {"name": "build", "bucket": "pass"},
            {"name": "lint", "bucket": "fail"},
            {"name": "test", "bucket": "pass"},
        ]
        result = _classify_checks(checks)
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["failedChecks"] == ["lint"]

    def test_pending_checks(self):
        """Pending checks are counted and names collected."""
        checks = [
            {"name": "build", "bucket": "pass"},
            {"name": "deploy", "bucket": "pending"},
            {"name": "e2e", "bucket": "pending"},
        ]
        result = _classify_checks(checks)
        assert result["pending"] == 2
        assert result["pendingChecks"] == ["deploy", "e2e"]

    def test_skipping_checks(self):
        """Checks with bucket 'skipping' are counted as skipped."""
        checks = [
            {"name": "build", "bucket": "pass"},
            {"name": "optional", "bucket": "skipping"},
        ]
        result = _classify_checks(checks)
        assert result["skipped"] == 1
        assert result["passed"] == 1

    def test_cancelled_checks(self):
        """Checks with bucket 'cancel' are counted as cancelled."""
        checks = [
            {"name": "build", "bucket": "cancel"},
            {"name": "test", "bucket": "pass"},
        ]
        result = _classify_checks(checks)
        assert result["cancelled"] == 1
        assert result["passed"] == 1

    def test_empty_list(self):
        """Empty checks list returns all zeros."""
        result = _classify_checks([])
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["pending"] == 0
        assert result["skipped"] == 0
        assert result["cancelled"] == 0
        assert result["total"] == 0
        assert result["failedChecks"] == []
        assert result["pendingChecks"] == []

    def test_missing_bucket_key(self):
        """Checks with missing bucket key are not counted in any category."""
        checks = [
            {"name": "build", "bucket": "pass"},
            {"name": "mystery"},
        ]
        result = _classify_checks(checks)
        assert result["passed"] == 1
        assert result["total"] == 2
        # The mystery check is not counted in any bucket

    def test_missing_name_uses_unknown(self):
        """Checks with missing name default to 'unknown'."""
        checks = [{"bucket": "fail"}]
        result = _classify_checks(checks)
        assert result["failedChecks"] == ["unknown"]
