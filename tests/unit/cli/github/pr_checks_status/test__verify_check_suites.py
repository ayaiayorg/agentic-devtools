"""Tests for _verify_check_suites function."""

from agentic_devtools.cli.github.pr_checks_status import _verify_check_suites


class TestVerifyCheckSuites:
    """Tests for check-suite verification logic."""

    def test_all_green(self):
        """All suites completed with success → verified True, no discrepancies."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "success", "app": {"slug": "github-actions"}},
            {"id": 2, "status": "completed", "conclusion": "success", "app": {"slug": "codecov"}},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is True
        assert discrepancies == []

    def test_one_failure(self):
        """One suite with failure conclusion → discrepancy."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "success", "app": {"slug": "github-actions"}},
            {"id": 2, "status": "completed", "conclusion": "failure", "app": {"slug": "codecov"}},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is False
        assert len(discrepancies) == 1
        assert discrepancies[0]["suiteId"] == 2
        assert discrepancies[0]["app"] == "codecov"
        assert discrepancies[0]["conclusion"] == "failure"

    def test_one_incomplete(self):
        """Suite with status != 'completed' → discrepancy."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "success", "app": {"slug": "ci"}},
            {"id": 2, "status": "in_progress", "conclusion": "", "app": {"slug": "deploy"}},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is False
        assert len(discrepancies) == 1
        assert discrepancies[0]["status"] == "in_progress"

    def test_neutral_treated_as_green(self):
        """Suite with conclusion 'neutral' is treated as green."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "neutral", "app": {"slug": "ci"}},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is True
        assert discrepancies == []

    def test_skipped_treated_as_green(self):
        """Suite with conclusion 'skipped' is treated as green."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "skipped", "app": {"slug": "ci"}},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is True
        assert discrepancies == []

    def test_empty_list(self):
        """Empty suites list → verified True, no discrepancies."""
        verified, discrepancies = _verify_check_suites([])
        assert verified is True
        assert discrepancies == []

    def test_conclusion_null(self):
        """Suite with conclusion None/null is treated as discrepancy."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": None, "app": {"slug": "ci"}},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is False
        assert len(discrepancies) == 1
        assert discrepancies[0]["conclusion"] == ""

    def test_mixed_discrepancies(self):
        """Multiple suites with different issues."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "success", "app": {"slug": "ok"}},
            {"id": 2, "status": "queued", "conclusion": "", "app": {"slug": "queued-app"}},
            {"id": 3, "status": "completed", "conclusion": "failure", "app": {"slug": "bad"}},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is False
        assert len(discrepancies) == 2

    def test_app_as_string(self):
        """Suite with app as string (not dict) is handled."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "failure", "app": "my-app"},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is False
        assert discrepancies[0]["app"] == "my-app"

    def test_app_missing(self):
        """Suite without app field defaults to 'unknown'."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "failure"},
        ]
        verified, discrepancies = _verify_check_suites(suites)
        assert verified is False
        assert discrepancies[0]["app"] == "unknown"
