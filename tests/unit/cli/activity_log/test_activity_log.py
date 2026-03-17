"""Tests for ActivityLog dataclass (to_dict, from_dict, has_been_posted, mark_as_posted)."""

from unittest.mock import patch

from agentic_devtools.cli import activity_log as al_module
from agentic_devtools.cli.activity_log import ActivityLog, ActivityLogEntry


class TestActivityLog:
    """Tests for ActivityLog dataclass."""

    def test_to_dict_empty_posted_commits(self):
        """Test that to_dict serializes empty postedCommits as empty dict."""
        log = ActivityLog()
        result = log.to_dict()

        assert result == {"postedCommits": {}}

    def test_to_dict_populated_posted_commits(self):
        """Test that to_dict serializes populated postedCommits correctly."""
        log = ActivityLog(
            postedCommits={
                "abc123": ActivityLogEntry(
                    postedUtc="2026-03-13T10:00:00Z",
                    branchName="feature/X",
                    worktreeKey="X",
                    prCommentPosted=True,
                    jiraCommentPosted=False,
                    prId=42,
                ),
            }
        )
        result = log.to_dict()

        assert "abc123" in result["postedCommits"]
        assert result["postedCommits"]["abc123"]["postedUtc"] == "2026-03-13T10:00:00Z"
        assert result["postedCommits"]["abc123"]["prId"] == 42

    def test_from_dict_empty_data(self):
        """Test that from_dict with empty data returns empty ActivityLog."""
        log = ActivityLog.from_dict({})

        assert log.postedCommits == {}

    def test_from_dict_populated_data(self):
        """Test that from_dict with populated data returns correct entries."""
        data = {
            "postedCommits": {
                "dead1234": {
                    "postedUtc": "2026-03-13T10:00:00Z",
                    "branchName": "feature/Y",
                    "worktreeKey": "Y",
                    "prCommentPosted": False,
                    "jiraCommentPosted": True,
                    "prId": 7,
                }
            }
        }
        log = ActivityLog.from_dict(data)

        assert "dead1234" in log.postedCommits
        entry = log.postedCommits["dead1234"]
        assert entry.branchName == "feature/Y"
        assert entry.prId == 7

    def test_round_trip_preserves_data(self):
        """Test that to_dict → from_dict round-trip preserves data."""
        original = ActivityLog(
            postedCommits={
                "aaa111": ActivityLogEntry(
                    postedUtc="2026-01-01T00:00:00Z",
                    branchName="main",
                    worktreeKey="key-1",
                    prCommentPosted=True,
                    jiraCommentPosted=True,
                    prId=99,
                ),
                "bbb222": ActivityLogEntry(
                    postedUtc="2026-02-02T00:00:00Z",
                    branchName="dev",
                    worktreeKey="key-2",
                    prCommentPosted=False,
                    jiraCommentPosted=False,
                ),
            }
        )
        restored = ActivityLog.from_dict(original.to_dict())

        assert len(restored.postedCommits) == 2
        assert restored.postedCommits["aaa111"].prId == 99
        assert restored.postedCommits["bbb222"].prId is None

    def test_has_been_posted_returns_false_for_unknown_hash(self):
        """Test that has_been_posted returns False for unknown hash."""
        log = ActivityLog(
            postedCommits={
                "known": ActivityLogEntry(
                    postedUtc="2026-03-13T10:00:00Z",
                    branchName="X",
                    worktreeKey="X",
                    prCommentPosted=True,
                    jiraCommentPosted=False,
                ),
            }
        )
        assert log.has_been_posted("unknown") is False

    def test_has_been_posted_returns_true_for_known_hash(self):
        """Test that has_been_posted returns True for known hash."""
        log = ActivityLog(
            postedCommits={
                "known": ActivityLogEntry(
                    postedUtc="2026-03-13T10:00:00Z",
                    branchName="X",
                    worktreeKey="X",
                    prCommentPosted=True,
                    jiraCommentPosted=False,
                ),
            }
        )
        assert log.has_been_posted("known") is True

    def test_has_been_posted_on_empty_log(self):
        """Test that has_been_posted on empty log returns False."""
        log = ActivityLog()

        assert log.has_been_posted("anything") is False

    def test_mark_as_posted_adds_entry(self):
        """Test that mark_as_posted adds entry to postedCommits."""
        log = ActivityLog()
        log.mark_as_posted(
            "abc123",
            posted_utc="2026-03-13T10:00:00Z",
            branch_name="feature/X",
            worktree_key="X",
        )

        assert "abc123" in log.postedCommits
        entry = log.postedCommits["abc123"]
        assert entry.postedUtc == "2026-03-13T10:00:00Z"
        assert entry.branchName == "feature/X"
        assert entry.worktreeKey == "X"
        assert entry.prCommentPosted is False
        assert entry.jiraCommentPosted is False
        assert entry.prId is None

    def test_mark_as_posted_overwrites_existing(self):
        """Test that mark_as_posted overwrites existing entry for same hash."""
        log = ActivityLog()
        log.mark_as_posted(
            "abc123",
            posted_utc="2026-03-13T10:00:00Z",
            branch_name="feature/old",
            worktree_key="old",
        )
        log.mark_as_posted(
            "abc123",
            posted_utc="2026-03-14T10:00:00Z",
            branch_name="feature/new",
            worktree_key="new",
            pr_comment_posted=True,
        )

        entry = log.postedCommits["abc123"]
        assert entry.branchName == "feature/new"
        assert entry.postedUtc == "2026-03-14T10:00:00Z"

    def test_mark_as_posted_with_pr_id(self):
        """Test that mark_as_posted stores pr_id on the entry."""
        log = ActivityLog()
        log.mark_as_posted(
            "abc123",
            posted_utc="2026-03-13T10:00:00Z",
            branch_name="feature/X",
            worktree_key="X",
            pr_id=42,
        )

        assert log.postedCommits["abc123"].prId == 42

    def test_mark_as_posted_does_not_call_save_or_mark_dirty(self):
        """Test that mark_as_posted does NOT call save_activity_log or mark_dirty."""
        with patch.object(al_module, "save_activity_log") as mock_save:
            with patch.object(al_module, "mark_dirty", create=True) as mock_dirty:
                log = ActivityLog()
                log.mark_as_posted(
                    "abc123",
                    posted_utc="2026-03-13T10:00:00Z",
                    branch_name="feature/X",
                    worktree_key="X",
                )

        mock_save.assert_not_called()
        mock_dirty.assert_not_called()

    def test_from_dict_non_dict_posted_commits_is_ignored(self):
        """Test that from_dict treats non-dict postedCommits as empty."""
        log = ActivityLog.from_dict({"postedCommits": ["not", "a", "dict"]})

        assert log.postedCommits == {}

    def test_from_dict_skips_non_dict_entry_values(self):
        """Test that from_dict skips entries whose value is not a dict."""
        data = {
            "postedCommits": {
                "bad-entry": "not-a-dict",
                "good-entry": {
                    "postedUtc": "2026-03-13T10:00:00Z",
                    "branchName": "feature/X",
                    "worktreeKey": "X",
                    "prCommentPosted": True,
                    "jiraCommentPosted": False,
                },
            }
        }
        log = ActivityLog.from_dict(data)

        assert "bad-entry" not in log.postedCommits
        assert "good-entry" in log.postedCommits

    def test_from_dict_skips_malformed_entry_missing_required_field(self):
        """Test that from_dict skips entries that raise KeyError/TypeError."""
        data = {
            "postedCommits": {
                "malformed": {
                    # missing required fields like postedUtc, branchName, etc.
                    "unexpectedKey": 42,
                },
                "good-entry": {
                    "postedUtc": "2026-03-13T10:00:00Z",
                    "branchName": "feature/X",
                    "worktreeKey": "X",
                    "prCommentPosted": True,
                    "jiraCommentPosted": False,
                },
            }
        }
        log = ActivityLog.from_dict(data)

        assert "malformed" not in log.postedCommits
        assert "good-entry" in log.postedCommits
