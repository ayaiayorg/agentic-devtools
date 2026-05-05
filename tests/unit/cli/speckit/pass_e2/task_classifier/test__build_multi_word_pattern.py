"""Tests for pass_e2.task_classifier — _build_multi_word_pattern edge cases."""

from agentic_devtools.cli.speckit.pass_e2.task_classifier import _build_multi_word_pattern


class TestBuildMultiWordPattern:
    """Verify multi-word pattern building, including single-token edge case."""

    def test_single_token_keyword(self) -> None:
        """When keyword has no real separators, pattern still works (else branch)."""
        # A keyword that produces only one token when split on [-\\s]+
        pattern = _build_multi_word_pattern("e2e")
        # Should match "e2e" and "e2es"
        assert pattern.search("run e2e tests") is not None
        assert pattern.search("e2es are important") is not None

    def test_multi_token_keyword(self) -> None:
        """Standard multi-word keyword with 2+ tokens."""
        pattern = _build_multi_word_pattern("integration test")
        assert pattern.search("run integration test suite") is not None
        assert pattern.search("integration-tests pass") is not None

    def test_hyphenated_keyword(self) -> None:
        """Hyphenated keyword splits into multiple tokens."""
        pattern = _build_multi_word_pattern("happy-path")
        assert pattern.search("happy path scenario") is not None
        assert pattern.search("happy-paths covered") is not None
