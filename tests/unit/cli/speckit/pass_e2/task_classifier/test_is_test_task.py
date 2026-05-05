"""Tests for pass_e2.task_classifier — is_test_task."""

from agentic_devtools.cli.speckit.pass_e2.task_classifier import is_test_task


class TestIsTestTask:
    """Verify FR-002 keyword matching semantics."""

    def test_single_word_test_matches(self) -> None:
        assert is_test_task("Write unit tests for feature") is True

    def test_single_word_verify_matches(self) -> None:
        assert is_test_task("Verify user login flow") is True

    def test_single_word_validate_matches(self) -> None:
        assert is_test_task("Validate input schema") is True

    def test_single_word_assert_matches(self) -> None:
        assert is_test_task("Assert correct output format") is True

    def test_multi_word_integration_test_matches(self) -> None:
        assert is_test_task("Write integration test for API") is True

    def test_multi_word_unit_test_matches(self) -> None:
        assert is_test_task("Create unit test for parser") is True

    def test_multi_word_e2e_matches(self) -> None:
        assert is_test_task("Run e2e for full flow") is True

    def test_multi_word_smoke_test_matches(self) -> None:
        assert is_test_task("Add smoke test for deployment") is True

    def test_hyphenated_integration_test(self) -> None:
        assert is_test_task("Write integration-test for API") is True

    def test_plural_unit_tests(self) -> None:
        assert is_test_task("Write unit tests for module") is True

    def test_case_insensitive(self) -> None:
        assert is_test_task("VERIFY the output format") is True

    def test_contest_does_not_match(self) -> None:
        """'contest' should NOT match 'test' — word-boundary rule."""
        assert is_test_task("Run the contest submission pipeline") is False

    def test_unverified_does_not_match(self) -> None:
        """'unverified' should NOT match 'verify' — word-boundary rule."""
        assert is_test_task("Handle unverified accounts") is False

    def test_hyphen_not_boundary_for_single_word(self) -> None:
        """Single-word 'test' should NOT match inside 'unit-test' via boundary."""
        # However, 'unit test' (multi-word) would match 'unit-test'
        # The key is: single-word 'test' alone should not match inside compounds
        assert is_test_task("Run the unit-test suite") is True  # matches 'unit test' multi-word

    def test_no_test_keywords(self) -> None:
        assert is_test_task("Implement user login feature") is False

    def test_implementation_only(self) -> None:
        assert is_test_task("Create database schema migration") is False
