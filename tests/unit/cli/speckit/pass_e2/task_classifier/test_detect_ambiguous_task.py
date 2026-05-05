"""Tests for pass_e2.task_classifier — detect_ambiguous_task."""

from agentic_devtools.cli.speckit.pass_e2.task_classifier import detect_ambiguous_task


class TestDetectAmbiguousTask:
    """Verify ambiguous task detection."""

    def test_ambiguous_implement_and_verify(self) -> None:
        assert detect_ambiguous_task("Implement and verify user login flow") is True

    def test_ambiguous_create_and_test(self) -> None:
        assert detect_ambiguous_task("Create unit tests for the parser module") is True

    def test_pure_test_not_ambiguous(self) -> None:
        assert detect_ambiguous_task("Verify that the output format is correct") is False

    def test_pure_implementation_not_ambiguous(self) -> None:
        assert detect_ambiguous_task("Implement the user login feature") is False

    def test_write_tests_is_ambiguous(self) -> None:
        """'Write' is impl keyword + 'tests' is test keyword."""
        assert detect_ambiguous_task("Write integration tests for the API") is True
