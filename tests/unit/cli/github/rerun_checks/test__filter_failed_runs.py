"""Tests for _filter_failed_runs."""

from agentic_devtools.cli.github.rerun_checks import _filter_failed_runs


class TestFilterFailedRuns:
    """Tests for _filter_failed_runs."""

    def test_all_failed_all_eligible(self):
        """All failed runs are eligible when no filter is applied."""
        runs = [
            {"id": 1, "name": "CI", "conclusion": "failure"},
            {"id": 2, "name": "Lint", "conclusion": "failure"},
        ]

        eligible, skipped = _filter_failed_runs(runs)

        assert len(eligible) == 2
        assert len(skipped) == 0

    def test_mixed_conclusions_only_failures_eligible(self):
        """Only failure/cancelled runs are eligible; success/pending are ignored."""
        runs = [
            {"id": 1, "name": "CI", "conclusion": "failure"},
            {"id": 2, "name": "Lint", "conclusion": "success"},
            {"id": 3, "name": "Build", "conclusion": "cancelled"},
            {"id": 4, "name": "Deploy", "conclusion": "pending"},
        ]

        eligible, skipped = _filter_failed_runs(runs, include_cancelled=True)

        assert [r["id"] for r in eligible] == [1, 3]
        assert len(skipped) == 0

    def test_cancelled_excluded_when_include_cancelled_false(self):
        """Cancelled runs are excluded when include_cancelled is False."""
        runs = [
            {"id": 1, "name": "CI", "conclusion": "failure"},
            {"id": 2, "name": "Build", "conclusion": "cancelled"},
        ]

        eligible, skipped = _filter_failed_runs(runs, include_cancelled=False)

        assert [r["id"] for r in eligible] == [1]
        assert len(skipped) == 0  # cancelled is not failure, so not in skipped either

    def test_stale_runs_eligible_by_default(self):
        """Stale runs are eligible alongside failures by default."""
        runs = [
            {"id": 1, "name": "CI", "conclusion": "failure"},
            {"id": 2, "name": "Build", "conclusion": "stale"},
            {"id": 3, "name": "Lint", "conclusion": "success"},
        ]

        eligible, skipped = _filter_failed_runs(runs, include_cancelled=True)

        assert [r["id"] for r in eligible] == [1, 2]
        assert len(skipped) == 0

    def test_stale_eligible_without_cancelled(self):
        """Stale runs are eligible even when cancelled is excluded."""
        runs = [
            {"id": 1, "name": "CI", "conclusion": "stale"},
            {"id": 2, "name": "Build", "conclusion": "cancelled"},
        ]

        eligible, skipped = _filter_failed_runs(runs, include_cancelled=False)

        assert [r["id"] for r in eligible] == [1]
        assert len(skipped) == 0

    def test_name_filter_matching(self):
        """Name filter selects only matching runs."""
        runs = [
            {"id": 1, "name": "Copilot Review Gate", "conclusion": "failure"},
            {"id": 2, "name": "CI", "conclusion": "failure"},
        ]

        eligible, skipped = _filter_failed_runs(runs, name_filter="Copilot Review")

        assert [r["id"] for r in eligible] == [1]
        assert [r["id"] for r in skipped] == [2]

    def test_name_filter_case_insensitive(self):
        """Name filter is case-insensitive."""
        runs = [
            {"id": 1, "name": "Copilot Review Gate", "conclusion": "failure"},
        ]

        eligible, skipped = _filter_failed_runs(runs, name_filter="copilot review")

        assert len(eligible) == 1
        assert len(skipped) == 0

    def test_name_filter_excludes_to_skipped(self):
        """Excluded runs go to skipped list, not silently dropped."""
        runs = [
            {"id": 1, "name": "CI", "conclusion": "failure"},
            {"id": 2, "name": "Lint", "conclusion": "failure"},
        ]

        eligible, skipped = _filter_failed_runs(runs, name_filter="Deploy")

        assert len(eligible) == 0
        assert len(skipped) == 2

    def test_empty_runs_list(self):
        """Empty input returns empty results."""
        eligible, skipped = _filter_failed_runs([])

        assert eligible == []
        assert skipped == []

    def test_null_conclusion_skipped(self):
        """Runs with null/empty conclusion are skipped entirely."""
        runs = [
            {"id": 1, "name": "CI", "conclusion": None},
            {"id": 2, "name": "Lint", "conclusion": ""},
            {"id": 3, "name": "Build"},  # missing conclusion key
        ]

        eligible, skipped = _filter_failed_runs(runs)

        assert eligible == []
        assert skipped == []
