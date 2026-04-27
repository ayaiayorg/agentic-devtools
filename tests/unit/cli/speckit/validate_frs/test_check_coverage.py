"""Tests for ``check_coverage()``."""

from agentic_devtools.cli.speckit.validate_frs import check_coverage


class TestCheckCoverage:
    """check_coverage: word-boundary, case-insensitive matching."""

    def test_all_covered(self) -> None:
        result = check_coverage(["FR-001", "FR-002"], "FR-001 and FR-002 are done.")
        assert result == {"FR-001": True, "FR-002": True}

    def test_none_covered(self) -> None:
        result = check_coverage(["FR-001", "FR-002"], "Nothing relevant here.")
        assert result == {"FR-001": False, "FR-002": False}

    def test_partial_coverage(self) -> None:
        result = check_coverage(["FR-001", "FR-002"], "Only FR-001 is covered.")
        assert result == {"FR-001": True, "FR-002": False}

    def test_case_insensitive_match(self) -> None:
        result = check_coverage(["FR-001"], "Tasks mention fr-001 in lowercase.")
        assert result == {"FR-001": True}

    def test_word_boundary_fr1_does_not_match_fr10(self) -> None:
        result = check_coverage(["FR-1"], "Tasks mention FR-10 and FR-100.")
        assert result == {"FR-1": False}

    def test_word_boundary_fr10_does_not_match_fr1(self) -> None:
        result = check_coverage(["FR-10"], "Tasks mention FR-1 and FR-100.")
        assert result == {"FR-10": False}

    def test_fr_inside_fenced_code_blocks_counts(self) -> None:
        tasks = """Some text.

```python
# Implements FR-001
```

More text.
"""
        result = check_coverage(["FR-001"], tasks)
        assert result == {"FR-001": True}

    def test_empty_fr_list(self) -> None:
        result = check_coverage([], "Some tasks content.")
        assert result == {}

    def test_empty_tasks_content(self) -> None:
        result = check_coverage(["FR-001"], "")
        assert result == {"FR-001": False}

    def test_exact_word_boundary(self) -> None:
        """FR-1 should match when standalone, not as prefix of FR-10."""
        tasks = "Task covers FR-1 explicitly."
        result = check_coverage(["FR-1", "FR-10"], tasks)
        assert result == {"FR-1": True, "FR-10": False}
