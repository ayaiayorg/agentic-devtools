"""Tests for agentic_devtools.cli.git.diff.DiffLinesInfo."""

from agentic_devtools.cli.git.diff import AddedLinesInfo, DiffLinesInfo, RemovedLinesInfo


class TestDiffLinesInfo:
    """Tests for DiffLinesInfo dataclass."""

    def test_stores_added_and_removed(self):
        """Should store both added and removed info."""
        added = AddedLinesInfo(lines=[], is_binary=False)
        removed = RemovedLinesInfo(lines=[], is_binary=False)
        info = DiffLinesInfo(added=added, removed=removed)

        assert info.added is added
        assert info.removed is removed

    def test_binary_flags_independent(self):
        """Should preserve binary flags from both sub-infos."""
        info = DiffLinesInfo(
            added=AddedLinesInfo(lines=[], is_binary=True),
            removed=RemovedLinesInfo(lines=[], is_binary=True),
        )

        assert info.added.is_binary is True
        assert info.removed.is_binary is True
