"""Tests for DEFAULT_ACTIONABLE_CHECK_NAMES."""

from agentic_devtools.cli.ci.actionable_checks import DEFAULT_ACTIONABLE_CHECK_NAMES


class TestDefaultActionableCheckNames:
    """Tests for the DEFAULT_ACTIONABLE_CHECK_NAMES constant."""

    def test_is_frozenset(self) -> None:
        assert isinstance(DEFAULT_ACTIONABLE_CHECK_NAMES, frozenset)

    def test_contains_worker_job_names(self) -> None:
        assert "Run Targeted Checks" in DEFAULT_ACTIONABLE_CHECK_NAMES
        assert "Run Smart Module Tests" in DEFAULT_ACTIONABLE_CHECK_NAMES
        assert "Workflow Tests" in DEFAULT_ACTIONABLE_CHECK_NAMES

    def test_contains_codeql_names(self) -> None:
        assert "Code scanning results / CodeQL" in DEFAULT_ACTIONABLE_CHECK_NAMES
        assert "CodeQL / Analyze (actions) (dynamic)" in DEFAULT_ACTIONABLE_CHECK_NAMES
        assert "CodeQL / Analyze (python) (dynamic)" in DEFAULT_ACTIONABLE_CHECK_NAMES

    def test_exact_members(self) -> None:
        assert DEFAULT_ACTIONABLE_CHECK_NAMES == frozenset(
            {
                "Run Targeted Checks",
                "Run Smart Module Tests",
                "Workflow Tests",
                "Code scanning results / CodeQL",
                "CodeQL / Analyze (actions) (dynamic)",
                "CodeQL / Analyze (python) (dynamic)",
            }
        )
