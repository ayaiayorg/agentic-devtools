"""Tests for STANDARD_COMMIT_TYPES constant."""

from agentic_devtools.cli.config.commit_type_resolution import STANDARD_COMMIT_TYPES


class TestStandardCommitTypes:
    """Tests for the STANDARD_COMMIT_TYPES constant."""

    def test_contains_all_conventional_commits_types(self):
        """Verify the list contains all 11 Conventional Commits types."""
        expected = [
            "feat",
            "fix",
            "docs",
            "style",
            "refactor",
            "perf",
            "test",
            "build",
            "ci",
            "chore",
            "revert",
        ]
        assert STANDARD_COMMIT_TYPES == expected

    def test_has_exactly_eleven_entries(self):
        """Verify the list has exactly 11 entries."""
        assert len(STANDARD_COMMIT_TYPES) == 11

    def test_all_entries_are_lowercase_strings(self):
        """All entries must be lowercase strings."""
        for entry in STANDARD_COMMIT_TYPES:
            assert isinstance(entry, str)
            assert entry == entry.lower()

    def test_is_a_list(self):
        """Must be a list type (not tuple or set)."""
        assert isinstance(STANDARD_COMMIT_TYPES, list)
