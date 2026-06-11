"""Tests for agentic_devtools.cli.git.commit_intent.CommitIntent."""

from agentic_devtools.cli.git.commit_intent import CommitIntent


class TestCommitIntent:
    """Tests for the CommitIntent dataclass."""

    def test_create_mode(self):
        """Test CommitIntent with create mode."""
        intent = CommitIntent(
            mode="create",
            title="feat: add feature",
            body="- Added tests",
            full_message="feat: add feature\n\n- Added tests",
        )
        assert intent.mode == "create"
        assert intent.title == "feat: add feature"
        assert intent.body == "- Added tests"
        assert intent.full_message == "feat: add feature\n\n- Added tests"

    def test_overwrite_mode(self):
        """Test CommitIntent with overwrite mode."""
        intent = CommitIntent(
            mode="overwrite",
            title="fix: correct bug",
            body=None,
            full_message="fix: correct bug",
        )
        assert intent.mode == "overwrite"
        assert intent.title == "fix: correct bug"
        assert intent.body is None

    def test_legacy_mode(self):
        """Test CommitIntent with legacy mode."""
        intent = CommitIntent(
            mode="legacy",
            title=None,
            body=None,
            full_message="feat: full message\n\nBody here",
        )
        assert intent.mode == "legacy"
        assert intent.title is None
        assert intent.body is None
        assert "full message" in intent.full_message
