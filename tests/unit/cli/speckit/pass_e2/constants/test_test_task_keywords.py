"""Tests for pass_e2.constants — TEST_TASK_KEYWORDS."""

from agentic_devtools.cli.speckit.pass_e2.constants import TEST_TASK_KEYWORDS


class TestTestTaskKeywords:
    """Verify TEST_TASK_KEYWORDS contains FR-002 required keywords."""

    def test_is_non_empty(self) -> None:
        assert len(TEST_TASK_KEYWORDS) > 0

    def test_contains_required_single_word_keywords(self) -> None:
        required = {"test", "verify", "validate", "assert", "e2e"}
        actual = set(TEST_TASK_KEYWORDS)
        assert required.issubset(actual)

    def test_contains_required_multi_word_keywords(self) -> None:
        required = {
            "spec test",
            "specification test",
            "e2e test",
            "integration test",
            "unit test",
            "smoke test",
            "acceptance test",
        }
        actual = set(TEST_TASK_KEYWORDS)
        assert required.issubset(actual)

    def test_no_duplicates(self) -> None:
        assert len(TEST_TASK_KEYWORDS) == len(set(TEST_TASK_KEYWORDS))
